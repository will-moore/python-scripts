#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------------------------------------------
#   Copyright (C) 2025 University of Dundee. All rights reserved.

#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# ------------------------------------------------------------------------------

"""
This script exports Shape bounding boxes to a CSV file and OMERO.table.

It is designed to handle large numbers of shapes by exporting a batch of
1000 shapes at a time. The script will write the data to a CSV file as it
goes to avoid losing data if the script crashes.
To continue after a crash, update the `offset` variable in the script and
run again.

If the script completes successfully, it will write the data to an OMERO.table
and link the table to the Image.

Otherwise, you can use omero2pandas to upload the CSV and create an OMERO.table.
"""

import argparse
import sys
import os
from omero.gateway import BlitzGateway, FileAnnotationWrapper
import omero
from omero.cli import cli_login
from omero.rtypes import rlong, rint, rstring, robject, unwrap
from omero.model import RectangleI, EllipseI, LineI, PolygonI, PolylineI, \
    MaskI, LabelI, PointI, \
    OriginalFileI, FileAnnotationI
from omero.grid import ImageColumn, LongColumn, StringColumn, DoubleColumn
from math import sqrt, pi
import re

DEFAULT_FILE_NAME = "Batch_ROI_Export.csv"
INSIGHT_POINT_LIST_RE = re.compile(r'points\[([^\]]+)\]')
DEFAULT_COLUMN_SIZE = 64


def log(data):
    """Handle logging or printing in one place."""
    print(data)


def get_export_data(conn, image):
    """Get pixel data for shapes on image and returns list of dicts."""
    log("Image ID %s..." % image.id)

    roi_service = conn.getRoiService()

    load_more = True
    # offset = 0
    offset = 129000
    limit = 1000

    export_data = []

    while load_more:
        roi_options = omero.api.RoiOptions()
        print("offset: %s, limit: %s" % (offset, limit))
        roi_options.offset = rint(offset)
        roi_options.limit = rint(limit)
        result = roi_service.findByImage(image.getId(), roi_options)

        print("Found %s ROIs" % len(result.rois))

        if len(result.rois) < limit:
            load_more = False
        else:
            offset += limit

        batch_data = []

        for roi in result.rois:
            for shape in roi.copyShapes():
                label = unwrap(shape.getTextValue())
                # wrap label in double quotes in case it contains comma
                label = "" if label is None else '"%s"' % label.replace(",", ".")
                shape_type = shape.__class__.__name__.rstrip('I').lower()
                # If shape has no Z or T, use -1
                the_z = shape.theZ.val if shape.theZ is not None else -1
                the_t = shape.theT.val if shape.theT is not None else -1
                row_data = {
                    "roi_id": roi.id.val,
                    "image_id": image.id,
                    "shape_id": shape.id.val,
                    "type": shape_type,
                    "text": label,
                    "z": the_z,
                    "t": the_t,
                }
                add_shape_coords(shape, row_data)
                batch_data.append(row_data)
    
        # write each batch to csv as we go... (avoid loss on crash)
        write_csv(batch_data)

        export_data.extend(batch_data)
    return export_data


COLUMN_NAMES = ["image_id",
                "shape_id",
                "type",
                "z",
                "t",
                "X",
                "Y",
                "X1",
                "Y1",
                "X2",
                "Y2",
            ]

COLUMN_TYPES = {"image_id": ImageColumn,
                "roi_id": LongColumn,
                "shape_id": LongColumn,
                "type": StringColumn,
                "z": LongColumn,
                "t": LongColumn,
                "X": LongColumn,
                "Y": LongColumn,
                "X1": LongColumn,
                "Y1": LongColumn,
                "X2": LongColumn,
                "Y2": LongColumn}


