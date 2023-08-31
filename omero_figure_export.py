
"""
See http://lists.openmicroscopy.org.uk/pipermail/ome-users/2017-February/006362.html
and
https://forum.image.sc/t/use-python-to-export-figures-from-omero/46520
"""

from omero.rtypes import wrap
from omero.gateway import BlitzGateway
import omero

# Script should already be installed here for figure app
SCRIPT_PATH = "/omero/figure_scripts/Figure_To_Pdf.py"
FIGURE_NAMESPACE = "omero.web.figure.json"

USERNAME = "username"
PASSWORD = "password"

conn = BlitzGateway(USERNAME, PASSWORD, host="localhost", port=4064)
conn.connect()

# cross-group query to search across all groups
conn.SERVICE_OPTS.setOmeroGroup(-1)

# list all Figures owned by me
user_id = conn.getUserId()
for figure_ann in conn.getObjects("FileAnnotation",
                                  attributes={'ns': FIGURE_NAMESPACE},
                                  opts={'owner': user_id}):
    print(figure_ann.getFile().getName(), figure_ann.id)

# Export a single figure...
figure_ann = conn.getObject("FileAnnotation", 7028)
figure_bytes = b''.join(figure_ann.getFileInChunks())
figure_json = figure_bytes.decode('utf8')

script_service = conn.getScriptService()
script_id = script_service.getScriptID(SCRIPT_PATH)

# set group for saving figure to same group as file
conn.SERVICE_OPTS.setOmeroGroup(figure_ann.getDetails().group.id.val)

input_map = {
    'Figure_JSON': wrap(figure_json),
    'Export_Option': wrap('PDF'),       # or 'TIFF'
    'Webclient_URI': wrap("http://your_server/webclient/"),  # Used in 'info' PDF page for links to images
}

proc = script_service.runScript(script_id, input_map, None, conn.SERVICE_OPTS)
job = proc.getJob()
cb = omero.scripts.ProcessCallbackI(conn.c, proc)

try:
    print("Job %s ready" % job.id.val)
    print("Waiting....")
    while proc.poll() is None:
        cb.block(1000)
    print("Callback received: %s" % cb.block(0))
    rv = proc.getResults(3)
finally:
    cb.close()

if rv.get('stderr'):
    print("Error. See file: ", rv.get('stderr').getValue().id.val)

ann_key = 'New_Figure'
if rv.get(ann_key):
    new_figure = rv.get(ann_key).getValue()
    figure_id = new_figure.id.val
    print("Figure file: ", figure_id)
    figure_pdf = conn.getObject("FileAnnotation", figure_id)
    figure_name = figure_pdf.getFile().getName()
    print("\nDownloading file... %s" % figure_name)
    with open(figure_name, 'wb') as f:
        for chunk in figure_pdf.getFileInChunks():
            f.write(chunk)
    print("File downloaded!")

conn.close()
