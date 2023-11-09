import os
import warnings

from typing import Union, List, Dict, Tuple
from omegaconf import DictConfig
from utils.config import parse_parameters, parse_objectives
from registry.strategy import get_generation_strategy

from ax.service.ax_client import AxClient
from utils.saving import save_run, AX_NAME, suppress_stdout_stderr

# TODO move to interface.py

def get_or_instantiate(cfg: DictConfig) -> AxClient:
    if len(cfg.resume_path) > 0:
        client = _get_client(cfg.resume_path)
    elif os.path.isfile(cfg.save_path + AX_NAME):
        if cfg.override:
            client = _instantiate_client(cfg)
        else:
            raise SystemExit(f'Not overriding existing client at {cfg.save_path}{AX_NAME}.'
                '\nSet override=1 in the command line to override anyway. Exiting.'
            )
    else:
        client = _instantiate_client(cfg)
    return client


def _instantiate_client(cfg: DictConfig) -> AxClient:
    # If we enter a path to a run to resume, try and do so (should be a JSON)
    num_dimensions = len(cfg.task.parameters)
    generation_strategy = get_generation_strategy(
        model_cfg=cfg.model, 
        acq_cfg=cfg.acq, 
        acqopt_cfg=cfg.acqopt, 
        init_cfg=cfg.init,
        num_dimensions=num_dimensions,
    )

    ax_client = AxClient(generation_strategy=generation_strategy)
    ax_client.create_experiment(
        name=cfg.experiment_name,
        parameters=parse_parameters(cfg.task.parameters),
        objectives=parse_objectives(cfg.task.objectives),
        parameter_constraints=cfg.task.get('constraints', None),
        overwrite_existing_experiment=True
    )
    save_run(cfg.save_path, ax_client)
    return ax_client


def _get_client(client_path: str):
    #with warnings.catch_warnings():
    #    warnings.simplefilter("ignore", category=FutureWarning)
    with suppress_stdout_stderr():
        ax_client = AxClient.load_from_json_file(client_path)
    return ax_client


def get_designs(
    max_num_designs: int = 1, 
    client: Union[AxClient, None] = None, 
    client_path: Union[str, None] = None,
    save: bool = True
) -> List[Tuple[Dict[str, float], str]]:
    # (trial_index, {x_1: 0.5, x_2: 2.3, ...})
    if client is None:
        client = _get_client(client_path + AX_NAME)

    batch_array = []
    for _ in range(max_num_designs):
        # trial contains both the parameters and the index of the trial
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            trial = client.get_next_trial()
        batch_array.append((trial))
        if save:
            save_run(client_path, client)
    return batch_array


def register_results(
    results: List[Tuple[Dict[str, float], str]],
    client: Union[AxClient, None] = None, 
    client_path: Union[str, None] = None,
    save: bool = True,
) -> None:
    # (trial_index, {coul_eff: 0.5})
    # TODO save run
    if client is None:
        client = _get_client(client_path + AX_NAME)
    
    for result in results:
        # for some reason, ax wants it the other way around when it's a result...
        # i.e. trial index first
        client.complete_trial(result[1], result[0])
        if save:
            save_run(client_path, client)


def cancel_trial(
    trial_index: str, 
    client: Union[AxClient, None] = None, 
    client_path: Union[str, None] = None,
    save: bool = True,
) -> None:
    if client is None:
        client = _get_client(client_path + AX_NAME)
    client.log_trial_failure(trial_index=trial_index)
    if save:
        save_run(client_path, client)
