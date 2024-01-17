import sys
import numpy as np

import torch
from torch import Tensor

from ax.modelbridge.cross_validation import cross_validate
from ax.plot.contour import interact_contour
from ax.plot.diagnostic import interact_cross_validation
from ax.plot.scatter import interact_fitted, plot_objective_vs_constraints, tile_fitted
from ax.plot.slice import plot_slice
from ax.service.ax_client import AxClient, ObjectiveProperties
from ax.utils.measurement.synthetic_functions import hartmann6
from ax.utils.notebook.plotting import init_notebook_plotting, render

from mybo.interface import _get_client 

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib import cm


PARAMS = ["x1", "x2"]
OBJECTIVES = ["y1", "y2"]
GRID_SIZE = 41
LEVELS = 25


cm = plt.cm.get_cmap('RdBu')
X1, X2 = np.linspace(0, 1, GRID_SIZE), np.linspace(0, 1, GRID_SIZE)
X1, X2 =  np.meshgrid(X1, X2)
X_plot = np.append(X1.flatten()[:, np.newaxis], X2.flatten()[:, np.newaxis], axis=1)
Xt_plot = Tensor(X_plot)

path = sys.argv[1]
ax_client = _get_client(path)
ax_client.fit_model()
df = ax_client.get_trials_data_frame()

thresholds = ax_client.experiment.optimization_config.objective_thresholds
threshold_vals = np.array([thresholds[i].bound for i in range(len(thresholds))]) 
threshold_vals = threshold_vals


Y = df.loc[:, OBJECTIVES].to_numpy()
all_better = np.all(Y > threshold_vals, axis=1).reshape(-1) 
one_better = np.any(Y > threshold_vals, axis=1).reshape(-1)

    
fig, axes = plt.subplots(1, len(OBJECTIVES), figsize=(10 * len(OBJECTIVES), 10))
for idx, objective in enumerate(OBJECTIVES):
    
    idx_arr = np.array(ax_client.objective_names) == objective
    if len(OBJECTIVES) == 1:
        ax_ = axes
    else:
        ax_ = axes[idx]

    obj_index = np.argwhere(idx_arr).item()

    X = df.loc[:, PARAMS].to_numpy()
    
    gp = ax_client.generation_strategy.model.model.surrogate.model
    ps = gp.posterior(Xt_plot)
    mean = ps.mean[..., obj_index].detach().numpy().reshape(GRID_SIZE, GRID_SIZE)
    
    ax_.contourf(X1, X2, mean, levels=LEVELS)
    
    sc = ax_.scatter(X[:, 0], X[:, 1], s=180, c='white', edgecolors='k', linewidths=2)
    sc = ax_.scatter(X[one_better, 0], X[one_better, 1], s=180, c='navy', edgecolors='k', linewidths=2)
    sc = ax_.scatter(X[all_better, 0], X[all_better, 1], s=180, c='red', edgecolors='k', linewidths=2)
    ax_.set_title(objective, fontsize=24)

plt.show()

