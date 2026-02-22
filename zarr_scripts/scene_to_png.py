

# url = "https://uk1s3.embassy.ebi.ac.uk/idr/zarr/test-data/v0.6.dev3/idr0050/4995115_output_to_ms.zarr"

import os
import math
import zarr
from PIL import Image, ImageDraw, ImageFont

import argparse

MS_BORDER = "#a0a0a0"
MS_FILL = "#ededf8"
CS_BORDER = MS_BORDER
CS_FILL = "#ffffff"
CS_HIGHLIGHT = "#fff8e1"
TRANSFORM_COLOR = "#1d8dcd"
TRANSFORM_FILL = "#e6f6fd"
TRANSFORM_WIDTH = 1
TEXT_COLOR = "#303030"
FONT_SIZE = 18
SMALL_FONT_SIZE = 12

argparser = argparse.ArgumentParser(description='Draw a scene graph from an OME-Zarr file')
argparser.add_argument('url', type=str, help='URL or path to OME-Zarr file')
args = argparser.parse_args()
url = args.url

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path_to_font = os.path.join(current_dir, "FreeSans.ttf")
    font = ImageFont.truetype(path_to_font, FONT_SIZE)
    font_small = ImageFont.truetype(path_to_font, SMALL_FONT_SIZE)
except Exception:
    font = ImageFont.load_default()
    font_small = ImageFont.load_default()

root = zarr.open_group(url, mode="r")

scene_attrs = root.attrs.get("ome")["scene"]

# keep track of things to draw...

# key is path.zarr/name and coods are x,y,width,height
systemCoords = {}
# each is {'name': "image.zarr", coords: {x,y,width,height}}
multiscales = []
# transforms is list of [{"start": "path.zarr/name", "end": "path.zarr/name", "transform": {...}}]
transforms = []

# gap between boxes etc.
SPACE = 20
TXT_MARGIN = 5
# start multiscale box ('scene') top-left of image...
ms_x = SPACE
ms_y = SPACE


child_paths = set()
for ct in scene_attrs.get("coordinateTransformations", []):
    # Now process the coordinateTransformations...
    start = f"{ct["input"].get("path", "scene")}/{ct["input"].get("name")}"
    end = f"{ct["output"].get("path", "scene")}/{ct["output"].get("name")}"
    transforms.append({"start": start, "end": end, "transform": ct})

    # keep track of child paths to process later...
    for io in ("input", "output"):
        path = ct[io].get("path", None)
        if path is not None:
            child_paths.add(path)

# find all coordinate systems in scene...
max_width = 0
# add "scene" text height...
box = font.getbbox("scene")
# keep track of system coords as we go...
ms_height = SPACE + box[3] + SPACE
system_x = ms_x + SPACE
system_y = ms_y + SPACE + box[3] + SPACE
for system in scene_attrs.get("coordinateSystems", []):
    text = system["name"]
    box = font.getbbox(text)
    txt_w = box[2] + 2 * TXT_MARGIN
    txt_h = box[3] + 2 * TXT_MARGIN
    systemCoords[f'scene/{text}'] = {"x": system_x, "y": system_y, "width": txt_w, "height": txt_h, "text": text}
    max_width = max(max_width, txt_w)
    system_y += txt_h + SPACE
    ms_height += txt_h + SPACE

# now we know dimentions for "scene"...
scene_box = {"name": "scene",
                    "coords": {"x": ms_x, "y": ms_y,
                               "width": max_width + 2 * SPACE,
                               "height": ms_height}}
multiscales.append(scene_box)

