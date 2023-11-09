from time import sleep

from typing import Any, List, Dict
import numpy as np


def mock_evaluate_mo(parameters: Any, metric_names: List[str]) -> Dict[str, float]:
    sleep(1)
    res = {mn: np.random.uniform(size=1)[0] for mn in metric_names.split()}
    return parameters[1], res