# -----------------------------------------------------------------------------
#  Copyright (C) 2018 University of Dundee. All rights reserved.
#
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# ------------------------------------------------------------------------------

"""
This script connects to IDR and copies a Plate to another OMERO server.

It creates new images via getPlane() and createImageFromNumpySeq().
NB: New images are only a single T and Z.
Usage: $ python idr_copy_plate.py username password idr_plate_id
"""

import argparse
from omero.cli import cli_login
import omero
from omero.gateway import BlitzGateway
from omero.rtypes import rint, rstring
from omero.model import ProjectI


def copy_image(conn, idr_image):
    """Create a copy of image. Single Z and T."""
    image_name = idr_image.getName()
    size_C = idr_image.getSizeC()
    clist = idr_image.getChannelLabels()
    zct_list = []
    for c in range(size_C):
        zct_list.append((0, c, 0))

    def planeGen():
        planes = idr_image.getPrimaryPixels().getPlanes(zct_list)
        for p in planes:
            yield p

    img = conn.createImageFromNumpySeq(planeGen(), image_name, sizeZ=1,
                                       sizeC=size_C, sizeT=1,
                                       channelList=clist)
    print("New image", img.id, img.name)
    return img



def run(conn, project_id):
    """Run the script."""

    # Create connection to IDR server
    # NB: conn.connect() not working on IDR. Do it like this
    idr_client = omero.client(host="idr.openmicroscopy.org", port=4064)
    idr_client.createSession('public', 'public')
    idr_conn = BlitzGateway(client_obj=idr_client)

    # The project we want to copy from IDR
    idr_project = idr_conn.getObject("Project", project_id)
    project_name = idr_project.getName()

    update_service = conn.getUpdateService()
    project = ProjectI()
    project.name = rstring(project_name)
    project = update_service.saveAndReturnObject(project)

    for dataset in idr_project.listChildren():
        print("Dataset", dataset.id, dataset.getName())
        # Create Dataset in local OMERO
        new_dataset = omero.model.DatasetI()
        new_dataset.name = rstring(dataset.getName())
        new_dataset = update_service.saveAndReturnObject(new_dataset)
        link = omero.model.ProjectDatasetLinkI()
        link.parent = omero.model.ProjectI(project.id.val, False)
        link.child = omero.model.DatasetI(new_dataset.id.val, False)
        update_service.saveObject(link)

        for idr_image in dataset.listChildren():
            print("Image", idr_image.id)
            image = copy_image(conn, idr_image)
            # Link to Dataset
            # new_dataset.addImage(omero.model.ImageI(image.id, False))
            link = omero.model.DatasetImageLinkI()
            link.parent = omero.model.DatasetI(new_dataset.id.val, False)
            link.child = omero.model.ImageI(image.id, False)
            update_service.saveObject(link)

    # for idr_well in idr_plate.listChildren():
    #     print("Well", idr_well.id, 'row', idr_well.row, 'col', idr_well.column)
    #     # For each Well, get image and clone locally...
    #     new_imgs = []
    #     for idr_wellsample in idr_well.listChildren():
    #         idr_image = idr_wellsample.getImage()

    #         print("Image", idr_image.id)
    #         image = copy_image(conn, idr_image)
    #         new_imgs.append(image)
    #     # link to Plate...
    #     add_images_to_plate(update_service, plate, new_imgs,
    #                         idr_well.row, idr_well.column)

    conn.close()
    idr_conn.close()


def main(args):
    """Entry point. Parse args and run."""
    parser = argparse.ArgumentParser()
    parser.add_argument('project_id')
    args = parser.parse_args(args)

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        run(conn, args.project_id)


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