# start a new column for multiscales...
ms_x += scene_box["coords"]["width"] + SPACE * 5
ms_y = SPACE
system_x = ms_x + SPACE
# repeat for each multiscale image...
child_paths = list(child_paths)
child_paths.sort()
for path in child_paths:
    image_attrs = root[path].attrs.get("ome")
    for ms in image_attrs.get("multiscales", []):
        # parse coordinateSystems, assigining coords for each box...
        bbox = font.getbbox(path)
        max_width =  bbox[2]
        ms_height = SPACE + bbox[3] + SPACE
        system_y = ms_y + SPACE + box[3] + SPACE
        for system in ms.get("coordinateSystems", []):
            text = system["name"]
            box = font.getbbox(text)
            txt_w = box[2] + 2 * TXT_MARGIN
            txt_h = box[3] + 2 * TXT_MARGIN
            systemCoords[f'{path}/{text}'] = {"x": system_x, "y": system_y, "width": txt_w, "height": txt_h, "text": text}
            max_width = max(max_width, txt_w)
            system_y += txt_h + SPACE
            ms_height += txt_h + SPACE
        
        # handle datasets... - combine whole pyramid into one box for now...
        datasets = ms.get("datasets", [])
        text = ", ".join([d["path"] for d in datasets])
        box = font.getbbox(text)
        txt_w = box[2] + 2 * TXT_MARGIN
        txt_h = box[3] + 2 * TXT_MARGIN
        systemCoords[f'{path}/{datasets[0]["path"]}'] = {"x": system_x, "y": system_y, "width": txt_w, "height": txt_h, "text": text}
        max_width = max(max_width, txt_w)
        system_y += txt_h + SPACE
        ms_height += txt_h + SPACE
        # just show transform from FIRST dataset - assume only ONE tranform
        ct = datasets[0].get("coordinateTransformations")[0]
        start = f"{path}/{ct["input"]}"    # spec says this matches "path"
        end = f"{path}/{ct["output"]}"
        transforms.append({"start": start, "end": end, "transform": ct})


        # add a box that contains the coordinateSystems
        multiscales.append({"name": path,
                            "coords": {"x": ms_x, "y": ms_y,
                                       "width": max_width + 2 * SPACE,
                                       "height": ms_height}})
        ms_y += ms_height + SPACE

        # Now process the coordinateTransformations...
        for ct in ms.get("coordinateTransformations", []):
            start = f"{path}/{ct["input"]}"
            end = f"{path}/{ct["output"]}"
            transforms.append({"start": start, "end": end, "transform": ct})

# find coordinateSystems that are NOT in inputs...
csKeys = set(systemCoords.keys())
for t in transforms:
    csKeys.remove(t["start"])
# ...add show in highlight color
for k in csKeys:
    systemCoords[k]["fill"] = CS_HIGHLIGHT


# draw the result ------------------->

max_x = max([ms["coords"]["x"] + ms["coords"]["width"] for ms in multiscales[1:]])
canvas_width = max_x + SPACE
canvas_height = multiscales[-1]["coords"]["y"] + multiscales[-1]["coords"]["height"] + SPACE
canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
draw = ImageDraw.Draw(canvas)

for ms in multiscales:
    # draw box for multiscale
    ms_coords = ms["coords"]
    draw.rounded_rectangle((ms_coords["x"], ms_coords["y"],
                    ms_coords["x"] + ms_coords["width"],
                    ms_coords["y"] + ms_coords["height"]), radius=5, outline=MS_BORDER, fill=MS_FILL)
    draw.text((ms_coords["x"] + SPACE, ms_coords["y"] + SPACE), ms["name"], fill=TEXT_COLOR, font=font)


for system in systemCoords.values():
    fill = system.get("fill", CS_FILL)
    draw.rounded_rectangle((system["x"], system["y"],
                    system["x"] + system["width"],
                    system["y"] + system["height"]), radius=5, outline=CS_BORDER, fill=fill
                    )
    draw.text((system["x"] + TXT_MARGIN, system["y"] + TXT_MARGIN), system["text"], fill=TEXT_COLOR, font=font)


