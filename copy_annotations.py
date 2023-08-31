
# https://forum.image.sc/t/how-to-copy-the-metadata-set-of-an-image-and-paste-it-to-a-new-one/60357
import argparse
import sys

import omero
import omero.clients
from omero.cli import cli_login
from omero.gateway import BlitzGateway


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('image_id', help='Copy annotations FROM Image ID')
    parser.add_argument('to_image_id', help='Copy annotaions TO Image ID')
    args = parser.parse_args(argv)

    image_id = args.image_id
    to_image_id = args.to_image_id

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        conn.SERVICE_OPTS.setOmeroGroup(-1)

        image1 = conn.getObject("Image", image_id)
        image2 = conn.getObject("Image", to_image_id)

        group_id = image1.getDetails().getGroup().id
        print('group_id', group_id)
        conn.SERVICE_OPTS.setOmeroGroup(group_id)
    
        # services we need (not using BlitzGateway after this)
        metadata = conn.getMetadataService()
        update = conn.getUpdateService()

        ann_dict = metadata.loadAnnotations("Image", [image1.id],
            annotationTypes=None,
            annotatorIds=None,
            options=None)

        for ann in ann_dict[image1.id]:
            # link each annotation to the new image
            # (will still be linked to original image)
            link = omero.model.ImageAnnotationLinkI()
            link.parent = omero.model.ImageI(image2.id, False)
            link.child = ann
            try:
                update.saveObject(link, {'group': group_id})
                print("Link created")
            except:
                print(f"Failed to link to Annotation: {ann.id}")


if __name__ == '__main__':
    main(sys.argv[1:])