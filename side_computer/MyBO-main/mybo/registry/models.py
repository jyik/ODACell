from omegaconf import OmegaConf
from typing import Dict, Optional

from botorch.models import (
    SingleTaskGP,
    SaasFullyBayesianSingleTaskGP
)
from botorch.models.fully_bayesian import (
    SaasPyroModel,
)


MODEL_REGISTRY = {
    "singletask": SingleTaskGP,
    "fullybayesian": SaasFullyBayesianSingleTaskGP,
}

FB_PRIOR_REGISTRY = {
    "saas": SaasPyroModel,
}


def parse_model_options(ard_num_dims: int, model_kwargs: Optional[Dict] = None) -> Dict:
    kwargs = model_kwargs if model_kwargs is not None else {}

    is_fully_bayesian = kwargs.pop("is_fully_bayesian", False)
    if "prior" in kwargs.keys():
        prior_name = kwargs.pop("prior")
        if is_fully_bayesian:
            kwargs["pyro_model"] = FB_PRIOR_REGISTRY[prior_name]()

    return kwargs