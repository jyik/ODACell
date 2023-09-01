# First Experimentations Using the Robotic System
Two experiments were conducted on ODACell. The first was to observe the reproducibility of automated coin cell assembly. The second explored different electrolyte compositions. Detailed methods, results and discussion provided in the [manuscript](https://doi.org/10.1039/D3DD00058C).
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
