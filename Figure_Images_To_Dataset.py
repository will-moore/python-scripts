
import argparse
import json
import sys

from omero.gateway import BlitzGateway
from omero.cli import cli_login
from omero.model import DatasetImageLinkI, DatasetI, ImageI

# For an Figure (File Annotation ID) add all Images to a Dataset
# Usage: python Figure_Images_To_Dataset.py FIGURE_ID DATASET_ID

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('figure_id', type=int, help='Figure ID')
    parser.add_argument('dataset_id', type=int, help='Dataset ID')
    args = parser.parse_args(argv)

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        upate = conn.getUpdateService()

        figure_id = args.figure_id
        file_ann = conn.getObject("FileAnnotation", figure_id)
        if file_ann is None:
            print("Figure File-Annotation %s not found" % figure_id)
        figure_json = b"".join(list(file_ann.getFileInChunks()))
        figure_json = figure_json.decode('utf8')
        json_data = json.loads(figure_json)

        image_ids = [p["imageId"] for p in json_data.get("panels")]
        image_ids = list(set(image_ids))
        print(image_ids)

        for image_id in image_ids:
            link = DatasetImageLinkI()
            link.parent = DatasetI(args.dataset_id, False)
            link.child = ImageI(image_id, False)
            try:
                upate.saveObject(link)
            except:
                print("link exists")

if __name__ == '__main__':
    main(sys.argv[1:])
