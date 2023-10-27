
# https://github.com/ome/omero-documentation/pull/2354

import argparse
import sys
from omero.cli import cli_login
from random import random
from omero.gateway import BlitzGateway
from omero.grid import LongColumn, StringColumn, DoubleColumn, ImageColumn
from omero.model import FileAnnotationI, OriginalFileI, DatasetAnnotationLinkI, DatasetI


def create_table(conn, dataset_id):
    dataset = conn.getObject('Dataset', dataset_id)
    group_id = dataset.getDetails().group.id.val
    conn.SERVICE_OPTS.setOmeroGroup(group_id)
    images = dataset.listChildren()
    # Create some data
    data = []
    for image in images:
        data.append(
            {
                'image': image.getId(),
                'image_name': image.getName(),
                'random_number': random(),
            }
        )
    # Determine column definitions
    n = len(data)
    cols = []
    for key, value in data[0].items():
        if key == 'image':
            cols.append(ImageColumn(key, '', [0] * n))
        elif isinstance(value, int):
            cols.append(LongColumn(key, 'Integer value column', [0] * n))
        elif isinstance(value, float):
            cols.append(DoubleColumn(key, '', [0.0] * n))
        elif isinstance(value, str):
            cols.append(StringColumn(
                key, 'String col to store text', 64, ['-'] * n))
    # initialize table
    resources = conn.c.sf.sharedResources()
    repository_id = resources.repositories(
    ).descriptions[0].getId().getValue()
    table = resources.newTable(
        repository_id, "test:%i" % int(random()*1e6))
    table.initialize(cols)
    # Populate the columns
    for col in cols:
        for row_ind, row in enumerate(data):
            col.values[row_ind] = row[col.name]
    # Upload the data
    table.addData(cols)
    table_file_id = table.getOriginalFile().id.val
    table.close()
    # link the table file to the Dataset
    annotation = FileAnnotationI()
    annotation.setFile(OriginalFileI(table_file_id, False))
    annotation = conn.getUpdateService().saveAndReturnObject(annotation)
    link = DatasetAnnotationLinkI()
    link.setParent(DatasetI(dataset.getId(), False))
    link.setChild(FileAnnotationI(annotation.getId().getValue(), False))
    link = conn.getUpdateService().saveAndReturnObject(link)
    print("Linked table to Dataset", dataset.name)


if __name__ == "__main__":
    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        parser = argparse.ArgumentParser()
        parser.add_argument('dataset_id', help='Dataset ID')
        args = parser.parse_args(sys.argv[1:])
        create_table(conn, args.dataset_id)
