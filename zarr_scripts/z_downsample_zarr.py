
from skimage.transform import resize
import zarr
from ome_zarr.writer import write_multiscale
from ome_zarr.io import parse_url
import os
import shutil

# Fails on large images e.g. (4, 259, 1920, 1920)
# Traceback (most recent call last):
#   File "/uod/idr/objectstore/minio/idr/v0.4/idr0077/z_downsample.py", line 49, in <module>
#     fix_data("9836832.zarr")
#   File "/uod/idr/objectstore/minio/idr/v0.4/idr0077/z_downsample.py", line 34, in fix_data
#     data = resize(data, new_shape)
#   File "/lifesci/groups/jrs/wmoore/miniconda3/envs/omero_zarr_export/lib/python3.9/site-packages/skimage/transform/_warps.py", line 190, in resize
#     image = convert_to_float(image, preserve_range)
#   File "/lifesci/groups/jrs/wmoore/miniconda3/envs/omero_zarr_export/lib/python3.9/site-packages/skimage/_shared/utils.py", line 378, in convert_to_float
#     image = img_as_float(image)
#   File "/lifesci/groups/jrs/wmoore/miniconda3/envs/omero_zarr_export/lib/python3.9/site-packages/skimage/util/dtype.py", line 458, in img_as_float
#     return _convert(image, np.floating, force_copy)
#   File "/lifesci/groups/jrs/wmoore/miniconda3/envs/omero_zarr_export/lib/python3.9/site-packages/skimage/util/dtype.py", line 319, in _convert
#     image = np.multiply(image, 1. / imax_in,
# numpy.core._exceptions.MemoryError: Unable to allocate 28.5 GiB for an array with shape (4, 259, 1920, 1920) and data type float64

downscale = 2

def fix_data(path):
    pyramid = []
    # chunk_list = []
    with zarr.open(path, "a") as f:
        print("f.attrs", f.attrs)
        axes = f.attrs['multiscales'][0]['axes']
        print('axes', axes)
        downsample_z = axes[-3]['name'] == 'z'
        print("downsample_z?", downsample_z)
        n_scales = len(f)

        data = f["0"]
        pyramid.append(data)

        # for each existing pyramid level... 
        for ds_name in range(n_scales - 1):

            dtype = data.dtype
            new_shape = list(data.shape)
            new_shape[-1] = data.shape[-1] // downscale
            new_shape[-2] = data.shape[-2] // downscale
            new_shape[-3] = data.shape[-3] // downscale

            print('new_shape...', new_shape)
            data = resize(data, new_shape).astype(dtype)
            pyramid.append(data)

        chunk_sizes = {'x': 125, 'y': 125, 'z': 125, 'c': 1, 't': 1}
        chunks = tuple([chunk_sizes[axis['name']] for axis in axes])
        print("chunks", chunks)

    out_path = "6001240_z.zarr"
    if os.path.isdir(out_path):
        shutil.rmtree(out_path)

    store = parse_url(out_path, mode="w").store
    root = zarr.group(store=store)
    write_multiscale(pyramid, root, axes=axes, chunks=chunks)

fix_data("/Users/wmoore/Desktop/ZARR/data/6001240.zarr")
