from typing import Dict

from botorch.models import (
    SingleTaskGP, 
    FixedNoiseGP, 
    SaasFullyBayesianSingleTaskGP
)


MODEL_REGISTRY = {
    'singletask': SingleTaskGP,
    'fixednoise': FixedNoiseGP,
    'fullybayesian': SaasFullyBayesianSingleTaskGP,
}

def parse_model_options(kwargs: Dict) -> Dict:
    return {}