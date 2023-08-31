
# This is gist: https://gist.github.com/will-moore/a368b47d1ff5cc93674fd5917c358f6f

import argparse
import sys

import omero
import omero.clients
from omero.rtypes import unwrap, rint, rstring
from omero.cli import cli_login
from omero.api import RoiOptions
from omero.gateway import BlitzGateway
from omero_marshal import get_decoder, get_encoder

# NB: Maks not supported. If you want to copy Masks,
# see https://github.com/ome/omero-ms-zarr/blob/master/src/scripts/copy-masks.py

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('username2', help='Target server Username')
    parser.add_argument('password2', help='Target server Password')
    parser.add_argument('server2', help='Target server Password')
    parser.add_argument('imageid', type=int, help=(
        'Copy ROIs FROM this image'))
    parser.add_argument('imageid2', type=int, help=(
        'Copy ROIs TO this image'))
    args = parser.parse_args(argv)

    to_image_id = args.imageid2

    PAGE_SIZE = 100

    from omero.cli import cli_login
    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        conn2 = BlitzGateway(args.username2, args.password2,
                             port=4064, host=args.server2)
        conn2.connect()

        roi_service = conn.getRoiService()
        update_service = conn2.getUpdateService()

        opts = RoiOptions()
        offset = 0
        opts.offset = rint(offset)
        opts.limit = rint(PAGE_SIZE)

        conn.SERVICE_OPTS.setOmeroGroup(-1)
        image = conn.getObject('Image', args.imageid)
        print(image.name)

        # NB: we repeat this query below for each 'page' of ROIs
        result = roi_service.findByImage(args.imageid, opts, conn.SERVICE_OPTS)

        while len(result.rois) > 0:
            print("offset", offset)
            print("Found ROIs:", len(result.rois))
            for roi in result.rois:

                new_roi = omero.model.RoiI()
                new_roi.setImage(omero.model.ImageI(to_image_id, False))

                for shape in roi.copyShapes():

                    encoder = get_encoder(shape.__class__)
                    json_shape = encoder.encode(shape)
                    encoder = get_encoder(shape.__class__)
                    decoder = get_decoder(encoder.TYPE)
                    json_shape = encoder.encode(shape)
                    new_shape = decoder.decode(json_shape)
                    new_roi.addShape(new_shape)

                update_service.saveObject(new_roi)

            offset += PAGE_SIZE
            opts.offset = rint(offset)
            result = roi_service.findByImage(args.imageid, opts, conn.SERVICE_OPTS)

        conn2.close()

if __name__ == '__main__':
    main(sys.argv[1:])