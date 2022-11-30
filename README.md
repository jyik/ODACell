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

## Demonstration
<p align="center">
<video src="https://youtu.be/r_yq-H4orKE"></video>
</p>

## Reproducibility
After assembling and cycling 80 cells of the test system, the relative standard deviation of the discharge capacity was 2%.

## Water Series Experiments
2.0 m LiClO<sub>4</sub> in water was added to the DMSO-electrolyte in various amounts and the dis/charge capacities and Coulombic efficiency was evaluated.

## Datafiles
Cycling Datafiles for all cells can be found in [datafiles.zip](datafiles.zip).

The analysis of the data can be found in [dataAnalysis.zip](dataAnalysis.zip).
