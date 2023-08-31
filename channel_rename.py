


# https://forum.image.sc/t/apply-channel-names-to-all-images-in-an-omero-dataset-possible-bug/70521/10

import argparse
import sys
from datetime import datetime

import omero
import omero.clients
from omero.rtypes import rlist, rlong, rstring
from omero.cli import cli_login
from omero.gateway import BlitzGateway

# Test performance of channel rename methods...

def set_channel_names_new(conn, dataset_ids, nameDict, lookup_group=False):

    # lookup first object to get group...
    if lookup_group:
        conn.SERVICE_OPTS.setOmeroGroup("-1")
        ds = conn.getQueryService().get("Dataset", dataset_ids[0], conn.SERVICE_OPTS)
        group_id = ds.details.group.id.val
        conn.SERVICE_OPTS.setOmeroGroup(group_id)

    images = conn.getContainerService().getImages("Dataset", dataset_ids, None, conn.SERVICE_OPTS)
    imageIds = [i.getId().getValue() for i in images]
    return

    queryService = conn.getQueryService()
    params = omero.sys.Parameters()
    params.map = {'ids': rlist([rlong(id) for id in imageIds])}

    # load Pixels, Channels, Logical Channels and Images
    query = ("select p from Pixels p left outer "
                "join fetch p.channels as c "
                "join fetch c.logicalChannel as lc "
                "join fetch p.image as i where i.id in (:ids)")
    pix = queryService.findAllByQuery(query, params, conn.SERVICE_OPTS)

    maxIdx = max(nameDict.keys())
    # NB: we may have duplicate Logical Channels (Many Iamges in Plate
    # linked to same LogicalChannel)
    toSave = set()
    updateCount = 0
    ctx = conn.SERVICE_OPTS.copy()
    for p in pix:
        sizeC = p.getSizeC().getValue()
        if sizeC < maxIdx:
            continue
        updateCount += 1
        group_id = p.details.group.id.val
        ctx.setOmeroGroup(group_id)
        for i, c in enumerate(p.copyChannels()):
            if i+1 not in nameDict:
                continue
            lc = c.logicalChannel
            lc.setName(rstring(nameDict[i+1]))
            # Add the Channel
            toSave.add(c)

    toSave = list(toSave)
    # conn.getUpdateService().saveCollection(toSave, ctx)
    conn.getUpdateService().saveAndReturnArray(toSave, ctx)
    return {'imageCount': len(imageIds), 'updateCount': updateCount}



def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset', help='Dataset ID')
    parser.add_argument('channels', help='Comma-delimited channel names: DAPI,GFP')

    args = parser.parse_args(argv)
    dataset_id = int(args.dataset)
    data_type = "Dataset"
    nameDict = {}
    for count, name in enumerate(args.channels.split(",")):
        nameDict[count + 1] = name
    print("nameDict", nameDict)




    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        # conn.SERVICE_OPTS.setOmeroGroup("-1")

        # start = datetime.now()
        # set_channel_names_new(conn, [dataset_id], nameDict)
        # print("set_channel_names_new", datetime.now() - start)

        # start = datetime.now()
        # conn.SERVICE_OPTS.setOmeroGroup("-1")
        # conn.setChannelNames(data_type, [dataset_id], nameDict, channelCount=None)
        # print("setChannelNames", datetime.now() - start)

        # start = datetime.now()
        # set_channel_names_new(conn, [dataset_id], nameDict, True)
        # print("set_channel_names_new lookup_group", datetime.now() - start)

        # start = datetime.now()
        # conn.SERVICE_OPTS.setOmeroGroup("-1")
        # set_channel_names_new(conn, [dataset_id], nameDict)
        # print("set_channel_names_new group -1", datetime.now() - start)

        conn.SERVICE_OPTS.setOmeroGroup("-1")

        start = datetime.now()
        images = conn.getContainerService().getImages("Dataset", [dataset_id], None, conn.SERVICE_OPTS)
        ids1 = [i.getId().getValue() for i in images]
        print("containerService.getImages()", datetime.now() - start)

        start = datetime.now()
        images = conn.getObjects("Image", opts={'dataset': dataset_id})
        ids2 = [i.id for i in images]
        print("getObjects()", datetime.now() - start)

        ids1.sort()
        ids2.sort()
        assert ids1 == ids2

        print("Image count: ", len(ids1))

        # start = datetime.now()
        # conn.getContainerService().getImages("Image", (ids1[0],), None, conn.SERVICE_OPTS)[0]
        # print("getImages()", datetime.now() - start)


if __name__ == '__main__':  
    main(sys.argv[1:])