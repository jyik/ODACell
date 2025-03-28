from typing import Dict

from omegaconf import OmegaConf
from ax.models.torch.botorch_modular.acquisition import Acquisition
from ax.models.torch.botorch_modular.surrogate import Surrogate
from ax.modelbridge.registry import Generators
from ax.modelbridge.generation_strategy import GenerationStep, GenerationStrategy

from registry.models import MODEL_REGISTRY, parse_model_options
from registry.acquisitions import ACQUISITION_REGISTRY, parse_acquisition_options
from registry.initialization import compute_doe

def get_generation_strategy(
        model_cfg: Dict, 
        acq_cfg: Dict, 
        acqopt_cfg: Dict,
        init_cfg: Dict,
        num_dimensions: int,
        budget: int = -1,
    ) -> Dict:
        
    model_enum = Generators.BOTORCH_MODULAR
    model_cfg = OmegaConf.to_container(model_cfg)
    bo_step = GenerationStep(
            # model=model_enum,
            model=model_enum,
            num_trials=budget,
            model_kwargs={
                # ensure we don't model the tracking metrics that are returned
                # witht the objecive 
                "fit_tracking_metrics": False,
                "surrogate": Surrogate(
                    botorch_model_class=MODEL_REGISTRY[model_cfg["name"]],
                    model_options=parse_model_options(ard_num_dims=num_dimensions, model_kwargs=model_cfg["kwargs"]),
                    mll_options=model_cfg.get("fit_kwargs"),
                ),
                "botorch_acqf_class": ACQUISITION_REGISTRY[acq_cfg.name],
                "acquisition_options": parse_acquisition_options(acq_cfg.get("kwargs")),
            },
            # must do OmegaConf.to_containe for dict conversion - serializability when saving
            model_gen_kwargs={"model_gen_options": { 
                    "optimizer_kwargs": OmegaConf.to_container(acqopt_cfg),
                },
            },
        )
    if compute_doe(init_cfg.num_doe, dimension=num_dimensions) > 0:
        init_step = GenerationStep(
            Generators.SOBOL,
            num_trials=compute_doe(init_cfg.num_doe, dimension=num_dimensions)
        )
        steps = [init_step, bo_step]
    else:
        steps = [bo_step]
    return GenerationStrategy(steps=steps)
    