
import omero
from omero.gateway import BlitzGateway
from omero.rtypes import rint, rstring

from skimage import morphology
from skimage import measure

# Adapted from https://gist.github.com/stefanv/7c296c26b0c3624746f4317bed6a3540

conn = BlitzGateway('user-3', 'ome', port=4064, host='merge-ci-devspace.openmicroscopy.org')
conn.connect()
updateService = conn.getUpdateService()


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

def add_polygon(contour, x_offset=0, y_offset=0):
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

total = 0
img_count = 0

threshold = 25
# plate = conn.getObject("Plate", plate_id)
# images = get_images_from_plate(plate)

dataset = conn.getObject('Dataset', 17371)
images = dataset.listChildren()

for image in images:
    pixels = image.getPrimaryPixels()
    plane = pixels.getPlane(theC=0)
    mask = plane < threshold
    mask = morphology.remove_small_objects(mask, min_size=10)
    mask = morphology.binary_dilation(mask)
    mask = morphology.binary_dilation(mask)
    mask = morphology.remove_small_holes(mask)
    contours = measure.find_contours(mask, 0)
    print('Found contours:', len(contours))
    total += len(contours)
    img_count += 1
    print('Total shapes:', total, "images:", img_count)
    for c in contours:
        add_polygon(c)
