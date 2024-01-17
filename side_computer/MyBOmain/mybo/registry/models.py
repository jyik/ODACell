from omegaconf import OmegaConf
from typing import Dict, Optional

from botorch.models import (
    SingleTaskGP, 
    FixedNoiseGP, 
    SaasFullyBayesianSingleTaskGP
)
from botorch.models.fully_bayesian import (
    SaasPyroModel,
    LogNormalPyroModel,
    SingleTaskPyroModel,
)


MODEL_REGISTRY = {
    "singletask": SingleTaskGP,
    "fixednoise": FixedNoiseGP,
    "fullybayesian": SaasFullyBayesianSingleTaskGP,
}

FB_PRIOR_REGISTRY = {
    "saas": SaasPyroModel,
    "gamma": SingleTaskPyroModel,
    "lognormal": LogNormalPyroModel,
}

def parse_model_options(kwargs: Optional[Dict]) -> Dict:
    kwargs = OmegaConf.to_container(kwargs) if kwargs is not None else {}
    if "prior" in kwargs.keys():
        prior_name = kwargs.pop("prior")
        kwargs["pyro_model"] = FB_PRIOR_REGISTRY[prior_name]()

    return kwargs