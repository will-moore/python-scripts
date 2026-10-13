

from omero.cli import cli_login
from omero.gateway import BlitzGateway, TagAnnotationWrapper
import requests

# Quick script to generate a bunch of "Phenotype" tags from the IDR searchengine
# Used for https://github.com/ome/omero-iviewer/pull/497

# This returns a good list of Phenotype values
url = "https://idr.openmicroscopy.org/searchengine/api/v1/resources/all/searchvalues/?key=Phenotype&value=e"

def phenotypes_to_tags(conn):

    # load json from url
    response = requests.get(url)
    phenotypes = response.json()

    for phenotype in phenotypes["image"]["data"]:
        tag_value = phenotype["Value"].title()
        print("tag_value", tag_value)
        tag = TagAnnotationWrapper(conn)
        tag.setValue(tag_value)
        tag.save()

def main():

    with cli_login() as cli:
        conn = BlitzGateway(client_obj=cli._client)

        phenotypes_to_tags(conn)


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
