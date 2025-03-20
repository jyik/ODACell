import os
from os.path import abspath
from argparse import ArgumentParser

import pandas as pd
from ax.service.ax_client import AxClient
import sys
sys.path.append(r"C:\Users\renrum\Desktop\code\MyBO-main")
sys.path.append(r"C:\Users\renrum\Desktop\code\MyBO-main\mybo")
from mybo.interface import _get_client, append_to_client



if __name__ == "__main__":
    parser = ArgumentParser(
        prog='Append data to client',
        description="Provide the path to the data, and the (possibly empty) client to append it to.",
    )

    parser.add_argument('-c', '--client')
    parser.add_argument('-d', '--data')
    args = parser.parse_args()

    client_path = abspath(args.client)
    data_path = abspath(args.data)
    print(f"Trying to append {abspath(args.data)} to {abspath(args.client)}.")

    client = _get_client(client_path)
    data_df = pd.read_csv(data_path)
    append_to_client(client, data_df, path=args.client)
