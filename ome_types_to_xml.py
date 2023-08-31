
from ome_types import to_xml
from ome_types.model.simple_types import PixelType
from ome_types.model import Pixels, OME, Image

ome = OME()
pt = PixelType("int8")
p = Pixels(dimension_order="XYZCT", size_c=1, size_t=1, size_z=10, size_x=256, size_y=256, type=pt, metadata_only=True)
i = Image(pixels=p)
ome.images = [i]
print(to_xml(ome))
