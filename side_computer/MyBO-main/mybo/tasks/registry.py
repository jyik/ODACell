from typing import Dict, Any, Callable, Tuple, Optional, List
from inspect import getmembers, isclass
from functools import partial

from omegaconf import OmegaConf, DictConfig

from ax.service.ax_client import AxClient
import botorch.test_functions as tfs
from tasks.callables import (
    evaluate_test_function,
    evaluate_benchsuite_funciton,
)


SYNTHETIC_REGISTRY = {tf[0]: tf[1] for tf in getmembers(tfs, isclass)}
REAL_REGISTRY = {} # TODO a generic callable for arbitrary tasks
BENCHSUITE_REGISTRY = {} # TODO get all the tasks from benchsuite (in their containers)

SYN_KWARGS = {'negate': True, 'noise_std': 0.0}

def _get_test_function(function_name: str, **kwargs: Any):
    return SYNTHETIC_REGISTRY[function_name](**kwargs)


def get_task(cfg: DictConfig) -> Tuple[Callable, Callable]:
    """Returns the primary objective (y-value) and any auxilliary objectives
    such as noiseless evaluations, or test-set MLL

    Args:
        cfg (DictConfig): the config.

    Returns:
        Tuple[Callable, Callable]: Objective and possible auxilliary objectives
    """    
    aux_task = cfg.get("aux_task", None)
    cfg = cfg.task
    function_name = cfg.name
    
    cfg = OmegaConf.to_container(cfg)
    if "dim" in cfg.keys():
        SYN_KWARGS["dim"] = cfg.pop("dim")

    # TODO benchmark-dependent kwargs. Bundle together more
    for key, val in cfg.items():
        if key in SYN_KWARGS:
            SYN_KWARGS[key] = val
            
    if function_name in SYNTHETIC_REGISTRY:    
        objective = _get_test_function(function_name=function_name, **SYN_KWARGS) 

        return partial(evaluate_test_function, objective)
    
    elif function_name in BENCHSUITE_REGISTRY:
        objective = evaluate_benchsuite_funciton(function_name=function_name, **BS_KWARGS)
    else:
        raise ValueError(f'Task {function_name} does not yet exist, or is missing a callable.')
