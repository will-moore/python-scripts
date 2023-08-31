# -----------------------------------------------------------------------------
#  Copyright (C) 2021 University of Dundee. All rights reserved.
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
This script copies a Dataset from one OMERO.server to another.

Usage:
Login to the source server:

$ omero login

Copy Dataset or Image to target server, using Dataset:ID or Image:ID

$ python copy_dataset.py username password target.example.org Dataset:123

NB: This needs omero-python-importer to import original files.
"""

IMPORT_TODO = """
Please download https://gitlab.com/openmicroscopy/incubator/omero-python-importer/-/blob/master/import.py
and place it in the same directory as this script, naming it 'omero_importer.py'
Or use --pixels to only transfer the raw pixels and not the original files.
"""

import os
import sys
import argparse
import omero
from omero.cli import cli_login
from omero.gateway import BlitzGateway, DatasetWrapper
from omero.rtypes import rint, rstring
from omero.model import DatasetI
import tempfile

if __name__ == '__main__':
    # Add current dir to sys.path so we can import omero_importer
    # From https://stackoverflow.com/questions/8299270/relative-imports-in-python-2-5
    curr_dir = os.path.dirname(os.path.join(os.getcwd(), __file__))
    sys.path.append(os.path.normpath(os.path.join(curr_dir, '..', '..')))
    try:
        from omero_importer import full_import
    except ImportError:
        full_import = None
        pass


def getTargetPath(fsFile, templatePrefix):
        if fsFile.getPath() == templatePrefix or templatePrefix == "":
            return fsFile.getName()
        relPath = os.path.relpath(fsFile.getPath(), templatePrefix)
        return os.path.join(relPath, fsFile.getName())


def copy_fileset(conn2, fileset, new_dataset=None):
    # Download all the files from fileset, create a new fileset
    # on target server and re-import into new_dataset

    print("copy_fileset...", fileset.id)
    bytes_in_mb = 1048576
    chunk_size = 2 * 1048576
    templatePrefix = fileset.getTemplatePrefix()
    img_ids = []
    with tempfile.TemporaryDirectory() as tmpdirname:
        print('created temporary directory', tmpdirname)
        for used_file in fileset.listFiles():
            rel_path = getTargetPath(used_file, templatePrefix)
            file_path = os.path.join(tmpdirname, rel_path)
            dir_name = os.path.dirname(file_path)
            file_size = used_file.getSize()
            print("file_size (bytes)", file_size)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            print('downloading file to', file_path)
            downloaded_bytes = 0
            with open(str(file_path), "wb") as f:
                for chunk in used_file.getFileInChunks(chunk_size):
                    downloaded_bytes += chunk_size
                    print(f"download: {(downloaded_bytes/file_size) * 100} %")
                    f.write(chunk)

        # re-import to target server
        client = conn2.c
        rsp = full_import(client, tmpdirname)
        if rsp:
            links = []
            for p in rsp.pixels:
                print ('Imported Image ID: %d' % p.image.id.val)
                img_ids.append(p.image.id.val)
                if new_dataset:
                    link = omero.model.DatasetImageLinkI()
                    link.parent = omero.model.DatasetI(new_dataset.id, False)
                    link.child = omero.model.ImageI(p.image.id.val, False)
                    links.append(link)
            if len(links) > 0:
                conn2.getUpdateService().saveArray(links, conn2.SERVICE_OPTS)
    return img_ids


def copy_filesets(conn2, images, new_dataset):
    # find all filesets for the images
    if full_import is None:
        print(IMPORT_TODO)
        return []

    filesets = {}
    for image in images:
        fset = image.getFileset()
        # ignore images created via API (no original files)
        if fset is not None:
            filesets[fset.id] = fset

    img_ids = []
    for fileset in filesets.values():
        ids = copy_fileset(conn2, fileset, new_dataset)
        img_ids.extend(ids)

    return img_ids


def copy_image(conn2, image, new_dataset):
    """Create a copy of image."""
    image_name = image.getName()
    size_Z = image.getSizeZ()
    size_C = image.getSizeC()
    size_T = image.getSizeT()
    total_planes = size_Z * size_C * size_T
    clist = image.getChannelLabels()
    zct_list = []
    for z in range(size_Z):
        for c in range(size_C):
            for t in range(size_T):
                zct_list.append( (z,c,t) )

    def planeGen():
        plane_count = 0
        planes = image.getPrimaryPixels().getPlanes(zct_list)
        for p in planes:
            plane_count += 1
            print(plane_count, '/', total_planes)
            yield p

    img = conn2.createImageFromNumpySeq(planeGen(), image_name, sizeZ=size_Z,
                                       sizeC=size_C, sizeT=size_T,
                                       channelList=clist, dataset=new_dataset._obj)
    # NB: could also copy rendering settings, annotations etc.
    print("New image", img.id, img.name)
    return img.id


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('username2', help='Target server Username')
    parser.add_argument('password2', help='Target server Password')
    parser.add_argument('server2', help='Target server Password')
    parser.add_argument('--pixels', help='Only copy pixels, not original files',
        action="store_true")
    parser.add_argument('--port', default=4064, help="OMERO server port")
    parser.add_argument('object', help=(
        'Object to copy, Image:ID or Dataset:ID'))
    args = parser.parse_args(argv)

    source_object = args.object

    with cli_login() as cli:
        # 2 Connections
        conn = BlitzGateway(client_obj=cli._client)
        conn.SERVICE_OPTS.setOmeroGroup(-1)

        conn2 = BlitzGateway(args.username2, args.password2,
                             port=args.port, host=args.server2)
        conn2.connect()
        default_group = conn2.getEventContext().groupId
        print('Importing into group', default_group)
        conn2.SERVICE_OPTS.setOmeroGroup(default_group)

        # The Dataset or Image we want to copy from
        images = []
        if source_object.startswith("Dataset:"):
            object_id = source_object.split(":")[1]
            dataset = conn.getObject("Dataset", object_id)
            dataset_name = dataset.getName()
            images = list(dataset.listChildren())
        elif source_object.startswith("Image:"):
            object_id = source_object.split(":")[1]
            images = [conn.getObject("Image", object_id)]
            dataset_name = "From OMERO 2 OMERO"
        else:
            print("The 'object' needs to be Image:ID or Dataset:ID")
            return

        update_service = conn2.getUpdateService()
        new_dataset = DatasetWrapper(conn2, DatasetI())
        new_dataset.setName(dataset_name)
        new_dataset.save()

        print('pixels only?', args.pixels)
        if args.pixels:
            img_ids = []
            for image in images:
                print("Image", image.id, image.name)
                img_ids.append(copy_image(conn2, image, new_dataset))
        else:
            img_ids = copy_filesets(conn2, images, new_dataset)
        
        print(f'{len(img_ids)} images imported into new Dataset: {new_dataset.id}')

    conn2.close()


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])