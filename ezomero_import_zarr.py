

import numpy as np
import zarr
import ezomero

from ome_zarr.io import parse_url
from ome_zarr.writer import write_image

# from https://forum.image.sc/t/images-batch-import-into-a-dataset-in-omero-using-ezomero-2-1-0/89529/12

def test_import(conn):

    # generate numpy data...
    # shape = (1, 4, 15, 9247, 8332)
    shape = (1, 2, 3, 1500, 3000)
    mean_val=10
    rng = np.random.default_rng(0)
    data = rng.poisson(mean_val, size=shape).astype(np.uint8)
    print(data.shape)

    # # write to ome-zarr...
    filename = "medium_image.zarr"
    chunks = (1, 1, 1, 1024, 1024)
    store = parse_url(filename, mode="w").store
    root = zarr.group(store=store)
    write_image(image=data, group=root, axes="tczyx", storage_options=dict(chunks=chunks))

    # import...
    id_image = ezomero.ezimport(conn=conn, target=filename, dataset=451)
    print('id_image', id_image)


if __name__ == '__main__':
    conn = ezomero.connect()
    test_import(conn)
