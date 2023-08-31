
import os
import dask.array as da

from ome_zarr.dask_utils import resize as da_resize

def downsample_pyramid_on_disk(original_image, group_path, paths):
    """
    Takes a high-resolution Dask array at original_image
    and down-samples it by a factor of 2 for each of the paths
    """

    for count, path in enumerate(paths):
        print("count", count, "path", path)
        target_path = os.path.join(group_path, path)
        if os.path.exists(target_path):
            print("path exists: %s" % target_path)
            continue
        # open previous resolution from disk via dask...
        if count == 0:
            dask_image = original_image
        else:
            path_to_array = os.path.join(group_path, paths[count - 1])
            print("read from", path_to_array)
            dask_image = da.from_zarr(path_to_array)

        # resize in X, Y and Z
        dims = list(dask_image.shape)
        dims[-1] = dims[-1] // 2
        dims[-2] = dims[-2] // 2
        dims[-3] = dims[-3] // 2
        output = da_resize(
            dask_image, tuple(dims), preserve_range=True, anti_aliasing=False
        )

        # write to disk
        print("writing", group_path, path)
        da.to_zarr(arr=output, url=group_path, component=path, dimension_separator="/")

    return paths

# url = "https://minio-dev.openmicroscopy.org/idr/v0.4/idr0077/9836832_z_dtype_fix.zarr/0"
url = "9836832_z_dtype_fix.zarr/0"
original_image = da.from_zarr(url)

downsample_pyramid_on_disk(original_image, "9836832_z_dtype_fix.zarr", ["1", "2", "3", "4", "5"])

