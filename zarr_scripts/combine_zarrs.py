
import argparse
import glob
import os
import shutil
import sys
import zarr


"""
This script combines multiple OME-Zarr zarr single C/T images into a single zarr time-lapse image.

The input is a directory containing multiple zarr directories, each containing a single Z-stack.
Each image is in the 'bioformats2raw' format, with a directory structure like this:

fused_tp_1_ch1.zarr
fused_tp_1_ch2.zarr
fused_tp_2_ch1.zarr
fused_tp_2_ch2.zarr…etc

The range of timepoints and channels is specified in the zarr_name argument...

e.g. fused_tp_<T:1-123>_ch<C:1-2>.zarr specifies timepoints 1-123 and channels 1-2
The first frame will be "fused_tp_1_ch1.zarr"
The last frame will be "fused_tp_123_ch2.zarr"

e.g. fused_tp_<T:000-055>_ch<C:0-1>.zarr specifies timepoints 0-55 and channels 0-1
The first frame will be "fused_tp_000_ch0.zarr"
The last frame will be "fused_tp_055_ch1.zarr"


Usage (requires zarr v2):

$ pip install "zarr>=2.8.1,<3"

$ python combine_zarrs.py path/to/input_dir output.zarr "fused_tp_<T:1-123>_ch<C:1-2>.zarr"

To check only, use --dry-run:

$ python combine_zarrs.py path/to/input_dir "fused_tp_<T:1-123>_ch<C:1-2>.zarr" output.zarr --dry-run

"""

def get_t_range(zarr_name):
    # E.g. fused_tp_<T:000-055>_ch<C:0-1>.zarr
    # Find the first <T:...> and extract the range
    t_start = zarr_name.find('<T:')
    if t_start == -1:
        return 1
    t_end = zarr_name.find('>', t_start)
    t_range = zarr_name[t_start+3:t_end]
    t_range = t_range.split('-')
    assert len(t_range[0]) == len(t_range[1]), "Timepoint range must have the same number of digits"
    return [int(t_range[0]), int(t_range[1])]


def get_c_range(zarr_name):
    # E.g. fused_tp_<T:000-055>_ch<C:0-1>.zarr
    # Find the first <C:...> and extract the range
    c_start = zarr_name.find('<C:')
    if c_start == -1:
        return 1
    c_end = zarr_name.find('>', c_start)
    c_range = zarr_name[c_start+3:c_end]
    c_range = c_range.split('-')
    assert len(c_range[0]) == len(c_range[1]), "Channel range must have the same number of digits"
    return [int(c_range[0]), int(c_range[1])]


def get_zarr_name(the_t, the_c, zarr_name):
    # E.g. fused_tp_<T:000-055>_ch<C:0-1>.zarr
    # Replace <T:...> and <C:...> with the actual values
    t_start = zarr_name.find('<T:')
    if t_start == -1:
        return 1
    t_end = zarr_name.find('>', t_start)
    t_range = zarr_name[t_start+3:t_end]
    t_digits = len(t_range.split('-')[0])
    
    c_start = zarr_name.find('<C:')
    if c_start == -1:
        return 1
    c_end = zarr_name.find('>', c_start)
    c_range = zarr_name[c_start+3:c_end]
    c_digits = len(c_range.split('-')[0])

    zarr_name = zarr_name.replace(f'<T:{t_range}>', f'{the_t:0{t_digits}d}')
    zarr_name = zarr_name.replace(f'<C:{c_range}>', f'{the_c:0{c_digits}d}')
    return zarr_name


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='input dir that contains time*.zarr dirs')
    parser.add_argument('output', help='output.zarr name')
    parser.add_argument('zarr_name', help='E.g. fused_tp_<T:000-055>_ch<C:0-1>.zarr')
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
        
    zarr_name = args.zarr_name
    t_range = get_t_range(zarr_name)
    c_range = get_c_range(zarr_name)
    size_t = t_range[1] - t_range[0] + 1
    size_c = c_range[1] - c_range[0] + 1
    print('t_range', t_range)
    print('c_range', c_range)

    # create a new zarr group
    if not dry_run:
        store = zarr.DirectoryStore(output_zarr)
        root = zarr.group(store=store)

    # Use first zarr to get the dataset paths
    first_name = get_zarr_name(t_range[0], c_range[0], zarr_name)
    print('first_name', first_name)
    zarr1 = os.path.join(input_dir, first_name, '0')

    # go through each dataset (pyramid level) in the first zarr
    # to get the shape of the data
    # Create an empty zarr array for each dataset in output,
    # with new size_t, size_c
    dataset_paths = []
    for dataset in os.listdir(zarr1):
        dir_path = os.path.join(zarr1, dataset)
        if os.path.isdir(dir_path):
            print('dir_path', dir_path)
            arr = zarr.open(dir_path, mode='r')
            print('arr', dataset, arr)
            assert len(arr.shape) == 5, "Only 5D data supported"
            assert arr.shape[0] == 1, "Only single-timepoint data supported"
            assert arr.shape[1] == 1, "Only single channel data supported"
            new_shape = (size_t, size_c) + arr.shape[2:]
            if not dry_run:
                # Create an empty zarr array for each dataset
                root.create_dataset(shape=new_shape, dtype=arr.dtype, chunks=arr.chunks, name=dataset, dimension_separator='/')
            dataset_paths.append(dataset)

    dataset_paths.sort()

    # copy multiscales group for .zarr/
    if not dry_run:
        attr1 = os.path.join(zarr1, '.zattrs')
        group1 = os.path.join(zarr1, '.zgroup')
        shutil.copy(attr1, os.path.join(output_zarr, '.zattrs'))
        shutil.copy(group1, os.path.join(output_zarr, '.zgroup'))

    pyramid_shapes = []

    # for each timepoint and channel, copy or move the data
    for the_t in range(size_t):
        for the_c in range(size_c):
            in_zarr = os.path.join(input_dir, get_zarr_name(the_t + t_range[0], the_c + c_range[0], zarr_name))

            for ds_index, dataset in enumerate(dataset_paths):
                # each dir has a Z-stack (single timepoint)
                series = "0"
                t = "0"
                c = "0"

                # construct the paths
                in_path = os.path.join(in_zarr, series, dataset, t, c)
                out_path = os.path.join(output_zarr, dataset, str(the_t), str(the_c))
                print('Copy', in_path, "->", out_path)
                if not os.path.exists(in_path):
                    print(f"MISSING {in_path}")
                    continue

                # check that the shape is the same for all timepoints
                arr_path = os.path.join(in_zarr, series, dataset)
                shape = zarr.open(arr_path, mode='r').shape
                if len(pyramid_shapes) <= ds_index:
                    # first time through
                    pyramid_shapes.append(shape)
                else:
                    assert pyramid_shapes[ds_index] == shape, f"Shape mismatch at timepoint {the_t} dataset {dataset}: {shape} != {pyramid_shapes[ds_index]}"

                if not dry_run:
                    # Had some issues with creating symlinks...
                    # os.symlink(in_path, f'{output_zarr}/{dataset}/{the_t}', target_is_directory=True)

                    # Copying instead of symlinking works!
                    shutil.copytree(in_path, out_path)

                    # Or we can MOVE the data... (destroying the original zarrs)
                    # shutil.move(in_path, out_path)


if __name__ == '__main__':
    main(sys.argv[1:])
