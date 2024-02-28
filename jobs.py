
# See https://forum.image.sc/t/omero-activity-history/92703

# This script lists the last 100 Script Jobs and the associated files
# which includes the python script itself and stdout/stderr files

import sys
from datetime import datetime

import omero
import omero.clients
from omero.rtypes import unwrap
from omero.cli import cli_login
from omero.gateway import BlitzGateway

def main(argv):

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        query_service = conn.getQueryService()

        # https://omero.readthedocs.io/en/stable/developers/Model/EveryObject.html#importjob
        params = omero.sys.ParametersI()
        offset = 0
        limit = 100
        params.page(offset, limit)
        query = """select j from ScriptJob as j
            left outer join fetch j.originalFileLinks as link
            join fetch link.child
            order by j.finished desc
        """
        results = query_service.findAllByQuery(query, params, None)
        for job in results:
            print("\nJob: ", job.id.val, unwrap(job.message), unwrap(job.username))
            for origFileLink in job.iterateOriginalFileLinks():
                print("    File:", origFileLink.child.id.val, origFileLink.child.name.val)
            if job.finished:
                print("    Finished:", str(datetime.fromtimestamp(job.finished.val/1000)))

if __name__ == '__main__':  
    main(sys.argv[1:])
