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
from botorch.acquisition.bayesian_active_learning import (
    qBayesianActiveLearningByDisagreement,
    qStatisticalDistanceActiveLearning,
    qBayesianQueryByComittee,
)
from botorch.acquisition.scorebo import (
    qSelfCorrectingBayesianOptimization
)
from botorch.acquisition.diversity import (
    qDistanceWeightedImprovementOverThreshold
)
ACQUISITION_REGISTRY = {
    'LogNEI': qLogNoisyExpectedImprovement,
    'NEHVI': qNoisyExpectedHypervolumeImprovement,
    'EI': qExpectedImprovement,
    'BALD': qBayesianActiveLearningByDisagreement,
    'BQBC': qBayesianQueryByComittee,
    'SAL': qStatisticalDistanceActiveLearning,
    'SCoreBO': qSelfCorrectingBayesianOptimization,
    'DWIT': qDistanceWeightedImprovementOverThreshold,
}


def parse_acquisition_options(kwargs: Dict) -> Dict:
    return kwargs