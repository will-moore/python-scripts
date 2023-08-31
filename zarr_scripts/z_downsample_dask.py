

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
import dask.array as da

from skimage.transform import resize
from ome_zarr.dask_utils import resize as dask_resize
from ome_zarr.scale import Scaler

class Zscaler(Scaler):

    def resize_image(self, image):
        """
        Resize a numpy array OR a dask array to a smaller array (not pyramid)
        """
        if isinstance(image, da.Array):

            def _resize(image, out_shape, **kwargs):
                return dask_resize(image, out_shape, **kwargs)

        else:
            _resize = resize

        print("resize image...", image.shape)
        # down-sample in X, Y and Z dimensions...
        new_shape = list(image.shape)
        new_shape[-1] = image.shape[-1] // self.downscale
        new_shape[-2] = image.shape[-2] // self.downscale
        new_shape[-3] = image.shape[-3] // self.downscale

        print('sizeZ', image.shape[-3], self.downscale)
        out_shape = tuple(new_shape)
        print("out_shape", out_shape)
        # This gives e.g. because each chunk is e.g. 1, 1, y, x
        # and you can't downscale each chunk in Z (2, 0, 137, 135)
        # Then this fails on the next iteration image.shape[-3] // self.downscale

        dtype = image.dtype
        image = _resize(
            image.astype(float), out_shape, order=1, mode="reflect", anti_aliasing=False
        )
        return image.astype(dtype)


fmt = CurrentFormat()

def write_to_zarr(im, f, axes):
    if os.path.isdir(f):
        shutil.rmtree(f)
    store = parse_url(f, mode="w").store
    group = zarr.group(store=store)
    write_image(im, group, scaler=Zscaler(), axes=axes, fmt=fmt, storage_options={'compressor': None})


loc = ZarrLocation("/Users/wmoore/Desktop/ZARR/data/6001240.zarr")
reader = Reader(loc)()
nodes = list(reader)
print("nodes", len(nodes), nodes)
node = nodes[0]
print('metadata', node.metadata)

im_read = node.load(Multiscales).array(resolution="0", version=fmt.version)

write_to_zarr(im_read, "6001240_z.zarr", node.metadata["axes"])
