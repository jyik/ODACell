from typing import Dict
import time
import torch
from botorch.test_functions import SyntheticTestFunction


# TODO make a registry for these

def evaluate_test_function(
    test_function: SyntheticTestFunction, 
    parameters: Dict[str, float], 
    trial_index: str, 
    seed: int=None
    ) -> Dict[str, float]:
    """All test functions simply take x_1, ..., x_n as input and output y1, ..., y_m.

    Args:
        parameters (Dict[str, float]): dict of parameters and their associated value.
        seed (int, optional): _description_. If returned with noise, fix the noise randomness.

    Returns:
        _type_: _description_
    """    
    time.sleep(1)
    x = torch.tensor(
        [[parameters[f"x{i+1}"] for i in range(len(parameters))]])
    print(x)
    if seed is not None:
        eval = test_function(x, seed=seed)
    else:
        eval = test_function(x)

    return {f'y{m + 1}': e.item() for m, e in enumerate(eval.T)}, trial_index
    