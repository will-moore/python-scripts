

import requests

SERVER = "https://idr.openmicroscopy.org/"

screen_id = 2651

plates_url = f"{SERVER}webclient/api/plates/?id={screen_id}"

plates_json = requests.get(plates_url).json()["plates"]

field = 0

images = []
for plate in plates_json[:3]:
    plate_id = plate['id']

    plate_url = f"{SERVER}webgateway/plate/{plate_id}/{field}/"

    plate_json = requests.get(plate_url).json()
    # find first not-null Well
    image = None
    for row in plate_json["grid"]:
        for col in row:
            if image is None:
                image = col
    print("img", image["id"])
    images.append(image)


with open("idr0088_files.csv", "w") as f:

    for image in images:
        file_paths_url = f"{SERVER}webgateway/original_file_paths/{image['id']}/"
        files_json = requests.get(file_paths_url).json()
        print(files_json["client"][0])
        f.write(files_json["client"][0] + "\n")
