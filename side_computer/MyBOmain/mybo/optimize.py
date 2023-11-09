import hydra
from omegaconf import DictConfig, OmegaConf

from interface import get_designs, register_results, get_or_instantiate

# TODO consider transferring data between clients

@hydra.main(version_base=None, config_path="../configs", config_name="base")
def main(cfg : DictConfig) -> None:
    # Prints out the settings that are run in a nice format...
    print(OmegaConf.to_yaml(cfg))
    
    ax_client = get_or_instantiate(cfg)
    # TODO either entire loop or single eval/call? cfg.closed_loop/open_loop?
   
    
    for opt_round in range(cfg.max_rounds):
        designs = get_designs(max_num_designs=cfg.batch_size, client_path=cfg.save_path, save=cfg.save)
        results = [objective(index, parameters) for index, parameters in designs]
        register_results(results, client_path=cfg.save_path, save=cfg.save)


if __name__ == '__main__':
    main()