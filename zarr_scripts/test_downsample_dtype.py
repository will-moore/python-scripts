
# https://github.com/ome/ome-zarr-py/issues/217

import numpy as np
import ome_zarr
import ome_zarr.scale
import ome_zarr.writer
import zarr

vol = np.random.randint(0, 1000, size=(32, 256, 256)).astype("uint16")

scaler = ome_zarr.scale.Scaler()
mip = scaler.local_mean(vol)

loc = ome_zarr.io.parse_url("./data", mode="w")
group = zarr.group(loc.store)

axes = [ 
    {"name": "z", "type": "space", "unit": "micrometer"},
    {"name": "y", "type": "space", "unit": "micrometer"},
    {"name": "x", "type": "space", "unit": "micrometer"},
]
ome_zarr.writer.write_multiscale(mip, group, axes=axes)
