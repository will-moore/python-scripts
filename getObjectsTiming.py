
import omero.clients
from omero.cli import cli_login
from omero.rtypes import wrap
from omero.gateway import BlitzGateway

from datetime import datetime


with cli_login() as cli:
    conn = BlitzGateway(client_obj=cli._client)

    my_groups = list(conn.getGroupsMemberOf())

    # Need a custom query to get 1 (random) image per Project
    query_service = conn.getQueryService()
    params = omero.sys.ParametersI()
    params.theFilter = omero.sys.Filter()
    params.theFilter.limit = wrap(1)

    query = "select count(obj.id) from %s as obj"

    groups = []

    for g in my_groups:
        conn.SERVICE_OPTS.setOmeroGroup(g.id)
        print(g.name, g.id)

        start = datetime.now()
        image_ids = query_service.projection(
                                "SELECT i.id FROM Image i",
                                params,
                                conn.SERVICE_OPTS
                )
        print(datetime.now() - start)
        start = datetime.now()
        # images = list(conn.getObjects("Image", params=params))
        # query, params, wrapper = conn.buildQuery("Image", None, params)
        query = "select obj from Image obj join fetch obj.details.owner as owner join fetch obj.details.creationEvent"
        result = query_service.findAllByQuery(query, params, conn.SERVICE_OPTS)
        print(len(result))
        print(datetime.now() - start)

        start = datetime.now()
        # query, p, wrapper = conn.buildQuery("Image", None, params)
        # print("query", query)
        # result = query_service.findAllByQuery(query, p, conn.SERVICE_OPTS)
        images = list(conn.getObjects("Image", params=params))
        print(len(images))

        print(datetime.now() - start)

        # if len(image_ids) == 0:
        #     continue        # Don't display empty groups
        # else:
        #     image = conn.getObject("Image", image_ids[0][0]._val)
