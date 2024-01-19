


import numpy as np

from omero.cli import cli_login
from omero.gateway import BlitzGateway

from omero.model.enums import PixelsTypeint8, PixelsTypeint16
from omero.model.enums import PixelsTypeuint16, PixelsTypeint32
from omero.model.enums import PixelsTypefloat
from omero.model.enums import PixelsTypecomplex, PixelsTypedouble
from omero.util.tiles import TileLoopIteration, RPSTileLoop
from omero.model import PixelsI

# see https://forum.image.sc/t/images-batch-import-into-a-dataset-in-omero-using-ezomero-2-1-0/89529/12

# WARNING - currently this script fails with....
# Traceback (most recent call last):
#   File "/Users/wmoore/Desktop/python-scripts/ezomero_import_zarr.py", line 120, in <module>
#     test_import(conn)
#   File "/Users/wmoore/Desktop/python-scripts/ezomero_import_zarr.py", line 47, in test_import
#     create_image_from_tiles(conn, data, img_name)
#   File "/Users/wmoore/Desktop/python-scripts/ezomero_import_zarr.py", line 106, in create_image_from_tiles
#     loop.forEachTile(tile_size, tile_size, Iteration())
#   File "/Users/wmoore/Desktop/PY/omero-py/target/omero/util/tiles.py", line 207, in forEachTile
#     return TileLoop.forEachTile(
#   File "/Users/wmoore/Desktop/PY/omero-py/target/omero/util/tiles.py", line 114, in forEachTile
#     iteration.run(data, z, c, t,
#   File "/Users/wmoore/Desktop/python-scripts/ezomero_import_zarr.py", line 102, in run
#     data.setTile(tile2d, z, c, t, x, y, tile_width, tile_height)
#   File "/Users/wmoore/Desktop/PY/omero-py/target/omero/util/tiles.py", line 135, in setTile
#     self.rps.setTile(buffer, z, c, t, x, y, w, h)
#   File "/Users/wmoore/Desktop/PY/omero-py/target/omero_api_RawPixelsStore_ice.py", line 1361, in setTile
#     return _M_omero.api.RawPixelsStore._op_setTile.invoke(self, ((buf, z, c, t, x, y, w, h), _ctx))
# ValueError: invalid value for element 0 of sequence<byte>

def test_import(conn):
    # generate numpy data...
    shape = (1, 2, 2, 1500, 3000)
    mean_val=10
    rng = np.random.default_rng(0)
    data = rng.poisson(mean_val, size=shape).astype(np.uint8)
    print(data.shape)
    img_name = "create_image_from_tiles: %s" % str(data.shape)
    create_image_from_tiles(conn, data, img_name)


def create_image_from_tiles(conn, numpy_5d, image_name, description=None, tile_size=1024):

    pixels_service = conn.getPixelsService()
    query_service = conn.getQueryService()
    img_shape = numpy_5d.shape
    size_x = img_shape[-1]
    size_y = img_shape[-2]
    size_z = img_shape[-3]
    size_c = img_shape[-4]
    size_t = img_shape[-5]

    pTypes = {'int8': PixelsTypeint8,
                'int16': PixelsTypeint16,
                'uint16': PixelsTypeuint16,
                'int32': PixelsTypeint32,
                'float_': PixelsTypefloat,
                'float8': PixelsTypefloat,
                'float16': PixelsTypefloat,
                'float32': PixelsTypefloat,
                'float64': PixelsTypedouble,
                'complex_': PixelsTypecomplex,
                'complex64': PixelsTypecomplex}
    dType = numpy_5d.dtype.name
    if dType not in pTypes:  # try to look up any not named above
        pType = dType
    else:
        pType = pTypes[dType]
    # omero::model::PixelsType
    pixelsType = query_service.findByQuery(
        "from PixelsType as p where p.value='%s'" % pType, None)
    if pixelsType is None:
        raise Exception(
            "Cannot create an image in omero from numpy array "
            "with dtype: %s" % dType)
    channelList = list(range(size_c))
    iid = pixels_service.createImage(
        size_x, size_y, size_z, size_t, channelList, pixelsType,
        image_name, description, conn.SERVICE_OPTS)

    new_image = conn.getObject("Image", iid)

    def get_tile(t, c, z, y, x):
        return numpy_5d[t, c, z, y:tile_size, x:tile_size]


    class Iteration(TileLoopIteration):

        def run(self, data, z, c, t, x, y, tile_width, tile_height, tile_count):
            tile2d = get_tile(t, c, z, y, x)
            print("x, y, z, c, t", x, y, z, c, t)
            print(tile2d)
            print(tile2d.shape, tile2d.dtype)
            data.setTile(tile2d, z, c, t, x, y, tile_width, tile_height)

    pid = new_image.getPixelsId()
    loop = RPSTileLoop(conn.c.sf, PixelsI(pid, False))
    loop.forEachTile(tile_size, tile_size, Iteration())

    return new_image


if __name__ == '__main__':
    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        print("conn", conn)
        test_import(conn)

