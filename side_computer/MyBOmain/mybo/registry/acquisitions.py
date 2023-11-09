from typing import Dict
from botorch.acquisition import (
    qExpectedImprovement,
)
from botorch.acquisition.logei import (
    qLogNoisyExpectedImprovement,
)
from botorch.acquisition.multi_objective import (
    qNoisyExpectedHypervolumeImprovement,
)

ACQUISITION_REGISTRY = {
    'LogNEI': qLogNoisyExpectedImprovement,
    'NEHVI': qNoisyExpectedHypervolumeImprovement,
    'EI': qExpectedImprovement,
}


def parse_acquisition_options(kwargs: Dict) -> Dict:
    return {}