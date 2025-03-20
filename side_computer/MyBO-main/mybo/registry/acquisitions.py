from typing import Dict

from botorch.acquisition.active_learning import qNegIntegratedPosteriorVariance
from botorch.acquisition.logei import (
    qLogNoisyExpectedImprovement,
)
from botorch.acquisition.multi_objective.logei import (
    qLogNoisyExpectedHypervolumeImprovement,
)
from botorch.acquisition.diversity import (
    qDistanceWeightedImprovementOverThreshold
)
ACQUISITION_REGISTRY = {
    'LogNEI': qLogNoisyExpectedImprovement,
    'NEHVI': qLogNoisyExpectedHypervolumeImprovement,
    'DWIT': qDistanceWeightedImprovementOverThreshold,
    'NIPV': qNegIntegratedPosteriorVariance,
}


def parse_acquisition_options(kwargs: Dict) -> Dict:
    return kwargs