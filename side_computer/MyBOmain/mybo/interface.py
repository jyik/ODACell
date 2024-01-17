import os
import warnings

from typing import Union, List, Dict, Tuple, Optional
from omegaconf import DictConfig
import pandas as pd

from ax.core.base_trial import TrialStatus
from ax.service.ax_client import AxClient
from utils.saving import save_run, AX_NAME, suppress_stdout_stderr

from utils.config import parse_parameters, parse_objectives
from registry.strategy import get_generation_strategy
# TODO move to interface.py

def get_or_instantiate(cfg: DictConfig) -> AxClient:
    if len(cfg.resume_path) > 0:
        client = _get_client(cfg.resume_path)
        save_run(cfg.save_path, client)
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
    num_dimensions = len(parse_parameters(
            cfg.task.parameters, 
            cfg.task.get("dim", 0), 
            cfg.task.get("embedding", 0)
    ))
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
        parameters=parse_parameters(
            cfg.task.parameters, 
            cfg.task.get("dim", 0), 
            cfg.task.get("embedding", 0)
        ),
        objectives=parse_objectives(cfg.task.objectives),
        parameter_constraints=cfg.task.get('constraints', None),
        overwrite_existing_experiment=True,
    )
    cfg.save_path = modify_save_path(cfg)
    save_run(cfg.save_path, ax_client, save_client=cfg.save)
    return ax_client

def modify_save_path(cfg: DictConfig):
    # gets all the attributes of each config that should be appended to the save
    task_name, algo_name, seed_name = cfg.save_path.split("/")[-3:]
    rest_of_name = cfg.save_path.split("/")[:-3]
    cfgitem_appends = {}
    for key, val in cfg.items():
        if isinstance(val, DictConfig):
            cfgitem_appends[key] = val.get("appends")

    # the task attribute should be added to the outermost dir
    if cfgitem_appends["task"] is not None:
        attr_names = [attr + str(cfg.task[attr]) for attr in 
                      cfgitem_appends["task"].strip().split(',')]
        task_name = '-'.join([task_name] + attr_names)
    
    del cfgitem_appends["task"]
        # the task attribute should be added to the outermost dir
    for key, val in cfgitem_appends.items():
        # TODO could consider not throwing an error if the appended
        # attribute is missing from the config
        if val is not None:
            attr_names = [attr + str(cfg[key][attr]) for attr in 
                        cfgitem_appends[key].strip().split(',')]
            algo_name = '-'.join([algo_name] + attr_names)

    full_name = '/'.join(rest_of_name + [task_name, algo_name, seed_name])
    return full_name

def _get_client(client_path: str):
    with suppress_stdout_stderr():
        ax_client = AxClient.load_from_json_file(client_path)
    return ax_client


def get_designs(
    max_num_designs: int = 1, 
    client: Union[AxClient, None] = None, 
    client_path: Union[str, None] = None,
    save: bool = True
) -> List[Tuple[Dict[str, float], int]]:
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
        save_run(client_path, client, save_client=save)
    return batch_array


def register_results(
    results: List[Tuple[Dict[str, float], int]],
    client_path: Optional[Union[str, None]] = None,
    client: Optional[Union[AxClient, None]] = None, 
    save: Optional[bool] = True,
) -> None:
    # (trial_index, {coul_eff: 0.5})
    # TODO save run
    if client is None:
        client = _get_client(client_path + AX_NAME)
    
    for result in results:
        # for some reason, ax wants it the other way around when it's a result...
        # i.e. trial index first
        client.complete_trial(result[1], result[0])
        save_run(client_path, client, save_client=save)


def cancel_trials(
    trial_index: Union[int, List[int]], 
    client_path: Union[str, None] = None,
    client: Union[AxClient, None] = None, 
    save: bool = True,
) -> None:
    if client is None:
        client = _get_client(client_path + AX_NAME)
    if isinstance(trial_index, str):
        client.log_trial_failure(trial_index=trial_index)
    elif isinstance(trial_index, list):
        for idx in trial_index:
            client.log_trial_failure(trial_index=idx)
    else:
        raise ValueError(f'Trial index if of invalid type {type(trial_index)}'
                          'Must be int or list of ints.')
    
    save_run(client_path, client, save_client=save)


def get_trial_subset(
    subset: str = "running", # running, completed, failed  etc.
    client_path: Union[str, None] = None,
    client: Union[AxClient, None] = None, 
) -> List[Tuple[Dict[str, float], int]]:
    if client is None:
        client = _get_client(client_path + AX_NAME)

    trials = client.experiment.trials
    running_trials = [] 
    for t_idx, value in trials.items():
        if value.status == getattr(TrialStatus, subset.upper()):
            running_trials.append((client.get_trial_parameters(t_idx), t_idx))

    return running_trials


def append_to_client(client: AxClient, df: pd.DataFrame, path: str):
    param_names = list(client.experiment.parameters.keys())
    obj_names = list(client.experiment.metrics.keys())
    non_metadata = obj_names + param_names
    
    for idx in range(len(df)):
        param_data = df.loc[idx, param_names].values
        obj_data = df.loc[idx, obj_names].values
        metadata = df.loc[idx, [col not in non_metadata for col in df.columns]]
    
        parameter_dict = {col: param for col, param in zip(param_names, param_data)}
        obj_dict = {obj: param for obj, param in zip(obj_names, obj_data)}
        output, trial_index = client.attach_trial(parameter_dict)
        if metadata.trial_status == "COMPLETED":
            client.complete_trial(trial_index, obj_dict)
        elif metadata.trial_status == "FAILED":
            client.log_trial_failure(trial_index=trial_index)
        elif metadata.trial_status == "RUNNING":
            print(f"Trial {trial_index} is still considered running.")
    
    save_run(save_path=path.strip('ax_client.json'), ax_client=client)