
import omero
from omero.gateway import BlitzGateway
from omero.rtypes import rint, rstring

from skimage import morphology
from skimage import measure

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

def add_polygon(contour):
    """ points is 2D list of [[x, y], [x, y]...]"""
    # format points like "10,20, 50,150, 200,200, 250,75"
    points = ["%s,%s" % (xy[1], xy[0]) for xy in contour]
    points = ", ".join(points)

    polygon = omero.model.PolygonI()
    polygon.strokeColor = rint(rgba_to_int(255, 255, 0))
    polygon.points = rstring(points)
    roi = omero.model.RoiI()
    roi.setImage(image._obj)
    roi.addShape(polygon)
    updateService.saveObject(roi)


dataset_id = 5220
dataset = conn.getObject("Dataset", dataset_id)
for image in dataset.listChildren():
    pixels = image.getPrimaryPixels()
    plane2 = pixels.getPlane(theT=2)
    plane3 = pixels.getPlane(theT=3)

    # difference between before and after
    bleach = plane2 - plane3
    # threshold at midpoint between min and max
    threshold = bleach > ((bleach.min() + bleach.max())/2)
    threshold = morphology.remove_small_objects(threshold, 100)
    threshold = morphology.remove_small_holes(threshold, 100)

    contours = measure.find_contours(threshold, 0)
    # we want to find longest contour (biggest polygon)
    print(image.name, 'Found %s contours' % len(contours))
    if len(contours) == 0:
        continue
    longest_contour = contours[0]
    for c in contours:
        if len(c) > len(longest_contour):
            longest_contour = c
    add_polygon(longest_contour)
            


