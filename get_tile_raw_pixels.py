
import numpy as np
from omero.gateway import BlitzGateway
from omero.model import enums as omero_enums

conn = BlitzGateway('username', 'password', port=4064, host='localhost')
conn.connect()



PIXEL_TYPES = {
    omero_enums.PixelsTypeint8: np.int8,
    omero_enums.PixelsTypeuint8: np.uint8,
    omero_enums.PixelsTypeint16: np.int16,
    omero_enums.PixelsTypeuint16: np.uint16,
    omero_enums.PixelsTypeint32: np.int32,
    omero_enums.PixelsTypeuint32: np.uint32,
    omero_enums.PixelsTypefloat: np.float32,
    omero_enums.PixelsTypedouble: np.float64,
}

IMAGE_ID = 2566
image = conn.getObject("image", IMAGE_ID)
print('image', image.name)

pixels = image.getPrimaryPixels()
dtype = PIXEL_TYPES.get(pixels.getPixelsType().value, None)

pix = image._conn.c.sf.createRawPixelsStore()
pid = image.getPixelsId()
level = 0
z, c, t, x, y = (0, 0, 0, 0, 0)

try:
    pix.setPixelsId(pid, False)

    # Get info on number of levels and sizes
    print([(r.sizeX, r.sizeY) for r in pix.getResolutionDescriptions()])

    pix.setResolutionLevel(2)
    print(pix.getTileSize())
    w, h = pix.getTileSize()
    tile = pix.getTile(z, c, t, x, y, w, h)
finally:
    pix.close()

tile = np.frombuffer(tile, dtype=dtype)
tile = tile.reshape((h, w))

print(tile.shape)

