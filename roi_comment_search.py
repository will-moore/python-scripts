
# https://forum.image.sc/t/searching-by-roi-comment-field-in-omero-web/38808

# https://gist.github.com/will-moore/bee8a8ad37a75ccb8b1461b66cfb886c

# Usage: $ python roi_comment_search.py search_query

import argparse
import sys

import omero
import omero.clients
from omero.sys import ParametersI
from omero.rtypes import rstring
from omero.cli import cli_login
from omero.gateway import BlitzGateway

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('query', help='Search Text')
    args = parser.parse_args(argv)

    query_text = args.query

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        qs = conn.getQueryService()
        query = """select annLink from RoiAnnotationLink as annLink
                    join fetch annLink.parent as roi
                    join fetch roi.image
                    join fetch annLink.child as ann where ann.textValue like :text"""

        params = ParametersI()
        with_wildcards = f'%{ query_text }%'
        params.addString('text', rstring(with_wildcards))
        results = qs.findAllByQuery(query, params, conn.SERVICE_OPTS)
        print('FOUND', len(results))
        for r in results:
            image = r.parent.image
            print(r.parent.id.val, image.id.val, image.name.val)

if __name__ == '__main__':
    main(sys.argv[1:])
