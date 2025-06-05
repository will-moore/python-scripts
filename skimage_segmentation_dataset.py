
import sys
import argparse

import omero
from omero.cli import cli_login
from omero.gateway import BlitzGateway
from omero.rtypes import rint, rstring

from skimage.filters import threshold_otsu
from skimage import morphology
from skimage import measure

# Adapted from https://gist.github.com/stefanv/7c296c26b0c3624746f4317bed6a3540

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

def add_polygon(image, updateService, contour, x_offset=0, y_offset=0):
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

def delete_ROIs(conn, image):
    rois = conn.getObjects('Roi', opts={'image': image.id})
    roi_ids = [roi.id for roi in rois]
    if len(roi_ids) > 0:
        print("Deleting %s ROIs" % len(roi_ids))
        conn.deleteObjects("Roi", roi_ids)

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('target', type=str, help='Dataset:123 or Plate:123')
    parser.add_argument('channel', type=int, help='channel index to segment')
    args = parser.parse_args(argv)

    total = 0
    img_count = 0

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        updateService = conn.getUpdateService()

        images = []
        target_type = args.target.split(':')[0]
        target_id = int(args.target.split(':')[1])
        if target_type == 'Plate':
            plate = conn.getObject('Plate', target_id)
            for well in plate.listChildren():
                for ws in well.listChildren():
                    images.append(ws.getImage())
        elif target_type == 'Dataset':
            dataset = conn.getObject('Dataset', target_id)
            images = list(dataset.listChildren())
        print("Found %s images in %s" % (len(images), target_type))

        for image in images:
            print("Image", image.id, image.name)
            ch_index = args.channel
            delete_ROIs(conn, image)
            pixels = image.getPrimaryPixels()
            plane = pixels.getPlane(theC=ch_index)

            # contour_count = 100
            # threshold = threshold_otsu(plane)
            threshold = 50
            # while contour_count > 10:
            mask = plane < threshold
            mask = morphology.remove_small_objects(mask, min_size=10)
            # mask = morphology.binary_dilation(mask)
            # mask = morphology.binary_dilation(mask)
            mask = morphology.remove_small_holes(mask)
            contours = measure.find_contours(mask, 0)
            contour_count = len(contours)
            print('Found contours:', contour_count)
            # threshold += 100

            total += len(contours)
            img_count += 1
            for c in contours:
                add_polygon(image, updateService, c)

        print('Total shapes:', total, "images:", img_count)

if __name__ == '__main__':
    main(sys.argv[1:])
