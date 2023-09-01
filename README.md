# ODACell
Otto-Dobbie-Autonomous-Cell (ODACell, pronounced similarly to Odyssey) Assembly Platform

Robotic Setup intended to accelerate battery research. Automating the assembly and cycling process increases reproducibility of experiments and speeds up experimentation. Downsizing large scale automation to fit into the research lab can shift the focus of research to data analysis and optimization.  

## Overview
Several commercially available robots with separate functionalities are coordinated together to be able to assemble and cycle CR2025 type coin cells. The robots consist of:
- Three DOBOT MG400 4-axis robotic arms
- Opentrons OT2 liquid handling robot
- TMAXCN Crimper

The assembly process is monitored and controlled from one desktop computer, while cycling is controlled by another desktop computer. The computers communicate through TCP/IP protocol as well as the three DOBOTs. The liquid handling robot is controlled by SSH and the crimper is controlled through digital logic gates. 

Each DOBOT is equipped with a different head allowing different tasks to be executed. A vertical gripper is attached to one robot to pick up assembled coin cells and place them in the holder for cycling. A vacuum suction head is attached to another robot to pick up coin cell components and place them onto a holder to be crimped. Finally, a fixed horizontal claw is attached to the last robot to pick up the holder where all the coin cell parts are assembled, bring the holder into the liquid handling robot, and place the holder into the crimper machine.

## Dependencies & Requirements
### Scripts/Files Explanation
Python APIs are provided from DOBOT and Opentrons manufacturers to interface robots with Python. This constitutes the low-level code of the project. [dobot_api_v2.py](dobot_api_v2.py) contains the basic commands for the MG400 robotic arms. No separate file is needed for OT2 basic commands; they are already integrated within the robot.

Documentation of API for [DOBOT](https://github.com/Dobot-Arm/TCP-IP-Protocol/blob/master/README-EN.md) and [OT2](https://docs.opentrons.com/v2/) can be found on their github and website, respectively.

[main2.py](main2.py) is the main executable file, which starts the program. [robot_class_v2.py](robot_class_v2.py) and [server.py](server.py) are required to run it. [robot_class_v2.py](robot_class_v2.py) contains all higher-level functions (wrapper for low-level functions to perform robot-specific tasks; therefore, requires [dobot_api_v2.py](dobot_api_v2.py)). [server.py](server.py) must be running on a separate computer before main.py is run; it controls the Astrol Battery Cycler program and automated data collection (battery cycling). Communication of DOBOTs with the main computer and the main computer with the server computer is all ultimately controlled by the socket Python package (TCP/IP protocol); Communication between the main computer and OT2 is controlled by the paramiko Python package (SSH protocol).

The main program reads/writes from/to [coordinates.xlsx](./tables_coordinates/coordinates.xlsx), [electrolyte_list.xlsx](./tables_coordinates/electrolyte_list.xlsx), [make_cells.xlsx](./tables_coordinates/make_cells.xlsx) and [stock_list.xlsx](./tables_coordinates/stock_list.xlsx) occasionally. coordinates.xlsx contain position coordinates for where the pickup positions are for each DOBOT. electrolyte_list.xlsx contain a list of all electrolytes made with the OT2. make_cells.xlsx contain a list of all cells made and to be made; jobs are taken from this list to assemble coin cells. stock_list.xlsx contain information on what the composition of stock solutions are located in which wells. All these Excel sheets will be moved to a SQL database in the future. 

File dependencies:
```
main2.py
├── robot_class_v2.py
│   └── dobot_api_v2.py
├── server.py
├── coordinates.xlsx
├── electrolyte_list.xlsx
├── make_cells.xlsx
└── stock_list.xlsx
```

In the ot2 directory, [cellholder_wellplate.json](./ot2/cellholder_wellplate.json) should be loaded in the OT2's custom labware and [startup.py](./ot2/startup.py) should be placed in the running directory of the OT2. main.py on the main computer executes startup.py on the OT2 once it is connected via SSH.
### Python Packages
Main scripts were run using Python 3.9.7; *server.py* was run on a different computer with Python 3.10.1
The following is a list of python packages used and their versions. Compatibility of older package versions is not guaranteed.
- numpy 1.21.2
- pandas 1.3.5
- paramiko 2.7.2
- pywinauto 0.6.8, pywin32 303
- opentrons 5.0.2
- shortuuid 1.0.8

Note: the opentrons Python package (in [startup.py](./ot2/startup.py)) is specific to the OT2 and is already installed on the OT2 when received (i.e. it is not necessary to install it on the main computer)
### Robot Firmware
While conducting the following experiments, the firmware version on the robots were:
- DOBOT Controller version 1.5.7.0
- OT2 v1.1.0-25e5cea
## Installation Instructions
See the [Quick Start Guide](quickstart.md)
## Demonstration
[Youtube Video of Demo](https://youtu.be/r_yq-H4orKE)
