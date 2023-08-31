# https://forum.image.sc/t/roi-deletion-issue-in-omero-with-omeropy/73717

import argparse

from omero.cli import cli_login
from omero.gateway import BlitzGateway


def delete_ROIs(conn, image):

    rois = conn.getObjects('Roi', opts={'image': image.id})
    roi_ids = [roi.id for roi in rois]

    if not roi_ids:
        print('no ROI to delete in', image.getName(), image.getId())
    else: 
        print('ROIs deleted in ', image.getName(), image.getId())
        print(roi_ids)
        conn.deleteObjects("Roi", roi_ids)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset', type=int)
    args = parser.parse_args(args)
    dataset_id = args.dataset

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)

        images = conn.getObjects('Image', opts={'dataset': dataset_id})

        for image in images:
            delete_ROIs(conn, image)


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
