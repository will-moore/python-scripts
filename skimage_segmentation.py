
import omero
from omero.gateway import BlitzGateway
from omero.rtypes import rint, rstring

from skimage import morphology
from skimage import measure
from skimage.filters import threshold_otsu
from skimage.util import invert
import matplotlib.pyplot as plt

# Adapted from https://gist.github.com/stefanv/7c296c26b0c3624746f4317bed6a3540

# Tested with https://downloads.openmicroscopy.org/images/SVS/77928.svs
# Using threshold = 200 and start_x = 5000, start_y = 5000, cols = 40, rows = 40
# this will produce about 250,000 shapes.

from omero.cli import cli_login

TILE_SIZE = 1000


def rgba_to_int(red, green, blue, alpha=255):
    """ Return the color as an Integer in RGBA encoding """
    r = red << 24
    g = green << 16
    b = blue << 8
    a = alpha
    rgba_int = r+g+b+a
    if (rgba_int > (2**31-1)):       # convert to signed 32-bit int
        rgba_int = rgba_int - 2**32
    return rgba_int

def add_polygon(contour, x_offset, y_offset):
    """ points is 2D list of [[x, y], [x, y]...]"""

    points = ["%s,%s" % (xy[1] + x_offset, xy[0] + y_offset) for xy in contour]
    points = ", ".join(points)

    polygon = omero.model.PolygonI()
    polygon.theZ = rint(0)
    polygon.theT = rint(0)
    polygon.strokeColor = rint(rgba_to_int(255, 255, 0))
    # points = "10,20, 50,150, 200,200, 250,75"
    polygon.points = rstring(points)
    roi = omero.model.RoiI()
    # use the omero.model.ImageI that underlies the 'image' wrapper
    roi.setImage(image._obj)
    roi.addShape(polygon)
    # Save the ROI (saves any linked shapes too)
    updateService.saveObject(roi)


with cli_login() as cli:
    conn = BlitzGateway(client_obj=cli._client)
    updateService = conn.getUpdateService()

    image_id = 3165
    image = conn.getObject("Image", image_id)
    pixels = image.getPrimaryPixels()

    size_x = image.getSizeX()
    size_y = image.getSizeY()

    # Hard-code some values...
    # TODO: use size_x and size_y to interate over whole image
    start_x = 5000
    start_y = 5000
    cols = 40
    rows = 40

    channel = 2
    threshold = 200

    total = 0
    tiles = 0
    for col in range(cols):
        for row in range(rows):
            tiles += 1
            x = start_x + (col * TILE_SIZE)
            y = start_y + (row * TILE_SIZE)
            tile = pixels.getTile(theC=channel, tile=(x, y, TILE_SIZE, TILE_SIZE))
            # nuclei are black...
            tile = invert(tile)

            # threshold = threshold_otsu(tile)
            # print('Threshold', threshold)
            mask = tile < threshold
            mask = morphology.remove_small_objects(mask, min_size=10)
            mask = morphology.binary_dilation(mask)
            mask = morphology.binary_dilation(mask)
            mask = morphology.remove_small_holes(mask)
            contours = measure.find_contours(mask, 0)
            print('Found %s contours', len(contours))
            total += len(contours)

            # Used this and threshold_otsu above to find a good threshold value
            # that gives a resonable number of polygons per tile. Then hard-coded it
            # to be the same for the whole image.

            # while len(contours) > 200:
            #     threshold += 5
            #     print('Threshold', threshold)
            #     mask = tile < threshold
            #     mask = morphology.remove_small_objects(mask, min_size=10)
            #     mask = morphology.binary_dilation(mask)
            #     mask = morphology.binary_dilation(mask)
            #     mask = morphology.remove_small_holes(mask)
            #     contours = measure.find_contours(mask, 0)
            #     print('Found %s contours', len(contours))

            print('total ROIS:', total, 'tiles', tiles)
            for c in contours:
                add_polygon(c, x, y)
