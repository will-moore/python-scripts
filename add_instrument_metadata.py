
# https://forum.image.sc/t/how-to-copy-the-metadata-set-of-an-image-and-paste-it-to-a-new-one/60357
import argparse
import sys

import omero
from omero.rtypes import wrap
import omero.clients
from omero.cli import cli_login
from omero.gateway import BlitzGateway

# https://docs.openmicroscopy.org/omero-model/5.6.14/javadoc/ome/model/acquisition/Microscope.html
from omero.model import InstrumentI, MicroscopeI, ObjectiveI, ObjectiveSettingsI
# https://docs.openmicroscopy.org/omero-model/5.6.14/javadoc/ome/model/enums/MicroscopeType.html
from omero.model.enums import UnitsLength
from omero.model import enums
print(dir(enums))
from omero.model.enums import MicroscopeTypeUpright, MicroscopeTypeInverted
from omero.model.enums import ImmersionOil, ImmersionWater
from omero.model.enums import CorrectionPlanApo

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
        
        # instrument = image.getInstrument()
        # microscope = instrument.getMicroscope()
        # print('microscope', microscope)

        # settings = image.getObjectiveSettings()
        # objective = settings.getObjective()
        # print('objective', objective._obj)

        microscope = MicroscopeI()
        mtype = query_service.findByQuery("from MicroscopeType as t where t.value='%s'" % MicroscopeTypeUpright, None)
        microscope.setType(mtype)
        microscope.setModel(wrap("Zeiss LSM 900"))
        microscope.setSerialNumber(wrap("12345"))
        microscope.setManufacturer(wrap("Zeiss"))

        instrument = InstrumentI()
        instrument.setMicroscope(microscope)

        objective = ObjectiveI()
        objective.setNominalMagnification(omero.rtypes.rdouble(20))
        objective.setModel(wrap("Olympus R1"))
        objective.setSerialNumber(wrap("abc12345"))
        objective.setManufacturer(wrap("Olympus"))
        objective.setLensNA(omero.rtypes.rdouble(1.4))
        immersionType = query_service.findByQuery("from Immersion as i where i.value='%s'" % ImmersionOil, None)
        objective.setImmersion(immersionType)
        correction = query_service.findByQuery("from Correction as c where c.value='%s'" % CorrectionPlanApo, None)
        objective.setCorrection(correction)
        objective.setWorkingDistance(omero.model.LengthI(0.1, UnitsLength.MILLIMETER))

        instrument = update_service.saveAndReturnObject(instrument, conn.SERVICE_OPTS)

        objective.setInstrument(instrument)
        settings = ObjectiveSettingsI()
        settings.setObjective(objective)

        image.setInstrument(instrument)
        image.setObjectiveSettings(settings)
        update_service.saveObject(image._obj, conn.SERVICE_OPTS)


if __name__ == '__main__':
    main(sys.argv[1:])