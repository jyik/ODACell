# ODACell
Otto-Dobbie-Autonomous-Cell (ODACell, pronounced similarly to Odyssey) Assembly and Testing Platform

Robotic Setup intended to accelerate battery research. Automating the assembly and cycling process increases reproducibility of experiments and speeds up experimentation. Downsizing large scale automation to fit into the research lab can shift the focus of research to data analysis and optimization.  

## Overview
Several commercially available robots with separate functionalities are coordinated together to be able to assemble and cycle CR2025 type coin cells. The robots consist of:
- Two DOBOT MG400 4-axis robotic arms
- Opentrons OT2 liquid handling robot
- TMAXCN Crimper

The assembly process is monitored and controlled from one desktop computer, while cycling is controlled by another desktop computer. The computers communicate through TCP/IP protocol as well as the two DOBOTs. The liquid handling robot is controlled by SSH and the crimper is controlled through digital logic gates. 

Each DOBOT is equipped with a different head allowing different tasks to be executed. A vertical gripper is attached to one robot to pick up assembled coin cells and place them in the holder for cycling. A fixed horizontal claw is attached to the other robot to pick up the holder where all the coin cell parts are assembled, bring the holder into the liquid handling robot, and place the holder into the crimper machine. Both robots additionally are equip with a vacuum suction head and are responsible for picking up the coin cell components and stacking the components in the holder. Each robot is responsible for specific components associated with the negative electrode or positive electrode, thus preventing electrode cross-contamination.

## Dependencies & Requirements
### Scripts/Files Explanation
Python APIs are provided from DOBOT and Opentrons manufacturers to interface robots with Python. This constitutes the low-level code of the project. [dobot_api_v2.py](dobot_api_v2.py) contains the basic commands for the MG400 robotic arms. No separate file is needed for OT2 basic commands; they are already integrated within the robot.

Documentation of API for [DOBOT](https://github.com/Dobot-Arm/TCP-IP-Python-V4/blob/main/README-EN.md) and [OT2](https://docs.opentrons.com/v2/) can be found on their github and website, respectively.

[main_v3.py](main_v3.py) is the main executable file, which starts the program. [dobot_class.py](dobot_class.py) contains all higher-level functions (wrapper for low-level functions to perform robot-specific tasks; therefore, requires [dobot_api_v2.py](dobot_api_v2.py)). [server.py](./side_computer/server.py) must be running on a separate computer before main.py is run; it controls the cycling program (NEWARE) and automated data collection (battery cycling). Communication of DOBOTs with the main computer and the main computer with the server computer is all ultimately controlled by the socket Python package (TCP/IP protocol); Communication between the main computer and OT2 is controlled by the paramiko Python package (SSH protocol).

On the separate computer that runs the cycling program, the Bayesian Optimization files are located in a folder called MyBOmain. The Client API from Ax is utilized and all relevant commands are located in the folder. The Bayesian Optimization Client files are also stored there when created. The separate computer is, therefore, responsible for analysing the cycling data once finished and updating the optimization client. When a new job is called from the main computer, the separate computer acquires new trials from the optimization client and sends the trial(s) to the main computer as an object wrapped in a pickle. The Bayesian optimization is pulled from [https://github.com/hvarfner/MyBO](https://github.com/hvarfner/MyBO). Custom python packages for the Bayesian optimization are used and listed below.

The main program reads/writes from/to a database file created in DuckDB that stores all the metadata (components, electrolyte formulations, coin cell assembled - jobs, etc.). coordinates.parquet contain position coordinates for where the pickup positions are for each DOBOT. Neware_cycler_state.parquet contains information on which cycler is occupied or free. track_objs.parquet contain information on the state of the setup (how many trays are available, which row to pick up comonents from, which wells are free to use or contain electrolyte, etc.).

Python File dependencies:
```
main_v3.py
├── dobbie_grip.py
│   └── dobot_class.py
│       ├── coordinate_funcs.py
│       └── dobot_api_v2.py
├── dobbie_crimp.py
│   └── dobot_class.py
│       ├── coordinate_funcs.py
│       └── dobot_api_v2.py
├── background_processes.py
│   ├── server_connection.py
│   ├── odacell_states.py
│   └── database_functions.py
│       └── qt_ui.py
├── OT2_class.py
└── camera.py

server.py
├── data_analyzer.py
├── neware_api.py
└── interface.py
```

In the ot2 directory, [cellholder_1_wellplate_120ul.json](./ot2/cellholder_1_wellplate_120ul.json) should be loaded in the OT2's custom labware and [startup.py](./ot2/startup.py) should be placed in the running directory of the OT2. main.py on the main computer executes startup.py on the OT2 once it is connected via SSH.
### Python Packages
Main scripts were run using Python 3.9.7; *server.py* was run on a different computer with Python 3.10.1
The requirements.txt file contain a list of python packages used and their versions. Compatibility of other package versions is not guaranteed. For the Bayesian optimization, custom packages are used:
- [botorch](https://github.com/hvarfner/botorch/tree/diversity)
- [Ax](https://github.com/hvarfner/Ax)

Note: the opentrons Python package (in [startup.py](./ot2/startup.py)) is specific to the OT2 and is already installed on the OT2 when received (i.e. it is not necessary to install it on the main computer)
### Robot Firmware
- DOBOT Controller version 1.5.9.0
- OT2 v1.1.0-25e5cea
## Installation Instructions
See the [Quick Start Guide](quickstart.md)
## Demonstration
[Youtube Video of Coin Cell Assembly Demo](https://www.youtube.com/watch?v=mAtBjrnRx-I)

[Youtube Video of Electrolyte Mixing Demo](https://www.youtube.com/watch?v=7C7m4rLT9PY)