def add_shape_coords(shape, row_data):
    """Add shape coordinates and length or area to the row_data dict."""
    if shape.getTextValue():
        row_data['Text'] = shape.getTextValue().getValue()
    if isinstance(shape, (RectangleI, EllipseI, PointI, LabelI, MaskI)):
        row_data['X'] = shape.getX().getValue()
        row_data['Y'] = shape.getY().getValue()
    if isinstance(shape, (PointI, LabelI)):
        row_data['X1'] = row_data['X']
        row_data['X2'] = row_data['X']
        row_data['Y1'] = row_data['Y']
        row_data['Y2'] = row_data['Y']
    if isinstance(shape, (RectangleI, MaskI)):
        width = shape.getWidth().getValue()
        height = shape.getHeight().getValue()
        row_data['X1'] = row_data['X'] - width/2
        row_data['X2'] = row_data['X'] + width/2
        row_data['Y1'] = row_data['Y'] - height/2
        row_data['Y2'] = row_data['Y'] + height/2
    if isinstance(shape, EllipseI):
        row_data['RadiusX'] = shape.getRadiusX().getValue()
        row_data['RadiusY'] = shape.getRadiusY().getValue()
        row_data['X1'] = row_data['X'] - row_data['RadiusX'] / 2
        row_data['X2'] = row_data['X'] + row_data['RadiusX'] / 2
        row_data['Y1'] = row_data['Y'] - row_data['RadiusY'] / 2 
        row_data['Y2'] = row_data['Y'] + row_data['RadiusY'] / 2
    if isinstance(shape, LineI):
        row_data['X1'] = shape.getX1().getValue()
        row_data['X2'] = shape.getX2().getValue()
        row_data['Y1'] = shape.getY1().getValue()
        row_data['Y2'] = shape.getY2().getValue()
        row_data['X'] = (row_data['X1'] + row_data['X2']) / 2
        row_data['Y'] = (row_data['Y1'] + row_data['Y2']) / 2
    if isinstance(shape, (PolygonI, PolylineI)):
        point_list = shape.getPoints().getValue()
        match = INSIGHT_POINT_LIST_RE.search(point_list)
        if match is not None:
            point_list = match.group(1)
        x_coords = []
        y_coords = []
        for xy in point_list.split(" "):
            [x, y] = xy.strip(",").split(",")
            x_coords.append(float(x))
            y_coords.append(float(y))
        min_x = min(x_coords)
        min_y = min(y_coords)
        max_x = max(x_coords)
        max_y = max(y_coords)
        row_data['Width'] = max_x - min_x
        row_data['Height'] = max_y - min_y
        row_data['X'] = min_x + (row_data['Width'] / 2)
        row_data['Y'] = min_y + (row_data['Height'] / 2)
        row_data['X1'] = min_x
        row_data['X2'] = max_x
        row_data['Y1'] = min_y
        row_data['Y2'] = max_y

def create_column(name, data=[]):
    col_type = COLUMN_TYPES[name]
    if col_type is StringColumn:
        return StringColumn(name, '', DEFAULT_COLUMN_SIZE, data)
    else:
        if col_type == LongColumn:
            data = [int(d) for d in data]
        return col_type(name, '', data)


def write_table(conn, export_data):
    """Write the list of data to an OMERO.table, return a file annotation."""
    table_name = DEFAULT_FILE_NAME
    if table_name.endswith('.csv'):
        table_name = table_name.replace('.csv', '')
    columns = [create_column(name, []) for name in COLUMN_NAMES]
    resources = conn.c.sf.sharedResources()
    repository_id = resources.repositories().descriptions[0].getId().getValue()
    table = resources.newTable(repository_id, table_name)
    table.initialize(columns)

    data = []
    for name in COLUMN_NAMES:
        col_data = [row.get(name) for row in export_data]
        data.append(create_column(name, col_data))
    table.addData(data)
    orig_file = table.getOriginalFile()
    table.close()
    orig_file_id = orig_file.id.val
    file_ann = FileAnnotationI()
    file_ann.setNs(rstring("omero.shape.boundingbox.coords"))
    file_ann.setFile(OriginalFileI(orig_file_id, False))
    file_ann = conn.getUpdateService().saveAndReturnObject(file_ann)
    return FileAnnotationWrapper(conn, file_ann)


def write_csv(export_data):
    """Write the list of data to a CSV file and create a file annotation."""
    file_name = DEFAULT_FILE_NAME
    if not file_name.endswith(".csv"):
        file_name += ".csv"

    csv_header = ",".join(COLUMN_NAMES)

    # If we're starting a new file, write the header
    if not os.path.exists(file_name):
        csv_rows = [csv_header]
    else:
        csv_rows = []

    for row in export_data:
        cells = [str(row.get(name, "")) for name in COLUMN_NAMES]
        csv_rows.append(",".join(cells))

    with open(file_name, 'a') as csv_file:
        csv_file.write("\n")
        csv_file.write("\n".join(csv_rows))

    # return conn.createFileAnnfromLocalFile(file_name, mimetype="text/csv")


def link_annotation(objects, file_ann):
    """Link the File Annotation to each object."""
    for o in objects:
        if o.canAnnotate():
            o.linkAnnotation(file_ann)


def get_images_from_plate(plate):
    imgs = []
    for well in plate.listChildren():
        for ws in well.listChildren():
            imgs.append(ws.image())
    return imgs


def batch_roi_export(conn, image_id):
    """Main entry point. Get images, process them and return result."""

    image = conn.getObject("Image", image_id)

    # build a list of dicts.
    export_data = get_export_data(conn, image)

    # write the data to a table and link to the objects
    # TODO: we could use the CSV file to create the table here with omero2pandas
    file_ann = write_table(conn, export_data)
    link_annotation([image], file_ann)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('image', help='Image ID')

    args = parser.parse_args(sys.argv[1:])

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        batch_roi_export(conn, args.image)
