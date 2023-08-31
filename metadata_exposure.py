
# https://forum.image.sc/t/omero-python-api-how-to-get-metadata-for-image-id/47418

import omero
from omero.gateway import BlitzGateway

conn = BlitzGateway('username', 'password', port=4064, host='localhost')
conn.connect()

image_id = 3454
image = conn.getObject("Image", image_id)

for theC in range(image.getSizeC()):
    # You can filter by C/Z/T here, to get a particular plane
    planeInfo = image.getPrimaryPixels().copyPlaneInfo(theC=theC, theZ=0, theT=0)

    for pi in planeInfo:
        deltaT = pi.getDeltaT(units="SECOND")
        exposure = pi.getExposureTime(units="SECOND")
        if deltaT is not None:
            print('deltaT secs', deltaT.getValue())
        if exposure is not None:
            print('exposure secs', exposure.getValue())

conn.close()
