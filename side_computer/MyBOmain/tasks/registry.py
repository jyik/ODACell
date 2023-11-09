from typing import Dict, Any
from inspect import getmembers, isclass
from functools import partial

from omegaconf import OmegaConf, DictConfig
import botorch.test_functions as tfs
from tasks.callables import evaluate_test_function


SYNTHETIC_REGISTRY = {tf[0]: tf[1] for tf in getmembers(tfs, isclass)}
REAL_REGISTRY = {}
BENCHSUITE_REGISTRY = {}

SYN_KWARGS = {'negate': True}

def _get_test_function(function_name: str, **kwargs: Any):
    return SYNTHETIC_REGISTRY[function_name](**kwargs)


def get_task(cfg: DictConfig):
    function_name = cfg.name
    kwargs =  OmegaConf.to_container(cfg).get('kwargs', {})
    if function_name in SYNTHETIC_REGISTRY:
        SYN_KWARGS.update(kwargs)
    
        objective = _get_test_function(function_name=function_name, **SYN_KWARGS) 
        return partial(
            evaluate_test_function, objective)
    else:
        raise ValueError(f'Task {function_name} does not yet exist, or is missing a callable.')