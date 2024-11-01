
# https://forum.image.sc/t/what-is-the-best-strategy-for-adding-instrument-and-aquisition-data-to-ome-tiff-files/104308/3
import argparse
import sys

import omero
from omero.rtypes import wrap
import omero.clients
from omero.cli import cli_login
from omero.gateway import BlitzGateway

from omero.model import PlaneInfoI, TimeI
from omero.model.enums import UnitsTime

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('image_id', help='Image ID')
    args = parser.parse_args(argv)

    image_id = args.image_id

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        update_service = conn.getUpdateService()
        query_service = conn.getQueryService()
        conn.SERVICE_OPTS.setOmeroGroup(-1)

        image = conn.getObject("Image", image_id)
        group_id = image.getDetails().getGroup().id
        conn.SERVICE_OPTS.setOmeroGroup(group_id)
        pixels_id = image.getPixelsId()

        # delete any existing PlaneInfo
        params = omero.sys.ParametersI()
        params.addLong('pid', pixels_id)
        query = "from PlaneInfo as Info where pixels.id=:pid"
        info_list = query_service.findAllByQuery(query, params, conn.SERVICE_OPTS)
        for info in info_list:
            update_service.deleteObject(info, conn.SERVICE_OPTS)

        # seconds between timepoints
        time_increment = 2.5
        exposure_time = 0.1

        to_save = []
        # We could create plateInfo for every Z-plane, but for now just do one Z per timepoint
        # for z in range(image.getSizeZ()):
        z = 0
        for c in range(image.getSizeC()):
            for t in range(image.getSizeT()):
                print("z", z, "c", c, "t", t)
                plane_info = PlaneInfoI()
                plane_info.deltaT = TimeI(t * time_increment, UnitsTime.SECOND)
                plane_info.exposureTime = TimeI(exposure_time, UnitsTime.SECOND)
                plane_info.pixels = omero.model.PixelsI(pixels_id, False)
                plane_info.theZ = wrap(z)
                plane_info.theT = wrap(t)
                plane_info.theC = wrap(c)
                to_save.append(plane_info)
        update_service.saveAndReturnArray(to_save, conn.SERVICE_OPTS)

        params = omero.sys.ParametersI()
        params.addLong('pid', pixels_id)
        query = "from PlaneInfo as Info where pixels.id=:pid"
        info_list = query_service.findAllByQuery(query, params, conn.SERVICE_OPTS)
        print("info_list", len(info_list))


if __name__ == '__main__':
    main(sys.argv[1:])