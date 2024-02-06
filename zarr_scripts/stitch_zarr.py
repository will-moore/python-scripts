
# See https://forum.image.sc/t/zoom-from-overview-to-detailed-scan-for-imported-czi-files/85002/7
# Tested with the czi file from that post, converted to OME-NGFF with NGFF converter tool.

# Dependencies are 'omero_zarr' and 'ome-zarr-py'
# All should be installed with:
# pip install omero-cli-zarr

import zarr
import shutil
import os
from ome_zarr.io import parse_url

import numpy as np
import dask.array as da
from math import ceil

from ome_zarr.writer import write_multiscales_metadata
from omero_zarr.raw_pixels import downsample_pyramid_on_disk

import xml.etree.ElementTree as ET

ZARR_PATH = "TEST 2023_10_10__1046.zarr"

RESOLUTION = "0"
RESOLUTION_SCALE = 1
# Since the original file is very large, we can choose to use a lower resolution
# from the OME-Zarr file. Full size is "0" resolution, half size is "1" etc.
# RESOLUTION = "1"
# RESOLUTION_SCALE = 2

SCHEMA = "{http://www.openmicroscopy.org/Schemas/OME/2016-06}"
IMAGE = f"{SCHEMA}Image"
STAGELABEL = f"{SCHEMA}StageLabel"
PIXELS = f"{SCHEMA}Pixels"

scenes = []
img_index = -1


class Scene():

    def __init__(self, img_index, size_x, size_y, pixsize, offset_x, offset_y):
        self.img_index = img_index
        self.width = int(size_x) // RESOLUTION_SCALE
        self.height = int(size_y) // RESOLUTION_SCALE
        self.pixsize = float(pixsize)
        # we want to work in pixel coordinates, so let's convert offsets
        self.x = int(float(offset_x) / self.pixsize) // RESOLUTION_SCALE
        self.y = int(float(offset_y) / self.pixsize) // RESOLUTION_SCALE
        array_path = f"{ZARR_PATH}/{self.img_index}/{RESOLUTION}"
        print("array_path", array_path)
        self.data = da.from_zarr(array_path)
        print("init width", self.width, "height", self.height, "pix", self.pixsize, "xy", self.x, self.y)
        print("array.shape", self.data.shape)

    def intersects(self, x, y, width, height):
        if x > self.x + self.width:
            return False
        if y > self.y + self.height:
            return False
        if (x + width) < self.x:
            return False
        if (y + height) < self.y:
            return False
        return True

    def get_region(self, ch_index, x, y, width, height):
        if not self.intersects(x, y, width, height):
            return None

        print("\nget_region x, y, width, height", x, y, width, height)
        print("scene --- x, y, width, height", self.x, self.y, self.width, self.height)
        # find coordinates relative to the image
        img_x = x - self.x
        img_y = y - self.y
        crop_width = width
        crop_height = height

        paste_x = 0
        paste_y = 0

        print("img_ximg_ximg_x", img_x)
        if img_x < 0:
            crop_width = width + img_x
            paste_x = -img_x
            img_x = 0
        if img_y < 0:
            crop_height = height + img_y
            paste_y = -img_y
            img_y = 0
        if x + width > self.x + self.width:
            extra = (x + width) - (self.x + self.width)
            crop_width = crop_width - extra
        if y + height > self.y + self.height:
            extra = (y + height) - (self.y + self.height)
            crop_height = crop_height - extra


        canvas = np.zeros((height, width), dtype=np.int8)
        print("crop img_x", img_x, 'crop_width', crop_width, 'img_y', img_y, 'crop_height', crop_height)
        region = self.data[0, ch_index, 0, img_y:(img_y + crop_height), img_x:(img_x + crop_width)]
        print('region', region.shape)
        print('paste_x, paste_y', paste_x, paste_y)
        canvas[paste_y:(crop_height + paste_y), paste_x:(crop_width + paste_x)] = region
        return canvas


