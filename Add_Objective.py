
import omero.scripts as scripts
from omero.gateway import BlitzGateway
import omero
from omero.rtypes import rstring, rlong, robject, wrap, rdouble
from omero.model import ObjectiveI, ObjectiveSettingsI, MicroscopeI, InstrumentI, LengthI
from omero.model.enums import UnitsLength
from datetime import datetime


# lookup enums with e.g. "MicroscopeTypeI", "Immersion", "Correction"
# for dt in conn.getEnumerationEntries("MicroscopeTypeI"):
#     print(dt.getValue())
microscope_types = ["Upright", "Inverted", "Dissection", "Electrophysiology", "Other", "Unknown"]
immersions = ["Oil", "Water", "WaterDipping", "Air", "Multi", "Glycerol", "Other", "Unknown"]
corrections = ["UV", "PlanApo", "PlanFluor", "SuperFluor", "VioletCorrected", "Achro", "Achromat", "Fluor", "Fl", "Fluar", "Neofluar", "Fluotar", "Apo", "Other", "Unknown"]


def find_enum(conn, enum_name, value):
    enum_entries = list(conn.getEnumerationEntries(enum_name))
    for entry in enum_entries:
        if entry.getValue() == value:
            print(f"Found {value} in {enum_name}")
            return entry._obj
    # Last one is Unknown
    print(f"Could not find {value} in {enum_name}", enum_entries[-1])
    return enum_entries[-1]._obj


def create_instrument(conn, params):
    microscope = MicroscopeI()
    mtype = find_enum(conn, "MicroscopeTypeI", params["Microscope_Type"])
    microscope.setType(mtype)
    # optional params - handle missing values
    microscope.setModel(wrap(params.get("Microscope_Model", "")))
    if "Microscope_Manufacturer" in params:
        microscope.setManufacturer(wrap(params["Microscope_Manufacturer"]))
    # microscope.setSerialNumber(wrap("12345"))
    instrument = InstrumentI()
    instrument.setMicroscope(microscope)
    return instrument


def add_objective(conn, params, image, instrument):
    objective = ObjectiveI()
    objective.setNominalMagnification(rdouble(20))
    objective.setModel(wrap("Olympus R1"))
    objective.setSerialNumber(wrap("abc12345"))
    objective.setManufacturer(wrap("Olympus"))
    objective.setLensNA(rdouble(1.4))
    immersionType = find_enum(conn, "Immersion", params["Immersion"])
    objective.setImmersion(immersionType)
    correction = find_enum(conn, "Correction", params["Correction"])
    objective.setCorrection(correction)
    objective.setWorkingDistance(LengthI(0.1, UnitsLength.MILLIMETER))
    objective.setInstrument(instrument)
    settings = ObjectiveSettingsI()
    settings.setObjective(objective)
    image.setObjectiveSettings(settings)


def add_metadata(conn, params):

    update_service = conn.getUpdateService()

    for image_id in params['IDs']:
        image = conn.getObject("Image", image_id)
        group_id = image.getDetails().getGroup().id
        conn.SERVICE_OPTS.setOmeroGroup(group_id)

        instrument = create_instrument(conn, params)
        image.setInstrument(instrument)
        add_objective(conn, params, image, instrument)
        
        update_service.saveObject(image._obj, conn.SERVICE_OPTS)
        

def run_script():
    """
    The main entry point of the script, as called by the client via the
    scripting service, passing the required parameters.
    """
    # only support Images for now
    data_types = [rstring('Image')]

    client = scripts.client(
        'Add_Objective.py',
        """Add Objective and Instrument metadata to Images""",

        # Data_Type and IDs are populated by the client
        scripts.String(
            "Data_Type", optional=False, grouping="1",
            description="The data you want to work with.", values=data_types,
            default="Image"),

        scripts.List(
            "IDs", optional=False, grouping="2",
            description="List of Image IDs").ofType(rlong(0)),

        scripts.String("Microscope_Type", grouping="3", description="Microscope Type",
                       values=wrap(microscope_types), default="Unknown"),
        scripts.String("Microscope_Model", grouping="3.1", description="Microscope Model", required=False),
        scripts.String("Microscope_Manuacturer", grouping="3.2", description="Microscope Manufacturer", required=False),

        scripts.String("Objective_Model", grouping="4", description="Objective Model", required=False),
        scripts.String("Objective_Manuacturer", grouping="4.1", description="Objective Manufacturer", required=False),
        scripts.String("Immersion", grouping="4.2", values=wrap(immersions), description="Objective Immersion", required=False),
        scripts.String("Correction", grouping="4.3", values=wrap(corrections), description="Objective Correction", required=False),

        version="0.0.0",
        authors=["William Moore", "OME Team"],
    )

    try:
        conn = BlitzGateway(client_obj=client)
        script_params = client.getInputs(unwrap=True)
        print(script_params)

        add_metadata(conn, script_params)

        client.setOutput("Message", wrap("Added Objective and Instrument metadata to Images"))

    finally:
        client.closeSession()


if __name__ == "__main__":
    run_script()
