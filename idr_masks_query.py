
# See https://forum.image.sc/t/labeled-images-for-developing-tutorial/76293

import sys

from omero.gateway import BlitzGateway
from omero.cli import cli_login
import omero

def main(argv):

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)

        params = omero.sys.ParametersI()
        params.page(0, 5)

        query = """select image from Image image
            left outer join fetch image.rois as roi
            left outer join fetch roi.shapes as shape
            where shape.class = Mask"""
        
        result = conn.getQueryService().findAllByQuery(query, params, {'group': '-1'})

        print("result", len(result))
        print(result[0])

if __name__ == '__main__':
    main(sys.argv[1:])
