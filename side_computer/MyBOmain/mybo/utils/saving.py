import sys
import os
from os.path import join, dirname, abspath

import warnings
from ax.service.ax_client import AxClient

AX_NAME = '_ax_client.json'
RUN_NAME = '_run.csv'

def save_run(save_path: str, ax_client: AxClient, save_client: bool = True) -> None:
    os.makedirs(dirname(save_path), exist_ok=True) 
    client_path = save_path + AX_NAME
    results_path = save_path + RUN_NAME
    if save_client:
        with suppress_stdout_stderr():
            ax_client.save_to_json_file(client_path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        ax_client.get_trials_data_frame().to_csv(results_path, index=False)


class DummyOutput(object):
    def __init__(self, *args, **kwargs):
        pass

    def write(self, *args, **kwargs):
        pass


class suppress_stdout_stderr(object):
    def __init__(self):
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def __enter__(self, *args, **kwargs):
        out = DummyOutput()
        sys.stdout = out
        sys.stderr = out

    def __exit__(self, *args, **kwargs):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
