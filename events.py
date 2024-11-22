
# https://forum.image.sc/t/is-there-a-way-to-properly-capture-events-in-omero-api/87527

# use psql to see what events table looks like...

#                                Table "public.event"
#       Column       |            Type             | Collation | Nullable | Default 
# -------------------+-----------------------------+-----------+----------+---------
#  id                | bigint                      |           | not null | 
#  permissions       | bigint                      |           | not null | 
#  status            | character varying(255)      |           |          | 
#  time              | timestamp without time zone |           | not null | 
#  containingevent   | bigint                      |           |          | 
#  external_id       | bigint                      |           |          | 
#  experimenter      | bigint                      |           | not null | 
#  experimentergroup | bigint                      |           | not null | 
#  session           | bigint                      |           | not null | 
#  type              | bigint                      |           | not null | 
# Indexes:
#     "event_pkey" PRIMARY KEY, btree (id)
#     "event_external_id_key" UNIQUE CONSTRAINT, btree (external_id)
#     "i_event_containingevent" btree (containingevent)
#     "i_event_experimenter" btree (experimenter)
#     "i_event_experimentergroup" btree (experimentergroup)
#     "i_event_session" btree (session)
#     "i_event_type" btree (type)
# Foreign-key constraints:
#     "fkevent_containingevent_event" FOREIGN KEY (containingevent) REFERENCES event(id)
#     "fkevent_experimenter_experimenter" FOREIGN KEY (experimenter) REFERENCES experimenter(id)
#     "fkevent_experimentergroup_experimentergroup" FOREIGN KEY (experimentergroup) REFERENCES experimentergroup(id)
#     "fkevent_external_id_externalinfo" FOREIGN KEY (external_id) REFERENCES externalinfo(id)
#     "fkevent_session_session" FOREIGN KEY (session) REFERENCES session(id)
#     "fkevent_type_eventtype" FOREIGN KEY (type) REFERENCES eventtype(id)
# Referenced by:
#     TABLE "_reindexing_required" CONSTRAINT "fk_reindexing_required_event_id" FOREIGN KEY (event_id) REFERENCES event(id)
#     TABLE "affinetransform" CONSTRAINT "fkaffinetransform_creation_id_event" FOREIGN KEY (creation_id) REFERENCES event(id)
# ...

# and the eventType table...

# idr=> select * from eventtype;
#  id | permissions |   value    | external_id 
# ----+-------------+------------+-------------
#   0 |         -52 | Bootstrap  |            
#   1 |         -52 | Import     |            
#   2 |         -52 | Internal   |            
#   3 |         -52 | Shoola     |            
#   4 |         -52 | User       |            
#   5 |         -52 | Task       |            
#   6 |         -52 | Test       |            
#   7 |         -52 | Processing |            
#   8 |         -52 | FullText   |            
#   9 |         -52 | Sessions   |            
# (10 rows)

import sys
from datetime import datetime

import omero
import omero.clients
from omero.rtypes import rstring, rtime
from omero.cli import cli_login
from omero.gateway import BlitzGateway


def find_event_by_id(conn, event_id):
    query_service = conn.getQueryService()
    params = omero.sys.ParametersI()
    params.addId(event_id)
    otypes = ["Project", "Dataset", "Image", "Screen", "Plate", "Well", "Roi", "Shape"]
    for otype in otypes:
        query = "select d from %s as d where d.details.updateEvent.id=:id" % otype
        obj = query_service.findByQuery(query, params, conn.SERVICE_OPTS)
        if obj is not None:
            print( " ---> Edited Object:", otype, obj.id.val, obj.details.updateEvent)
            return
    print("No object found for event id:", event_id)


def main(argv):

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)
        query_service = conn.getQueryService()

        # get event types...
        event_types = {}
        for et in query_service.findAllByQuery("select t from EventType as t", None, None):
            event_types[et.value.val] = et.id.val
        print("event_types", event_types)

        # find events from the last month or hour
        now = datetime.now()
        # now = now.replace(month=now.month-1)
        now = now.replace(hour=now.hour-1)
        print("Finding events since:", str(now))
        millisecs = now.timestamp() * 1000
        print("millisecs", millisecs)

        # Find most bunch of events of each type...
        # for evt_type in ["User"]:    # event_types.keys():
        params = omero.sys.ParametersI()
        offset = 0
        limit = 50
        params.page(offset, limit)

        # params.add('type', rstring(evt_type))
        params.add('time', rtime(millisecs))

        query = """select e from Event as e
            join fetch e.type as t
            left outer join fetch e.containingEvent as evt
            order by e.time desc
        """

        results = query_service.findAllByQuery(query, params, None)

        # print(result)
        # print("\nevt_type", evt_type)
        for evt in results:
            print(evt.id.val, str(datetime.fromtimestamp(evt.time.val/1000)), evt.type.value.val)
            # print(evt)
            # these both seem to be None
            # print('cevt', evt.containingEvent, evt.status)
            # Try to find the object associated with the event...
            find_event_by_id(conn, evt.id.val)
        print("results", len(results))


        # find recent TagAnnotation links...
        for dtype in ("Project", "Dataset", "Image"):
            query = ("select l from %sAnnotationLink as l "
                     "join fetch l.parent as p "
                     "join fetch l.child as a "
                     # "left outer join fetch a.file " - only for FileAnnotation
                     "join fetch l.details.creationEvent as evt "
                     "where evt.time>:time "
                     "and a.class=TagAnnotation "
                     "order by evt.time desc" % dtype)

            results = query_service.findAllByQuery(query, params, None)
            print(dtype, "links...")
            for link in results:
                print("Tag", link.child.textValue.val, str(datetime.fromtimestamp(link.details.creationEvent._time.val/1000)))

if __name__ == '__main__':  
    main(sys.argv[1:])