# https://stackoverflow.com/questions/246525/how-can-i-draw-a-bezier-curve-using-pythons-pil
def make_bezier(xys):
    # xys should be a sequence of 2-tuples (Bezier control points)
    n = len(xys)
    combinations = pascal_row(n-1)
    def bezier(ts):
        # This uses the generalized formula for bezier curves
        # http://en.wikipedia.org/wiki/B%C3%A9zier_curve#Generalization
        result = []
        for t in ts:
            tpowers = (t**i for i in range(n))
            upowers = reversed([(1-t)**i for i in range(n)])
            coefs = [c*a*b for c, a, b in zip(combinations, tpowers, upowers)]
            result.append(
                tuple(sum([coef*p for coef, p in zip(coefs, ps)]) for ps in zip(*xys)))
        return result
    return bezier

def pascal_row(n, memo={}):
    # This returns the nth row of Pascal's Triangle
    if n in memo:
        return memo[n]
    result = [1]
    x, numerator = 1, n
    for denominator in range(1, n//2+1):
        # print(numerator,denominator,x)
        x *= numerator
        x /= denominator
        result.append(x)
        numerator -= 1
    if n&1 == 0:
        # n is even
        result.extend(reversed(result[:-1]))
    else:
        result.extend(reversed(result))
    memo[n] = result
    return result

ts = [t/100.0 for t in range(101)]

def draw_curve(start, end, right=True):
    x1, y1 = start
    x2, y2 = end
    dy = math.fabs(y2 - y1)
    if right:
        offset = dy * 2
        xys = [(x1, y1), (x1 + offset, y1), (x2 + offset, y2), (x2, y2)]
    else:
        midpoint = (x1 + x2) / 2
        xys = [(x1, y1), (midpoint, y1), (midpoint, y2), (x2, y2)]
    bezier = make_bezier(xys)
    points = bezier(ts)
    draw.line(points, fill=TRANSFORM_COLOR, width=TRANSFORM_WIDTH)

    # add arrow head polygon
    arrow_size = -10 if right or x1 > x2 else 10
    points = [(x2, y2), (x2 - arrow_size, y2 - arrow_size/2), (x2 - arrow_size, y2 + arrow_size/2)]
    draw.polygon(points, fill=TRANSFORM_COLOR)


# draw lines for transforms...
for t in transforms:
    start_coords = systemCoords.get(t["start"])
    end_coords = systemCoords.get(t["end"])
    to_or_from_scene = t["start"].startswith("scene/") != t["end"].startswith("scene/")
    start_x = start_coords["x"] + start_coords["width"]
    start_y = start_coords["y"] + start_coords["height"] / 2
    end_x = end_coords["x"] + end_coords["width"]
    end_y = end_coords["y"] + end_coords["height"] / 2
    if to_or_from_scene:
        # update non-scene endpoint
        if not t["start"].startswith("scene/"):
            start_x = start_coords["x"]
        else:
            end_x = end_coords["x"]
        draw_curve((start_x, start_y), (end_x, end_y), False)
    else:
        draw_curve((start_x, start_y), (end_x, end_y))

    # add text for transform type
    tf = t["transform"]
    ct_type = tf["type"]
    if ct_type == "sequence":
        ct_type += " (" + ", ".join([t["type"] for t in tf["transformations"]]) + ")"
    bbox = font_small.getbbox(ct_type)
    text_x = (start_x + end_x) / 2 - (bbox[2] / 2)
    if not to_or_from_scene:
        text_x += math.fabs(end_y - start_y) * 1.5
    text_y = (start_y + end_y) / 2 - bbox[3] / 2

    draw.rounded_rectangle((text_x, text_y,
                    text_x + bbox[2] + 2 * TXT_MARGIN,
                    text_y + bbox[3] + 2 * TXT_MARGIN), radius=FONT_SIZE, outline=TRANSFORM_COLOR, fill=TRANSFORM_FILL
                    )
    draw.text((text_x + TXT_MARGIN, text_y + TXT_MARGIN), ct_type, fill=TEXT_COLOR, font=font_small)

canvas.show()
