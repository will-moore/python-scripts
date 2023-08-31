

import omero
from omero.gateway import BlitzGateway
from omero.cli import cli_login

with cli_login() as cli:
    conn = BlitzGateway(client_obj=cli._client)

    image_id = 122915
    updateService = conn.getUpdateService()
    params = omero.sys.ParametersI()
    params.addLong('pid', conn.getObject("Image", image_id).getPixelsId())
    query = "from PlaneInfo as Info where pixels.id=:pid"
    info_list = conn.getQueryService().findAllByQuery(
        query, params, conn.SERVICE_OPTS)
    for info in info_list:
        if info.deltaT is not None:
            info.deltaT.setUnit(omero.model.enums.UnitsTime.DAY)
            updateService.saveObject(info)
