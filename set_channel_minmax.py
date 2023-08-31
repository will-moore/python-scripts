
import argparse
import json
import sys

from omero.gateway import BlitzGateway
from omero.cli import cli_login
from omero.model import StatsInfoI
from omero.rtypes import rdouble

# For an Image (ID), set min/max values for channel stats
# Usage: python set_channel_minmax.py 3453 '{"0":[0,2000], "1":[1, 1100]}'

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=int, help='Image ID')
    parser.add_argument('minmax', help=(
        'Channel min/max values as JSON {"0":[0,100], "1":[1, 110]}'))
    args = parser.parse_args(argv)

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)

        image_id = args.image
        minmax_vals = json.loads(args.minmax)
        image = conn.getObject("Image", image_id)

        # Set statsInfo min & max
        for index, ch in enumerate(image.getChannels(noRE=True)):
            if str(index) in minmax_vals:
                minmax = minmax_vals[str(index)]
            else:
                continue
            si = ch.getStatsInfo()
            if si is None:
                si = StatsInfoI()
            else:
                si = si._obj
            if minmax[0] is not None:
                si.globalMin = rdouble(minmax[0])
            if minmax[1] is not None:
                si.globalMax = rdouble(minmax[1])
            ch._obj.statsInfo = si
            ch.save()

if __name__ == '__main__':
    main(sys.argv[1:])
