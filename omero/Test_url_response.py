"""
https://forum.image.sc/t/issue-outputting-original-file-from-omero-script-as-download/78635/3
"""

import omero.scripts as scripts
from omero.gateway import BlitzGateway
from omero.rtypes import wrap

def runScript():
    """
    The main entry point of the script, as called by the client via the
    scripting service, passing the required parameters.
    """

    client = scripts.client('Test_url.py', """Return URL""",
    )

    try:

        orig_file_id = 123
        webclient = "https://my-server/webclient/"
        url = f"{webclient}download_original_file/{orig_file_id}/"
        client.setOutput("URL", wrap({"type": "URL", "href": url}))
        client.setOutput("Message", wrap("Click the button to download"))


    finally:
        client.closeSession()

if __name__ == "__main__":
    runScript()