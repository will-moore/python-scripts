
# https://forum.image.sc/t/how-to-copy-the-metadata-set-of-an-image-and-paste-it-to-a-new-one/60357
import argparse
import sys

import omero
from omero.rtypes import wrap
import omero.clients
from omero.cli import cli_login
from omero.gateway import BlitzGateway

from omero.model import InstrumentI, MicroscopeI, FilterI, TransmittanceRangeI, LengthI, LightPathI, \
    LightPathEmissionFilterLinkI
from omero.model.enums import UnitsLength
from omero.model.enums import MicroscopeTypeUpright

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

        microscope = MicroscopeI()
        mtype = query_service.findByQuery("from MicroscopeType as t where t.value='%s'" % MicroscopeTypeUpright, None)
        microscope.setType(mtype)
        microscope.setModel(wrap("Zeiss LSM 900"))
        microscope.setSerialNumber(wrap("12345"))
        microscope.setManufacturer(wrap("Zeiss"))

        instrument = InstrumentI()
        instrument.setMicroscope(microscope)

        # Create and save an emission filter...
        emissionFilter = FilterI()
        tr = TransmittanceRangeI()
        tr.setCutIn(LengthI(400, UnitsLength.NANOMETER))
        tr.setCutOut(LengthI(500, UnitsLength.NANOMETER))
        emissionFilter.setTransmittanceRange(tr)
        emissionFilter.setInstrument(instrument)
        emissionFilter = update_service.saveAndReturnObject(emissionFilter, conn.SERVICE_OPTS)

        # Link it to a new light path for each channel, adding the light path to the logical channel
        for index, ch in enumerate(image.getChannels(noRE=True)):
            print("CHANNEL")
            logicalChannel = ch.getLogicalChannel()._obj
            if logicalChannel is not None:
                lightPath = LightPathI()
                link = LightPathEmissionFilterLinkI()
                link.setParent(lightPath)
                link.setChild(emissionFilter)
                link = update_service.saveAndReturnObject(link, conn.SERVICE_OPTS)
                print("link", link.id.val, "parent lightPath", link.parent.id.val, "child Filter", link.child.id.val)
                logicalChannel.setLightPath(link.parent)
                logicalChannel = update_service.saveAndReturnObject(logicalChannel, conn.SERVICE_OPTS)
                print("logicalChannel", logicalChannel)

        # Check if we can see the emission filter in the webclient
        for ch in image.getChannels(noRE=True):
            logicalChannel = ch.getLogicalChannel()
            lightPath = logicalChannel.getLightPath()
            if lightPath is not None:
                # print seems to show that the emission filter IS loaded
                # _emissionFilterLinkLoaded = True
                print("lightPath", lightPath._obj.id.val)
                # But None of these load the emission filters created above
                for filter in lightPath._obj.copyEmissionFilterLink():
                    print("copy filter", filter)
                for ef in lightPath._obj.linkedEmissionFilterList():
                    print("linked filter", ef)
                # This is what webclient does: uses _obj.copyEmissionFilterLink()
                for f in lightPath.getEmissionFilters():
                    print("emission filter", f)

        image.setInstrument(instrument)
        update_service.saveObject(image._obj, conn.SERVICE_OPTS)


if __name__ == '__main__':
    main(sys.argv[1:])