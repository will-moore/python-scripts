
import omero
from omero.gateway import BlitzGateway
from omero.rtypes import rint, rstring

from omero.cli import cli_login

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from skimage import data
from skimage.filters import threshold_otsu
from skimage.segmentation import clear_border
from skimage.measure import label, regionprops
from skimage.morphology import closing, square
from skimage.color import label2rgb


with cli_login() as cli:
    conn = BlitzGateway(client_obj=cli._client)

    total = 0


    threshold = 25
    # plate = conn.getObject("Plate", plate_id)
    # images = get_images_from_plate(plate)

    # dataset = conn.getObject('Dataset', 251)
    # images = dataset.listChildren()

    # for image in images:

    omero_image = conn.getObject("Image", 105234)
    pixels = omero_image.getPrimaryPixels()
    image = pixels.getPlane(theC=0)

    # https://scikit-image.org/docs/stable/auto_examples/segmentation/plot_label.html#sphx-glr-auto-examples-segmentation-plot-label-py

    # apply threshold
    thresh = threshold_otsu(image)
    bw = closing(image > thresh, square(3))

    # remove artifacts connected to image border
    cleared = clear_border(bw)

    # label image regions
    label_image = label(cleared)

    print("label_image", label_image.shape, label_image.min(), label_image.max())

    print("label_image", label_image)


    # to make the background transparent, pass the value of `bg_label`,
    # and leave `bg_color` as `None` and `kind` as `overlay`
    # image_label_overlay = label2rgb(label_image, image=image, bg_label=0)

    # fig, ax = plt.subplots(figsize=(10, 6))
    # ax.imshow(image_label_overlay)

    # for region in regionprops(label_image):
    #     # take regions with large enough areas
    #     if region.area >= 100:
    #         # draw rectangle around segmented coins
    #         minr, minc, maxr, maxc = region.bbox
    #         rect = mpatches.Rectangle((minc, minr), maxc - minc, maxr - minr,
    #                                 fill=False, edgecolor='red', linewidth=2)
    #         ax.add_patch(rect)

    # ax.set_axis_off()
    # plt.tight_layout()
    # plt.show()
