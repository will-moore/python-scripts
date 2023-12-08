
from io import BytesIO

import argparse
import omero
from omero.rtypes import wrap
import omero.grid
from omero.cli import cli_login
from omero.gateway import BlitzGateway
from random import choices


def get_random_string(length=6):
    # chars include A-Z a-z
    letters = [chr(i) for i in range(65, 91)] + [chr(i) for i in range(97, 123)]
    return "".join(choices(letters, k=length))


def create_file_annotation(conn):
    update = conn.getUpdateService()
    random_string = get_random_string()
    text_content = "some text content: %s" % random_string
    name = "fake file %s" % random_string
    ns = "omero.test.fileannotation"
    file_size = len(text_content)
    f = BytesIO()
    f.write(text_content.encode('utf8'))
    orig_file = conn.createOriginalFileFromFileObj(f, '', name, file_size, mimetype="text")
    fa = omero.model.FileAnnotationI()
    fa.setFile(omero.model.OriginalFileI(orig_file.getId(), False))
    fa.setNs(wrap(ns))
    fa = update.saveAndReturnObject(fa, conn.SERVICE_OPTS)
    print("New File Annotation", fa.id.val)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=10)
    args = parser.parse_args(args)
    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        for i in range(args.count):
            create_file_annotation(conn)


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])