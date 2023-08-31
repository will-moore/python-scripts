
# from https://github.com/ome/ome-zarr-py/issues/219

import os.path
import numpy as np
import zarr
import shutil
from ome_zarr.writer import write_image
from ome_zarr.io import parse_url
from ome_zarr.io import ZarrLocation
from ome_zarr.reader import Multiscales, Reader
from ome_zarr.format import CurrentFormat
import dask.array.core

im = np.random.normal(size=(3, 100, 100))
fmt = CurrentFormat()

## write
def write_to_zarr(im, f):
    if os.path.isdir(f):
        shutil.rmtree(f)
    store = parse_url(f, mode="w").store
    group = zarr.group(store=store)
    write_image(im, group, axes=["c", "x", "y"], fmt=fmt, storage_options={'compressor': None})


write_to_zarr(im, "debug0.zarr")

# ## read
# reader = parse_url("debug0.zarr", mode="r")
# multiscale = reader.root_attrs["multiscales"][0]
# # read full-size resolution
# data = reader.load(multiscale["datasets"][0]["path"])
# print("data", data)

loc = ZarrLocation("debug0.zarr")
# loc = ZarrLocation("testimage")
reader = Reader(loc)()
nodes = list(reader)
print("nodes", len(nodes), nodes)
# assert len(nodes) == 1
node = nodes[0]
im_read = node.load(Multiscales).array(resolution="0", version=fmt.version)

## write again (error)
write_to_zarr(im_read, "debug1.zarr")
# write_to_zarr(data, "debug1.zarr")

##
import xarray as xr
xr.DataArray(im).chunks
