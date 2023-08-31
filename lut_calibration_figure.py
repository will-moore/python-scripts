
import argparse
import json
import sys
import numpy as np

from omero.gateway import BlitzGateway
from omero.cli import cli_login
from omero.rtypes import rdouble

from omero.model.enums import PixelsTypeint8, PixelsTypeuint8, PixelsTypeint16
from omero.model.enums import PixelsTypeuint16, PixelsTypeint32
from omero.model.enums import PixelsTypeuint32, PixelsTypefloat
from omero.model.enums import PixelsTypecomplex, PixelsTypedouble

# For an Image (ID), create a greyscale gradient image
# with corresponding pixel type and channels
# Gradient left -> right from min -> max intensity for each channel

omeroToNumpy = {PixelsTypeint8: np.int8,
                PixelsTypeuint8: np.uint8,
                PixelsTypeint16: np.int16,
                PixelsTypeuint16: np.uint16,
                PixelsTypeint32: np.int32,
                PixelsTypeuint32: np.uint32,
                PixelsTypefloat: np.float32,
                PixelsTypedouble: np.double}

def main(argv):
    parser = argparse.ArgumentParser()  
    parser.add_argument('image', type=int, help='Image ID')
    # parser.add_argument('max', type=int, help='Maximum pixel value')
    args = parser.parse_args(argv)

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)

        image_id = args.image
        image = conn.getObject("Image", image_id)
        size_c = image.getSizeC()

        pix_type = image.getPrimaryPixels().getPixelsType().getValue()
        dtype = omeroToNumpy[pix_type]
        parent = image.getParent()._obj

        print('dtype', dtype)

        # min_value = args.min
        # max_value = args.max
        # create numpy data width 512 x 100 pixels
        size_x = 512
        size_y = 100

        planes = []

        for ch in image.getChannels():
            min_value = int(ch.getWindowMin())
            max_value = int(ch.getWindowMax())

            print('min_value', min_value, max_value)

            value_per_pixel = (max_value - min_value) / size_x

            plane = np.fromfunction(
                lambda y, x: min_value + (value_per_pixel * x),
                (size_y, size_x), dtype=dtype)
            print('plane.dtype', plane.dtype)
            planes.append(plane.astype(dtype))

        name = image.getName() + "_calibration"
        img = conn.createImageFromNumpySeq(
            iter(planes), name, sizeC=size_c,
            sourceImageId=image.id, dataset=parent)
        print("Done", img)

if __name__ == '__main__':
    main(sys.argv[1:])
