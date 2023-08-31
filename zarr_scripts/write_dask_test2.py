import os.path
import shutil

import dask.array.core
import numpy as np
import zarr
from ome_zarr.format import CurrentFormat
from ome_zarr.io import ZarrLocation, parse_url
from ome_zarr.reader import Multiscales, Reader
from ome_zarr.writer import write_image
import filecmp

im = np.random.normal(size=(3, 100, 100))
fmt = CurrentFormat()

# write
input_img = "debug2.zarr"
output_img = "debug4.zarr"

def write_to_zarr(im, f):
    if os.path.isdir(f):
        shutil.rmtree(f)
    store = parse_url(f, mode="w").store
    group = zarr.group(store=store)
    if isinstance(im, np.ndarray) or isinstance(im, dask.array.core.Array):
        write_image(im, group, axes=["c", "x", "y"], fmt=fmt, storage_options={"compressor": None})
    else:
        raise ValueError("the array to write must be a numpy array or a dask array")

# allow use of existing data if it exists...
if not os.path.isdir(input_img):
    write_to_zarr(im, input_img)

# read
loc = ZarrLocation(input_img)
reader = Reader(loc)()
nodes = list(reader)
# assert len(nodes) == 1
node = nodes[0]
im_read = node.load(Multiscales).array(resolution="0", version=fmt.version)


# write again (error)
write_to_zarr(im_read, output_img)

# from stackoverflow
class dircmp(filecmp.dircmp):  # type: ignore[type-arg]
    """
    Compare the content of dir1 and dir2. In contrast with filecmp.dircmp, this
    subclass compares the content of files with the same path.
    """

    def phase3(self) -> None:
        """
        Find out differences between common files.
        Ensure we are using content comparison with shallow=False.
        """
        fcomp = filecmp.cmpfiles(self.left, self.right, self.common_files, shallow=False)
        self.same_files, self.diff_files, self.funny_files = fcomp


def are_directories_identical(dir1, dir2):
    compared = dircmp(dir1, dir2)
    if compared.left_only or compared.right_only or compared.diff_files or compared.funny_files:
        print('compared.left_only', compared.left_only)
        print('compared.right_only', compared.right_only)
        print('compared.diff_files', compared.diff_files)
        print('compared.funny_files', compared.funny_files)
        return False

    for subdir in compared.common_dirs:
        if not are_directories_identical(
            os.path.join(dir1, subdir),
            os.path.join(dir2, subdir),
        ):
            print("DIFF", os.path.join(dir1, subdir), os.path.join(dir2, subdir))
            return False
    return True

# inspect the content of the files to manually check for numerical approximation errors
# if the output matrices are not close up to the machine precision, then the difference is not due to numerical errors
loc = ZarrLocation(input_img)
reader = Reader(loc)()
nodes = list(reader)
# assert len(nodes) == 1
node = nodes[0]
im_read = node.load(Multiscales).array(resolution="1", version=CurrentFormat().version)

loc = ZarrLocation(output_img)
reader = Reader(loc)()
nodes = list(reader)
# assert len(nodes) == 1
node = nodes[0]
im_read2 = node.load(Multiscales).array(resolution="1", version=CurrentFormat().version)
print(im_read[:5, :5, 0].compute())
print(im_read2[:5, :5, 0].compute())

##
assert are_directories_identical(input_img, output_img)