
# https://forum.image.sc/t/error-when-querying-image-id-of-a-dataset/71870

import argparse
import omero
import sys

from omero.gateway import BlitzGateway
from omero.cli import cli_login
from omero.model import StatsInfoI
from omero.rtypes import rdouble

# For an Image (ID), set min/max values for channel stats
# Usage: python set_channel_minmax.py 3453 '{"0":[0,2000], "1":[1, 1100]}'

def main(argv):
    # parser = argparse.ArgumentParser()
    # parser.add_argument('image', type=int, help='Image ID')
    # parser.add_argument('minmax', help=(
    #     'Channel min/max values as JSON {"0":[0,100], "1":[1, 110]}'))
    # args = parser.parse_args(argv)

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        datasetId = 64177

        query_service = conn.getQueryService()
        params = omero.sys.ParametersI()
        params.addId(datasetId)
        query = "select l.child.id from DatasetImageLink as l where l.parent.id = :id"
        result = query_service.projection(query, params, conn.SERVICE_OPTS)
        for r in result:
            print("Image ID:", r[0].val)

        for image in conn.getObjects("Image", opts={"dataset": datasetId}):
            print(image.id)



if __name__ == '__main__':
    main(sys.argv[1:])
