# https://github.com/ome/ome-zarr-py/issues/297

import dask.array as da
from ome_zarr.io import parse_url
from ome_zarr.reader import Reader

location = parse_url("51.ome.zarr/")
reader = Reader(location)

data = next(reader()).data[0]
print("data", data)
# this passes
assert isinstance(data, da.Array), type(data)

result = data.compute()
# this fails
print("result", result)
assert not isinstance(result, da.Array), type(result)
