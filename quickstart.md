# Quick Installation and Setup
1. Clone the files. Move all the files in the side_computer directory to a separate computer where the Neware/Astrol Cycler is connected to.
2. Connect the DOBOTs and OT2 to the main computer. Check that the DOBOTs, OT2, and server computer can be connected to. Adjust the IP addresses in the main file as needed.
3. Check cycling protocol file on server computer. Update where server.py points to get the template cycling protocol file.
4. Install any python package dependencies. Update the directory for all support files (e.g. database file, BO directory, etc.).
5. (Optional) Arduino sensors can be used in the main script; if no Arduino is used, remove all accociated "arduino" code from main_v3.py (use Control+F). They are commented out by default.
6. Run server.py on the server computer.
7. Run main_v3.py on the main computer. Wait for startup and homing sequence.
8. Update consumables status using the "update" command (e.g. "update small_pipette_id 5").
9. Close any open database files or Excel sheets associated with the program — Python cannot access file if already open and will crash.
10. Use command "addjob {number of jobs}" to create new trials from BO if no jobs are already added.
11. Start coin cell assembly and cycling with command "makeCell"; if active material mass is different than the one set in server.py, use "makeCell *\[mg active material\]*"
