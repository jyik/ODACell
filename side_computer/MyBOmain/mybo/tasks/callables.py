from typing import Dict, Optional, Tuple, List

import torch
from ax.service.ax_client import AxClient
from botorch.test_functions import SyntheticTestFunction

from tasks.aux_objective import evaluate_mll, get_best_guess


# TODO make a registry for these
NUM_MLL_POINTS = 2500
def evaluate_test_function(
    test_function: SyntheticTestFunction, 
    parameters: Dict[str, float], 
    trial_index: str, 
    ax_client: Optional[AxClient] = None,
    aux_objectives: Optional[List[str]] = ["noiseless_eval"], # TODO implement this
) -> Tuple[Dict[str, float], str]:
    """All test functions simply take x_1, ..., x_n as input and output y1, ..., y_m.

    Args:
        parameters (Dict[str, float]): dict of parameters and their associated value.
        seed (int, optional): If returned with noise, fix the noise randomness.

    Returns:
        _type_: _description_
    """
    x = torch.tensor(
        [[parameters[f"x{i+1}"] for i in range(test_function.dim)]])
    eval = test_function(x)
    # flip the sign if negated
    
    noiseless_eval = (-1) ** test_function.negate * test_function.evaluate_true(x)
    output_dict = {f'y{m + 1}': e.item() for m, e in enumerate(eval.T)}

    if "noiseless_eval" in aux_objectives:
        output_dict.update({f'f{m + 1}': e.item() for m, e in enumerate(noiseless_eval.T)})

    if "mll" in aux_objectives:
        mll_rmse = evaluate_mll(ax_client, test_function, NUM_MLL_POINTS)
        output_dict.update(mll_rmse)
    # evaluate test RMSE, test MLL
    
    if "best_guess" in aux_objectives:
        best_guess = get_best_guess(ax_client, test_function)
        output_dict.update({"Best Guess": best_guess})
    return output_dict, trial_index
    

def evaluate_benchsuite_funciton(
    function: callable,
    parameters: Dict[str, float], 
    trial_index: str, 
    seed: Optional[int] = 0,
) -> Tuple[Dict[str, float], str]:
    pass