# Start by parsing the ome.xml to get the offsets for each "scene"...
tree = ET.parse(f"{ZARR_PATH}/OME/METADATA.ome.xml")
root = tree.getroot()
for child in root:
    is_img_tag = child.tag == IMAGE
    if is_img_tag:
        img_index += 1
        size_x = None
        size_y = None
        offset_x = None
        offset_y = None
        # NB: assume pixels are square
        pixsize = None
        for ch_element in child:
            if ch_element.tag == STAGELABEL:
                # print("STAGELABEL", img_index, ch_element.attrib)
                offset_x = ch_element.attrib.get("X")
                offset_y = ch_element.attrib.get("Y")
            elif ch_element.tag == PIXELS:
                pix_attrs = ch_element.attrib
                size_x = pix_attrs.get("SizeX")
                size_y = pix_attrs.get("SizeY")
                # size_z = pix_attrs.get("SizeZ")
                # size_c = pix_attrs.get("SizeC")
                # size_t = pix_attrs.get("SizeT")
                pixsize = pix_attrs.get("PhysicalSizeX")
        if offset_x is not None and size_x is not None:
            print("image", img_index, offset_x,size_x)
            scene = Scene(img_index, size_x, size_y, pixsize, offset_x, offset_y)
            scenes.append(scene)

if len(scenes) == 0:
    print("Found no Images with StageLabel coordinates to stitch")

# update offsets to start at 0, 0
x_offsets = [scene.x for scene in scenes]
y_offsets = [scene.y for scene in scenes]
min_x_offset = min(x_offsets)
min_y_offset = min(y_offsets)
for scene in scenes:
    scene.x = scene.x - min_x_offset
    scene.y = scene.y - min_y_offset
    print("xy", scene.img_index, scene.x, scene.y)

# find total canvas size needed
img_width = max([scene.x + scene.width for scene in scenes])
img_height = max([scene.y + scene.height for scene in scenes])
print("img_width, img_height", img_width, img_height)


# create image...
target = f"output_{RESOLUTION}.zarr"

# in case we ran the script before, delete the output (useful when testing)
if os.path.exists(target):
    shutil.rmtree(target)

store = parse_url(target, mode="w").store
root = zarr.group(store=store)

# Some values hard-coded
tile_size = 1024
channel_count = 3
d_type = np.uint8

# We only expect & handle 2D, 3-channel images...
shape = (channel_count, img_height, img_width)
chunks = (1, tile_size, tile_size)

row_count = ceil(img_height/tile_size)
col_count = ceil(img_width/tile_size)

# create empty array at root of pyramid
zarray = root.require_dataset(
    "0",
    shape=shape,
    exact=True,
    chunks=chunks,
    dtype=d_type,
)


def get_tile(ch_index, col, row, tile_size):
    # To get a tile, we check each of the Scenes in turn - returns None if no overlap
    # NB: We only get a tile from the 1st scence which overlaps our tile.
    # FIXME: would be better to get data from all scenes and combine them into a tile
    for scene in scenes:
        x = (col * tile_size)
        y = (row * tile_size)
        tile_w = min(tile_size, img_width - x)
        tile_h = min(tile_size, img_height - y)
        tile = scene.get_region(ch_index, x, y, tile_w, tile_h)
        if tile is not None:
            return tile
    

print("row_count", row_count, "col_count", col_count)
# Go through all tiles and write data to "0" array
for ch_index in range(channel_count):
    for row in range(row_count):
        for col in range(col_count):
            tile = get_tile(ch_index, col, row, tile_size)
            if tile is None:
                # No data - leave empty
                continue
            tile_w = tile.shape[-1]
            tile_h = tile.shape[-2]
            y1 = row * tile_size
            y2 = y1 + tile_h
            x1 = col * tile_size
            x2 = x1 + tile_w
            zarray[ch_index, y1:y2, x1:x2] = tile


# We down-sample to generate an image pyramid...
# We could dynamically choose the number of resolutions, but this works for now...
paths = ["0", "1", "2", "3", "4"]
axes = [{"name": "c", "type": "channel"}, {"name": "y", "type": "space"}, {"name": "x", "type": "space"}]

# We have "0" array. This downsamples (in X and Y dims only) to create "1" and "2" etc.
downsample_pyramid_on_disk(root, paths)

transformations = [
    [{"type": "scale", "scale": [1.0, 1.0, 1.0]}],
    [{"type": "scale", "scale": [1.0, 2.0, 2.0]}],
    [{"type": "scale", "scale": [1.0, 4.0, 4.0]}],
    [{"type": "scale", "scale": [1.0, 8.0, 8.0]}],
    [{"type": "scale", "scale": [1.0, 16.0, 16.0]}]
]
datasets = []
for p, t in zip(paths, transformations):
    datasets.append({"path": p, "coordinateTransformations": t})

write_multiscales_metadata(root, datasets, axes=axes)
