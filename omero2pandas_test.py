
import pandas as pd
import omero2pandas
from omero.cli import cli_login
# df = pandas.read_csv("/path/to/my_data.csv")

with cli_login() as cli:
    my_client=cli._client

    col_names = ['Image', 'Drug', 'Cell_Count', 'Control']
    image_ids = [259, 258, 261, 260, 257]
    reagent = ['DMSO', 'Nocodazole', 'Monastrol', 'Drug-X', 'foo']
    cell_count = [32, 25, 41, 29, 36]
    control = [True, False, False, False, False]

    df = pd.DataFrame(list(zip(image_ids, reagent, cell_count, control)), columns=col_names)
    ann_id = omero2pandas.upload_table(df, "omero2pandas_data", 55, "Dataset", omero_connector=my_client)
