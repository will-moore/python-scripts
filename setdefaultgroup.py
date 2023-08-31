
import argparse
import sys

import omero.clients
from omero.cli import cli_login
from omero.gateway import BlitzGateway
from omero.model import ExperimenterGroupI

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('username', help='Username')
    parser.add_argument('group_id', type=int, help=(
        'Set this group to be the default'))
    args = parser.parse_args(argv)

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        admin_service = conn.getAdminService()

        user = admin_service.lookupExperimenter(args.username)
        group = ExperimenterGroupI(args.group_id, False)
        admin_service.setDefaultGroup(user, group)

if __name__ == '__main__':
    main(sys.argv[1:])
