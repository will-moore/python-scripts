
import argparse
import math
import sys
import os

import zarr
import dask.array as da
import numpy as np
from scipy import ndimage
import skimage as ski
from ome_zarr.writer import write_image, add_metadata, get_metadata
from napari.utils.transforms import Affine

"""
This script takes a ~large OME-Zarr v0.5 or (v0.4) image and crops a region
from it, optionally rotating the region in the XY plane. The cropped region is
then saved as a new OME-Zarr v0.6 dataset, with appropriate metadata including
coordinate transformations to place the cropped region in the same physical
space as the original image.

Usage: python crop_zarr.py <path> <xywh> <rotation>

The following will create 2 tiles and the original 'full' image,
all under a new top-level zarr group:

$ python crop_zarr.py 9036345.ome.zarr/ 300,300,300,300 20
$ python crop_zarr.py 9036345.ome.zarr/ 200,200,200,200 30
$ python crop_zarr.py 9036345.ome.zarr/ full 0

NB: This uses ome-zarr-py 0.12.0 (Not yet with RFC-5 support)
"""

COORDINATE_SYS_NAMES = ["physical", "rotated", "stitched"]


def crop_zarr(path, xywh, rotation):
    """Crop a region from a Zarr dataset and save to a new Zarr dataset.

    Args:
        path (str): Path to the input Zarr dataset.
        xywh (str): Crop region in the format 'x,y,width,height' or 'full'.
    """
    # Open the input Zarr dataset
    input_zarr = zarr.open_group(path)

    zarr_attrs = input_zarr.attrs.asdict()
    if "ome" in zarr_attrs:
        zarr_attrs = zarr_attrs["ome"]

    multiscales = zarr_attrs["multiscales"][0]
    axes = multiscales["axes"]
    omero_attrs = zarr_attrs.get("omero")

    array_path_0 = multiscales["datasets"][0]["path"]
    data = da.from_zarr(input_zarr[array_path_0])


    # for top-resolution, assume first transformation is scale
    # e.g. "coordinateTransformations": [ { "type": "scale", "scale": [1.0, 1.0, 1.0] }...
    orig_scale = multiscales["datasets"][0]["coordinateTransformations"][0]["scale"]
    
    identity_aff = Affine(translate=[0] * data.ndim)
    identity_matrix = identity_aff.affine_matrix.tolist()
    
    # handle .ome.zarr or .zarr
    out_path = path.replace('.ome.zarr', '.zarr')

    if xywh.lower() == "full":
        final_data = data
        tile_path = out_path.replace('.zarr', f'_full.zarr')
    else:
        # Parse the xywh and rotation args
        x, y, width, height = map(int, xywh.split(','))
        tile_path = out_path.replace(
            '.zarr', f'_cropped_{x}_{y}_{width}_{height}_rot{int(rotation)}.zarr')

        # crop...
        slices = tuple([slice(None) for _ in range(data.ndim - 2)] +
                    [slice(y, y + height), slice(x, x + width)])
        cropped_data = data[slices]

        # ...now we rotate in XY plane - last 2 axes
        ndim = data.ndim
        final_data = ndimage.rotate(
            cropped_data, rotation, axes=(ndim - 1, ndim - 2), reshape=False)

        # After scaling each resolution to full size, we then translate the panel
        # to put the centre of the panel at 0,0 so that the rotation matrix is around the
        # centre of the panel
        half_width = (width / 2) * orig_scale[-1]
        half_height = (height / 2) * orig_scale[-2]

        # rotate in Z axis, uses degrees
        # e.g. this will give 5 x 5 matrix for 4D image
        # Affine(rotate=30).expand_dims([0, 1]).affine_matrix
        rotation_aff = Affine(rotate=-rotation)    # 3 x 3 matrix for 2D image
        extra_dims = final_data.ndim - 2
        if extra_dims > 0:
            rotation_aff = rotation_aff.expand_dims(list(range(extra_dims)))
        rotation_matrix = rotation_aff.affine_matrix.tolist()

        print("Affine rotation_matrix:", rotation_matrix)

        # Finally we translate again to undo translation above and put panel top-left at x, y
        trans_x = ((width / 2) + x) * orig_scale[-1]
        trans_y = ((height / 2) + y) * orig_scale[-2]

        # These 2 transformations are siblings of 'multiscales'
        sibling_trans = {
            "type": "sequence",
            "input": COORDINATE_SYS_NAMES[0],
            "output": COORDINATE_SYS_NAMES[1],
            "transformations": [
                {
                    "name": "translate_centre_to_origin",
                    "type": "translation",
                    "translation": [0] * (final_data.ndim - 2) + [-half_height, -half_width]
                },
                {
                    "name": "rotate_around_centre",
                    "type": "rotation",
                    "rotation": rotation_matrix
                }
            ]
        }

    # TOP-LEVEL transformation translate tiles to stitched position
    # LET's add "sequence" transform and "affine" (identity matrix)
    top_level_trans = {
        "input": tile_path,
        "output": COORDINATE_SYS_NAMES[2],
        "type": "sequence",
        "transformations": [
            {
                "name": "affine_identity",
                "type": "affine",
                "affine": identity_matrix
            }
        ]
    }
    if xywh.lower() != "full":
        top_level_trans["transformations"].append({
            "name": "translate_tile_to_stitched_position",
            "type": "translation",
            "translation": [0] * (final_data.ndim - 2) + [trans_y, trans_x]
        })

    # This is the same for each resolution
    # full_size_translation = [0] * (final_data.ndim - 2) + [trans_y, trans_x]

    coord_trnsfms = []
    coord_trnsfms.append([{
        "input": "0",
        "output": COORDINATE_SYS_NAMES[0],
        "type": "scale",
        "scale": orig_scale
    }])

    # We don't know how many levels will be in new image, but we can assume
    # same number as original image. If croped image has FEWER levels, that
    # is OK, the extra cood_trnsfms will be ignored.
    for level in range(1, len(multiscales["datasets"])):
        previous_scale = coord_trnsfms[-1][0]["scale"]
        curr_scale = previous_scale[:]
        curr_scale[-1] *= 2
        curr_scale[-2] *= 2
        coord_trnsfms.append([{
            "input": str(level),
            "output": COORDINATE_SYS_NAMES[0],
            "type": "scale",
            "name": f"scale_{level}",
            "scale": curr_scale
        }])

    if xywh.lower() != "full":
        # HARD-CODED!
        coord_trnsfms = coord_trnsfms[:5]


    # READY to write out...

    # top-level zarr group that links the tiles together...

    root_path = out_path.replace('.zarr', f'_tiles.zarr')
    # this may already exist, so open in append mode
    root = zarr.open_group(root_path, mode="a")
    if "ome" in root.attrs:
        existing_attrs = dict(root.attrs["ome"])
    else:
        existing_attrs = {}
    
    if "coordinateTransformations" not in existing_attrs:
        existing_attrs["coordinateTransformations"] = []
        existing_attrs["version"] = "0.6dev2"
        # also add coordinateSystem - TODO: allow to add more than one?
        existing_attrs["coordinateSystems"] = [
            {
                "name": COORDINATE_SYS_NAMES[2],
                "axes": axes,
            }
        ]
    
    existing_attrs["coordinateTransformations"].append(top_level_trans)
    root.attrs["ome"] = existing_attrs

    # Sub-group for the tile image...

    save_to_path = os.path.join(root_path, tile_path)
    print("Writing tile to:", save_to_path)

    tile_group = zarr.open_group(save_to_path, mode="w", zarr_format=3)
    write_image(image=final_data, group=tile_group,
                coordinate_transformations=coord_trnsfms, axes=axes)
    
    # manually add coordinateTransformations for rotated system
    ms = get_metadata(tile_group)["multiscales"]
    if xywh.lower() == "full":
        # Full image has "physical" only
        ms[0]["coordinateSystems"] = [{
            "name": COORDINATE_SYS_NAMES[0],
            "axes": axes
        }]
    else:
        # cropped/rotated image has "physical" and "rotated"
        ms[0]["coordinateTransformations"] = [sibling_trans]
        ms[0]["coordinateSystems"] = [{
            "name": COORDINATE_SYS_NAMES[1],
            "axes": axes
        }, {
            "name": COORDINATE_SYS_NAMES[0],
            "axes": axes
        }]

    add_metadata(tile_group, {"multiscales": ms})
    # force update of version
    add_metadata(tile_group, {"version": "0.6dev2"})

    if omero_attrs:
        add_metadata(tile_group, {"omero": omero_attrs})


    # Write labels...
    # channel_axis = [ax["name"] for ax in axes].index("c")
    # if channel_axis > -1:
    #     # slide final_data to get first channel
    #     ch_data = np.take(final_data, [0], axis=channel_axis)
    #     print("ch_data, before squeeze:", ch_data.shape, ch_data.dtype)
    #     ch_data = np.squeeze(ch_data, axis=channel_axis)
    # else:
    #     ch_data = final_data

    # print("ch_data, after squeeze:", ch_data.shape, ch_data.dtype)
    # threshold = ski.filters.threshold_otsu(ch_data)
    # label_data = ch_data > threshold
    # label_data = label_data.astype(np.uint8)
    # print("Label data:", label_data.shape, label_data.dtype)

    # labels_grp = tile_group.create_group("labels")
    # label_name = "green"
    # add_metadata(labels_grp, {"labels": [label_name], "version": "0.6dev2"})
    # label_grp = labels_grp.create_group(label_name)

    # lbl_trans = coord_trnsfms.copy()
    # if channel_axis > -1:
    #     # remove channel dimension from scale transforms
    #     for t_list in lbl_trans:
    #         for t in t_list:
    #             if t["type"] == "scale":
    #                 # remove channel dimension
    #                 t["scale"].pop(channel_axis)
    #             elif t["type"] == "translation":
    #                 t["translation"].pop(channel_axis)

    # label_axes = [ax for ax in axes if ax["name"] != "c"]
    # write_image(label_data, label_grp, coordinate_transformations=lbl_trans, axes=label_axes)
    # # we need 'image-label' attr to be recognized as label
    # add_metadata(label_grp, {"image-label": {
    #     "colors": [{"label-value": 1, "rgba": [255, 255, 255, 255]}]
    # }})
    # # manually add coordinateTransformations for rotated system
    # # TODO: need to remove channel dimension from translation & rotation matrices
    # ms = get_metadata(label_grp)["multiscales"]
    # ms[0]["coordinateTransformations"] = [sibling_trans]
    # add_metadata(label_grp, {"multiscales": ms})
    # # force update of version
    # add_metadata(label_grp, {"version": "0.6dev2"})



def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='Path to the Zarr dataset')
    parser.add_argument('xywh', help='Crop region: x,y,width,height OR "full"')
    parser.add_argument('rotation', help='Rotation angle in degrees')

    args = parser.parse_args(argv)

    # Parse the xywh and rotation args
    # x, y, width, height = map(int, args.xywh.split(','))
    rotation = int(args.rotation)

    # Call the crop function
    dir_path = os.path.dirname(args.path)  # remove trailing /
    crop_zarr(dir_path, args.xywh, rotation)


if __name__ == '__main__':
    main(sys.argv[1:])
