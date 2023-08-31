import cv2
import numpy as np

from omero.gateway import BlitzGateway
conn = BlitzGateway('username', 'password', host='localhost', port=4064)
conn.connect()

imageId = 3701
image = conn.getObject("Image", imageId)
z, t, c = 0, 0, 0                     # first plane of the image
pixels = image.getPrimaryPixels()
im = pixels.getPlane(z, c, t)      # get a numpy array.

# im = cv2.imread("blob.jpg", cv2.IMREAD_GRAYSCALE)

detector = cv2.SimpleBlobDetector()
keypoints = detector.detect(im)

print(keypoints)

im_with_keypoints = cv2.drawKeypoints(im, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

cv2.imshow("Keypoints", im_with_keypoints)
cv2.waitKey(0)
