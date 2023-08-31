
# https://forum.image.sc/t/harmonization-of-image-metadata-for-different-file-formats-omero-mde/50827/8

import omero
from omero.gateway import BlitzGateway

conn = BlitzGateway('username', 'password', port=4064, host='localhost')
conn.connect()

# current group
group_id = conn.getEventContext().groupId
print('group_id', group_id)
# Use -1 for cross-group query
conn.SERVICE_OPTS.setOmeroGroup(group_id)

# Find Images by Pixel Type
# https://docs.openmicroscopy.org/omero-blitz/5.5.8/slice2html/omero/model/Pixels.html#pixelsType

params = omero.sys.ParametersI()
params.addString('value', 'uint8')
# pagination
offset = 0
limit = 100
params.page(offset, limit)

query = """
    select img from Image img
    join fetch img.pixels as pixels
    where pixels.pixelsType.value = :value
    """

# images = conn.getQueryService().findAllByQuery(query, params, conn.SERVICE_OPTS)

# for img in images:
#     print(img.id.val, img.name.val)


# Convert original metadata to Key-Value pairs
iid = 3457
keys = [
    "Wavelength 1 mean intensity",
    "Z axis angle",
    "Extended header Z9 W2 T0:exWavelen"
]
image = conn.getObject("Image", iid)
f, series_metadata, global_metadata = image.loadOriginalMetadata()
key_value_data = []
for metadata in (series_metadata, global_metadata):
    for key, value in metadata:
        if key in keys:
            print('key, value', key, value, type(value))
            key_value_data.append([key, str(value)])
print('key_value_data', key_value_data)
if len(key_value_data) > 0:
    map_ann = omero.gateway.MapAnnotationWrapper(conn)
    namespace = "custom.from.original_metadata"
    map_ann.setNs(namespace)
    map_ann.setValue(key_value_data)
    map_ann.save()
    image.linkAnnotation(map_ann)

# Find Images by Key-Value pairs (map annotations)

params = omero.sys.ParametersI()
params.addString('key', '[OME-Model]{0}#[OME:Image]{0}#[MyCustomObject]{0} | ExampleKey_1')
params.addString('value', 'food')
offset = 0
limit = 100
params.page(offset, limit)

# Here we use 'projection' query to load specific values rather than whole objects
# This can be more performant, but here I'm using it based on Map-Annotation
# query examples in omero-mapr
query = """
    select image.id, image.name from 
    ImageAnnotationLink ial
    join ial.child a
    join a.mapValue mv
    join ial.parent image
    where mv.name = :key and mv.value like :value"""
# result = conn.getQueryService().projection(query, params, conn.SERVICE_OPTS)
# for row in result:
#     print("Img ID: %s Name: %s" % (row[0].val, row[1].val))


# Testing conn.getObjectsByMapAnnotations
# print(len(list(conn.getObjectsByMapAnnotations('Image', value='ACA'))))

# found = list(conn.getObjectsByMapAnnotations('Image', key='*Antibody'))
# print(len(found))

# found = list(conn.getObjectsByMapAnnotations('Image', key='*Anti'))
# print(len(found))

# found = list(conn.getObjectsByMapAnnotations('Image', key='*Anti*'))
# print(len(found))

# found = list(conn.getObjectsByMapAnnotations('Image', key='Antibody'))
# print(len(found))

# found = list(conn.getObjectsByMapAnnotations('Image', key='[OME-Model]{0}#[OME:Image]{0}#[MyCustomObject]{0} | ExampleKey_1', value='foo*'))
# print(len(found))

# found = list(conn.getObjectsByMapAnnotations('Image', key='Test_k*', value='my%va*'))
# print(len(found))

# for image in found:
#     print('Image-----', image.id)
#     for ann in image.listAnnotations():
#         print(ann._obj.__class__.__name__)
#         # if ann.OMERO_CLASS == omero.model.MapAnnotationI:
#         print(ann.getValue())

# for l in range(10):
#     found = list(conn.getObjectsByMapAnnotations('Image', opts={"limit": 100 * l}))
#     found2 = list(conn.getObjects('Image', opts={"limit": 100 * l}))
#     print(l, len(found), len(found2))

conn.close()
