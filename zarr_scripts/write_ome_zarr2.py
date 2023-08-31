from ome_zarr.writer import write_image
import numpy
import zarr


store = zarr.DirectoryStore("/tmp/blah.zarr")
img_group = zarr.group(store=store)
img = numpy.zeros((123, 456, 1), dtype="uint8")

# now knowing that this axisorder is not supported
# I'd still expect a meaningful Exception here...
# not LinAlgError: SVD did not converge
write_image(img, img_group, axes="yxc")
