# https://forum.image.sc/t/how-do-i-save-an-image-in-zarr-format-using-python-and-retain-my-size-metadata/103627

import numpy as np
import zarr
import os

from ome_zarr.io import parse_url
from ome_zarr.writer import write_multiscale

path = "test_ngff_image_with_ct.zarr"
os.mkdir(path)

# Some 5D data...
size_xy = 128
size_z = 10
size_t = 2
size_c = 3
rng = np.random.default_rng(0)
data = rng.poisson(lam=10, size=(size_t, size_c, size_z,
                   size_xy, size_xy)).astype(np.uint8)

# zarr store and group
store = parse_url(path, mode="w").store
root = zarr.group(store=store)

# prepare metadata
pix_size_x = 0.45
pix_size_y = 0.45
pix_size_z = 1.1
time_interval = 1.25

coordinate_transformations = [
    # A single resolution level. If we had more pyramid levels, we'd have more lists here,
    # and the 'pixel sizes' would be e.g. 2 x bigger for each level
    [{"scale": [time_interval, 1, pix_size_z, pix_size_y, pix_size_x], "type": "scale"}]
]

axes = [
    {
        "name": "t",
        "type": "time",
        "unit": "second"
    },
    {
        "name": "c",
        "type": "channel"
    },
    {
        "name": "z",
        "type": "space"
    },
    {
        "unit": "micrometer",
        "name": "y",
        "type": "space"
    },
    {
        "unit": "micrometer",
        "name": "x",
        "type": "space"
    }
]

# write the image data - note the pyramid=[data] is a single resolution level
# If pyramid is a list of nd-arrays, each nd-array is a resolution level
write_multiscale(pyramid=[data], group=root, coordinate_transformations=coordinate_transformations,
            axes=axes, storage_options=dict(chunks=(1, size_xy, size_xy)))

# add channel label & color...
# min/max are the pixel instensity range for each channel
# start/end are the display range for each channel
root.attrs["omero"] = {
    "channels": [{
        "color": "0000FF",
        "label": "DAPI",
        "active": True,
        "window": {"min": 0, "max": 500, "start": 0, "end": 255}
    }, {
        "color": "00FF00",
        "label": "GPF",
        "active": True,
        "window": {"min": 0, "max": 500, "start": 0, "end": 255}
    }, {
        "color": "FF0000",
        "label": "Red",
        "active": True,
        "window": {"min": 0, "max": 500, "start": 0, "end": 255}
    }]
}
