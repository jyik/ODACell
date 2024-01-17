from typing import Callable
import torch
from torch import Tensor
from torch.quasirandom import SobolEngine
from botorch.utils.transforms import unnormalize
from botorch.test_functions import SyntheticTestFunction
from gpytorch.mlls import ExactMarginalLogLikelihood
from ax.service.ax_client import AxClient

NUM_SPLITS = 10
def evaluate_mll(ax_client: AxClient, objective: SyntheticTestFunction, num_test_points: int):
    results = {'MLL': 0, 'RMSE': 0}
    try:
        model = ax_client.get_model_predictions()
    except NotImplementedError:
        return results

    sobol = SobolEngine(len(objective.bounds.T), scramble=True, seed=42)
    test_samples = sobol.draw(num_test_points)

    split_len = int(len(test_samples) / NUM_SPLITS)


    for split_idx in range(NUM_SPLITS):
        split_idx_low, split_idx_high = split_idx * \
            split_len, (1 + split_idx) * split_len
        test_sample_batch = test_samples[split_idx_low:split_idx_high]

        output = -objective.evaluate_true(unnormalize(test_sample_batch, objective.bounds))
        y_transform = ax_client._generation_strategy.model.transforms['StandardizeY']
        y_mean, y_std = y_transform.Ymean["y1"], y_transform.Ystd["y1"]

        mu, _ = ax_client._generation_strategy.model.model.predict(
            test_sample_batch)
        mu_true = (mu * y_std + y_mean).flatten()
    
        model = ax_client._generation_strategy.model.model.surrogate.model
        mll = ExactMarginalLogLikelihood(model.likelihood, model)
        model.eval()
        preds = model(test_sample_batch)
        norm_yvalid = (output - y_mean) / y_std

        norm_yvalid = norm_yvalid.flatten()
        # marg_dist = MultivariateNormal(predmean, predcov)
        # joint_loglik = -mll(marg_dist, norm_yvalid).mean()
        results['MLL'] = results['MLL'] - \
            mll(preds, norm_yvalid).mean().item()
        results['RMSE'] = results['RMSE'] + \
            torch.pow(output - mu_true, 2).mean().item()

    return {key: val / NUM_SPLITS for key, val in results.items()}


def get_best_guess(ax_client: AxClient, objective: SyntheticTestFunction):
    try:
        model = ax_client.get_model_predictions()
    except NotImplementedError:
        return -1e6
    sobol = SobolEngine(len(objective.bounds.T), scramble=True, seed=42)
    gp = ax_client.generation_strategy.model.model.surrogate.model

    from botorch.acquisition import PosteriorMean
    from botorch.optim import optimize_acqf
    post_mean = PosteriorMean(gp)
    best_guess, acqval = optimize_acqf(
        acq_function=post_mean, 
        bounds=objective.bounds,
        raw_samples=8192,
        num_restarts=20,
        q=1,
        options={"sample_around_best": True, "batch_limit": 256},
    )
    return -objective.evaluate_true(best_guess).item()
