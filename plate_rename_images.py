# https://forum.image.sc/t/imports-of-tiff-to-omero/71648/9
# usage: with plate ID - You will be asked for login...
# $ python plate_rename_images.py 1234

import argparse
import sys

from omero.cli import cli_login
from omero.gateway import BlitzGateway


def rename_images(plate):

    for well in plate.listChildren():
        label = well.getWellPos()
        for field, ws in enumerate(well.listChildren()):
            img = ws.getImage()
            name = f"{label} Field {field + 1}"
            print(img.id, name)
            img.setName(name)
            img.save()


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('plate_id', help='Plate ID')
    args = parser.parse_args(argv)

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        plate = conn.getObject('Plate', args.plate_id)
        rename_images(plate)


if __name__ == '__main__':
    main(sys.argv[1:])
