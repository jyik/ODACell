from typing import Dict, Union

from omegaconf import DictConfig, OmegaConf
from ax.service.utils.instantiation import ObjectiveProperties


def parse_parameters(parameter_cfg: Dict) -> Dict:
    parameter_list = []
    for parameter_name, properties in parameter_cfg.items():
        per_param_dict = {}
        per_param_dict['name'] = parameter_name
        per_param_dict['bounds'] = list(properties.bounds)
        per_param_dict['type'] = properties.type
        per_param_dict['value_type'] = properties.get('value_type', 'float')
        per_param_dict['log_scale'] = properties.get('log_scale', False)        

        # TODO Convert to float if range?
        parameter_list.append(per_param_dict)
    return parameter_list

def parse_objectives(objective_cfg: Union[Dict, str]) -> Dict:
    objectives = {}

    # default (maximization) if nothing needs specification
    if isinstance(objective_cfg, str):
        for objective_name in objective_cfg.split():
            objectives[objective_name] = ObjectiveProperties(minimize=False)

    # otherwise, a dict needs to be passed in
    elif isinstance(objective_cfg, (dict, DictConfig)):
        for objective_name, properties in objective_cfg.items():
            objectives[objective_name] = ObjectiveProperties(
                minimize=False,
                threshold=properties.get('threshold', None),
            )
    
    else: 
        raise ValueError(f'Objectives must be string or dict, is {type(objective_cfg)}')
    
    return objectives
