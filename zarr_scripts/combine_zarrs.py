
import argparse
import glob
import os
import shutil
import sys
import zarr


"""
This script combines multiple OME-Zarr zarr images into a single zarr time-lapse image.

The input is a directory containing multiple zarr directories, each containing a single timepoint.
Each image is in the 'bioformats2raw' format, with a directory structure like this:

input_dir/time_01.zarr/0/OME/METADATA.ome.xml
input_dir/time_02.zarr/0/OME/METADATA.ome.xml

The xxx.zarr directories can be named in any way that ends with .zarr, but when sorted
by name, they should be in the correct time order.

Usage (requires zarr v2):

$ pip install "zarr>=2.8.1,<3"

$ python combine_zarrs.py path/to/input_dir output.zarr

To check only, use --dry-run:

$ python combine_zarrs.py path/to/input_dir output.zarr --dry-run

"""

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='input dir that contains time*.zarr dirs')
    parser.add_argument('output', help='output.zarr name')
    parser.add_argument('--dry-run', help='Check only, no action', action="store_true")
    parser.add_argument('--overwrite', help='Overwrite existing output', action="store_true")
    args = parser.parse_args(argv)

    dry_run = args.dry_run
    input_dir = args.input
    output_zarr = args.output

    if os.path.exists(output_zarr):
        if args.overwrite and not dry_run:
            shutil.rmtree(output_zarr)
        else:
            print(f"Output zarr {output_zarr} exists. Use --overwrite to remove it.")
            sys.exit(1)
        
    zarr_dirs = glob.glob(os.path.join(input_dir, '*.zarr'))
    zarr_dirs = [os.path.join(input_dir, d) for d in zarr_dirs if os.path.isdir(d)]
    zarr_dirs.sort()
    print('zarr_dirs', zarr_dirs)
    size_t = len(zarr_dirs)
    print(f'Found {len(zarr_dirs)} zarr dirs')

    # create a new zarr group
    if not dry_run:
        store = zarr.DirectoryStore(output_zarr)
        root = zarr.group(store=store)

    # for each dataset resolution...
    # create a new zarr array
    zarr1 = os.path.join(zarr_dirs[0], '0')

    # go through each dataset (pyramid level) in the first zarr
    # and copy the arrays to the new zarr group, with new size_t
    dataset_paths = []
    for dataset in os.listdir(zarr1):
        dir_path = os.path.join(zarr1, dataset)
        if os.path.isdir(dir_path):
            print('dir_path', dir_path)
            arr = zarr.open(dir_path, mode='r')
            print('arr', dataset, arr)
            assert arr.shape[0] == 1, "Only single-timepoint data supported"
            new_shape = (size_t,) + arr.shape[1:]
            if not dry_run:
                # Create an empty zarr array for each dataset
                root.create_dataset(shape=new_shape, dtype=arr.dtype, chunks=arr.chunks, name=dataset, dimension_separator='/')
            dataset_paths.append(dataset)

    dataset_paths.sort()

    # copy multiscales group for .zarr/
    if not dry_run:
        attr1 = os.path.join(zarr_dirs[0], '0', '.zattrs')
        group1 = os.path.join(zarr_dirs[0], '0', '.zgroup')
        shutil.copy(attr1, os.path.join(output_zarr, '.zattrs'))
        shutil.copy(group1, os.path.join(output_zarr, '.zgroup'))

    pyramid_shapes = []

    # for each timepoint, symlink the data from the
    for the_t, time_dir in enumerate(zarr_dirs):
        print('time_dir', the_t, time_dir)

        for ds_index, dataset in enumerate(dataset_paths):
            # each dir has a Z-stack (single timepoint)
            series = "0"
            t = "0"

            # check that the shape is the same for all timepoints
            arr_path = os.path.join(time_dir, series, dataset)
            shape = zarr.open(arr_path, mode='r').shape
            if len(pyramid_shapes) <= ds_index:
                # first time through
                pyramid_shapes.append(shape)
            else:
                assert pyramid_shapes[ds_index] == shape, f"Shape mismatch at timepoint {the_t} dataset {dataset}: {shape} != {pyramid_shapes[ds_index]}"

            # copy or move the data
            t_path = os.path.join(time_dir, series, dataset, t)
            print('Copy', t_path, "->", f'{output_zarr}/{dataset}/{the_t}')
            if not dry_run:
                # Had some issues with creating symlinks...
                # os.symlink(t_path, f'{output_zarr}/{dataset}/{the_t}', target_is_directory=True)

                # Copying instead of symlinking works!
                # shutil.copytree(t_path, os.path.join(output_zarr, dataset, str(the_t)))

                # Or we can MOVE the data... (destroying the original zarrs)
                shutil.move(t_path, os.path.join(output_zarr, dataset, str(the_t)))


if __name__ == '__main__':
    main(sys.argv[1:])
