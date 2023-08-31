
import argparse
import json
import sys
from io import BytesIO

from omero.gateway import BlitzGateway
from omero.cli import cli_login
from omero.model import FileAnnotationI, OriginalFileI
from omero.rtypes import wrap

# For each Panel in a Figure (File Annotation ID) find an Image with the same
# name is the Dataset (ID), replace the ID in the figure JSON.
# Then save as a new Figure (in the same group as the Images)
# Usage: python Dataset_Images_To_New_Figure.py DATASET_ID FIGURE_ID

JSON_FILEANN_NS = "omero.web.figure.json"

def save_web_figure(conn, json_data):
    """
    Saves 'figureJSON' in POST as an original file. If 'fileId' is specified
    in POST, then we update that file. Otherwise create a new one with
    name 'figureName' from POST.
    """
    image_ids = []
    first_img_id = None
    try:
        for panel in json_data['panels']:
            image_ids.append(panel['imageId'])
        if len(image_ids) > 0:
            first_img_id = int(image_ids[0])
        # remove duplicates
        image_ids = list(set(image_ids))
        # pretty-print json
        figure_json = json.dumps(json_data, sort_keys=True,
                                 indent=2, separators=(',', ': '))
    except Exception:
        pass

    # See https://github.com/will-moore/figure/issues/16
    figure_json = figure_json.encode('utf8')

    if 'figureName' in json_data and len(json_data['figureName']) > 0:
        figure_name = json_data['figureName']
    else:
        print("No figure name found")
        return

    # we store json in description field...
    description = {}
    if first_img_id is not None:
        # We duplicate the figure name here for quicker access when
        # listing files
        # (use this instead of file name because it supports unicode)
        description['name'] = figure_name
        description['imageId'] = first_img_id
        if 'baseUrl' in panel:
            description['baseUrl'] = panel['baseUrl']
    desc = json.dumps(description)

    # Create new file
    # Try to set Group context to the same as first image
    curr_gid = conn.SERVICE_OPTS.getOmeroGroup()
    i = None
    if first_img_id:
        i = conn.getObject("Image", first_img_id)
    if i is not None:
        gid = i.getDetails().getGroup().getId()
        conn.SERVICE_OPTS.setOmeroGroup(gid)
    else:
        # Don't leave as -1
        conn.SERVICE_OPTS.setOmeroGroup(curr_gid)
    file_size = len(figure_json)
    f = BytesIO()
    f.write(figure_json)
    orig_file = conn.createOriginalFileFromFileObj(
        f, '', figure_name, file_size, mimetype="application/json")
    fa = FileAnnotationI()
    fa.setFile(OriginalFileI(orig_file.getId(), False))
    fa.setNs(wrap(JSON_FILEANN_NS))
    fa.setDescription(wrap(desc))

    update = conn.getUpdateService()
    fa = update.saveAndReturnObject(fa, conn.SERVICE_OPTS)
    file_id = fa.getId().getValue()
    return file_id


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset_id', type=int, help='Dataset ID')
    parser.add_argument('figure_id', type=int, help='Figure ID')
    args = parser.parse_args(argv)

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        conn.SERVICE_OPTS.setOmeroGroup(-1)

        figure_id = args.figure_id
        file_ann = conn.getObject("FileAnnotation", figure_id)
        if file_ann is None:
            print("Figure File-Annotation %s not found" % figure_id)
        figure_json = b"".join(list(file_ann.getFileInChunks()))
        figure_json = figure_json.decode('utf8')
        json_data = json.loads(figure_json)

        # Get Images by Name from Dataset
        dataset = conn.getObject("Dataset", args.dataset_id)
        images_by_name = {}
        for image in dataset.listChildren():
            images_by_name[image.name] = image.id
        print("images_by_name", images_by_name)

        # For each panel, get the name and update the ID
        for p in json_data.get("panels"):
            name = p['name']
            if name not in images_by_name:
                print("Could not find Image %s" % name)
                # TODO: add option to ignore?
                return
            new_id = images_by_name[name]
            p["imageId"] = new_id

        # Save new Figure, in the appropriate group
        file_id = save_web_figure(conn, json_data)

if __name__ == '__main__':
    main(sys.argv[1:])
