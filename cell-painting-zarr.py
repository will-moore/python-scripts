

from ome_zarr.io import parse_url
from ome_zarr.reader import Reader
import numpy as np
from datetime import datetime
from PIL import Image

url = "https://cellpainting-gallery.s3.amazonaws.com/cpg0004-lincs/broad/images/2016_04_01_a549_48hr_batch1/images_zarr/SQ00014812__2016-05-23T20_44_31-Measurement1.ome.zarr/A/1/0/"

# read the image data
store = parse_url(url, mode="r").store

reader = Reader(parse_url(url))
# nodes may include images, labels etc
nodes = list(reader())
# first node will be the image pixel data
image_node = nodes[0]

pyramid = image_node.data
dask_data = pyramid[-1]

display_min = 0
display_max = 1000

def display(image, display_min, display_max): # copied from Bi Rico
    # https://stackoverflow.com/questions/14464449/using-numpy-to-efficiently-convert-16-bit-image-data-to-8-bit-for-display-with
    image.clip(display_min, display_max, out=image)
    image -= display_min
    np.floor_divide(image, (display_max - display_min + 1) / 256,
                    out=image, casting='unsafe')
    return image.astype(np.uint8)

def render_plane(dask_data, z, c, t, window=None):
    # -> 2D, also slice top/left quarter
    channel0 = dask_data[t, c, z, :1000, :1000]
    print(channel0.shape)

    start = datetime.now()
    channel0 = channel0.compute()

    if window is None:
        min_val = channel0.min()
        print("min", min_val)

        print(datetime.now() - start)
        start = datetime.now()

        max_val = channel0.max()
        print("max", max_val)
        window = [min_val, max_val]

    print(datetime.now() - start)
    return display(channel0, window[0], window[1])


def setActiveChannels(dask_data, channels, colors, windows=None):
    # colors are (r, g, b)
    rgb_plane = None

    the_z = 0
    the_t = 0
    for ch_index, color in zip(channels, colors):
        print("----", ch_index, color)
        plane = render_plane(dask_data, the_t, ch_index, the_z)
        if rgb_plane is None:
            rgb_plane = np.zeros((*plane.shape, 3), np.uint16)
        for index, fraction in enumerate(color):
            if fraction > 0:
                rgb_plane[:, :, index] += (fraction * plane)

    rgb_plane.clip(0, 255, out=rgb_plane)
    return rgb_plane.astype(np.uint8)

# rgb = np.dstack((red, green, blue))
colors = [
    (0, 1, 1),
    (1, 1, 0),
    (1, 0, 1),
    (1, 0, 0),
    (0, 1, 0)
]
rgb = setActiveChannels(dask_data, [0, 1, 2, 3, 4], colors)

img = Image.fromarray(rgb)
img.show()
