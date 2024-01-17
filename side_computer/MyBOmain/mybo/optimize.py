import hydra
from omegaconf import DictConfig, OmegaConf

from interface import get_designs, register_results, get_or_instantiate
from tasks.registry import get_task

# TODO consider transferring data between clients

@hydra.main(version_base=None, config_path="../configs", config_name="base")
def main(cfg : DictConfig) -> None:
    # Prints out the settings that are run in a nice format...
    print(OmegaConf.to_yaml(cfg))
    
    ax_client = get_or_instantiate(cfg)

    # TODO either entire loop or single eval/call? cfg.closed_loop/open_loop?
    # ensure the auxilliary task (if any) gets retrieved here as well
    if cfg.max_rounds > 0:
        objective = get_task(cfg)
    else: 
        objective = None
        
    for opt_round in range(cfg.max_rounds):
        designs = get_designs(
            max_num_designs=cfg.batch_size, 
            client=ax_client, 
            client_path=cfg.save_path, 
            save=cfg.save
        )
        if cfg.aux_task is not None:
            results = [objective(index, parameters, ax_client, cfg.aux_task)
                        for index, parameters in designs]
        else:
            results = [objective(index, parameters) for index, parameters in designs]
        register_results(results, client=ax_client, client_path=cfg.save_path, save=cfg.save)


if __name__ == '__main__':
    main()