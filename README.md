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

## Experimentation Using the Robotic System
Two experiments were conducted on ODACell. The first was to observe the reproducibility of automated coin cell assembly. The second explored different electrolyte compositions. Detailed methods, results and discussion provided in the manuscript.
### Test System
- LiFePO<sub>4</sub> || Li<sub>4</sub>Ti<sub>5</sub>O<sub>12</sub> full cells 
- 2.0 m LiClO<sub>4</sub> in dimethyl sulfoxide (DMSO) electrolyte
- CR2025 type coin cell configuration
### Reproducibility
After assembling and cycling 80 cells of the test system, the relative standard deviation of the discharge capacity was 2%.
### Water Series Experiments
2.0 m LiClO<sub>4</sub> in water was added to the DMSO-electrolyte in various amounts and the dis/charge capacities and Coulombic efficiency was evaluated. Similar performance metrics were observed between 0% – 4% water in DMSO-electrolyte.
## Datafiles & Analysis
### Cycling Datafiles for all cells can be found in [datafiles.zip](datafiles.zip).
Datafiles are the output files of the Astrol Battery Cycler software. In the zip file, the datafiles are split into two folders: ***reproducibility\_0vol*** and ***water series***.

***reproducibility\_0vol*** contains 83 datafiles, of which 80 were used for determining spread and distribution of the capacities of the assembled batteries. ***water series*** contains 48 datafiles, of which 45 were used to compare the performance of three different electrolyte formulations with varying amounts of added water. To separate each category, there is the string "\_*\[water concentration\]*" added to the end of the filename (e.g. "...\_04.txt" signifies the electrolyte with 4% water).
- **Filename format:** *\[date\]*\_*\[5 digit ID\]*\_*\[random string\]*\_*\[any comments\]*.txt  
  e.g. 2022-10-12_66845_Z32zYRTZ3diVqEUzMhdfD2.txt (no comments after *random string*)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2022-10-03_12413_PpCWRt6iFrJsX8EFocfPn6\_removed.txt (comment after *random string*)
- **Filetype format:** plain text (.txt) CSV filetype with tab ("\\t") delimiter.
- **Data format:** header - any additional comments (usually "no\_additional\_comments")  
  &nbsp;&nbsp;&nbsp;Data recorded every 15 seconds  
  &nbsp;&nbsp;&nbsp;Six columns:
  - TT \[min\] –⁠ Total time of the experiment in minutes
  - U \[V\] –⁠ Cell voltage in volts
  - I \[mA\] –⁠ Current in milliamperes
  - Z1 \[\] – Cycle number
  - C \[Ah/kg\] – Cell capacity in ampere-hour per kilogram of limiting active material (in this case Li<sub>4</sub>Ti<sub>5</sub>O<sub>12</sub>)
  - Comment – Cycling procedure comments (e.g. when charge or discharge ends, etc.)
### The analysis of the data can be found in [dataAnalysis.zip](dataAnalysis.zip).
Zip file contains two Jupyter notebooks: ***for_reproducibility.ipynb*** and ***for_waterSeries.ipynb***
- ***for_reproducibility.ipynb***: Uses only files in *./datafiles/reproducibility\_0vol/* to determine and plot distributions of capacity and differential capacity.
-  ***for_waterSeries.ipynb***: Uses all the datafiles and categorizes them to plot the performance of each group. 

#### Data Cleaning/Preprocessing
No preprocessing of data was done for distributions and cell voltage vs. capacity plots besides grouping data based on cycle number, dis/charge state, and/or water content. Dis/charge capacities for each cycle were taken to be the highest value of each cycle grouping and Coulombic efficiency was the quotient of charge and discharge capacities. Resampling and calculating the differential capacities on a spline fit of the data was done to obtain smoother differential capacities vs. cell voltage plots.
