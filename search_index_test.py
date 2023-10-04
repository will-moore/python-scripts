# https://forum.image.sc/t/omero-web-search-does-not-find-images-present-in-omero/86141/10

import argparse
import sys
from datetime import datetime

import omero
import omero.clients
from omero.rtypes import rlist, rlong, rstring
from omero.cli import cli_login
from omero.gateway import BlitzGateway


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset', type=int, help='Dataset ID')

    args = parser.parse_args(argv)
    dataset_id = args.dataset

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        update_service = conn.getUpdateService()
        is_admin = conn.isAdmin()

        dataset = conn.getObject("Dataset", dataset_id)

        # only needed if saving name changes below
        group_id = dataset.getDetails().group.id.val
        conn.SERVICE_OPTS.setOmeroGroup(group_id)
        print('group_id', group_id)

        for image in dataset.listChildren():
            print("Image", image.id, image.name)

            results = conn.searchObjects(["Image"], f"id:{image.id}")
            print(results)

            if is_admin:
                # Need to be Admin user - script waits for indexing...
                update_service.indexObject(omero.model.ImageI(image.id))

            else:
                # Alternative for non-Admin - rename to trigger background re-indexing
                name = image.name
                image.setName("reindex")
                image.save()
                # restore original name
                image.setName(name)
                image.save()

if __name__ == '__main__':  
    main(sys.argv[1:])