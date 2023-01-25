# Quick Installation and Setup
1. Clone the files. Move the server.py to a separate computer where the Astrol Battery Cycler is connected to.
2. Connect the three DOBOTs and OT2 to the main computer. Check that the DOBOTs, OT2, and server computer can be connected to. Adjust the IP addresses in main2.py as needed.
3. Check cycling protocol file on server computer. Update where server.py points to get the template cycling protocol file.
4. Install any python package dependencies. Update the directory for all support files (e.g. make_cells.xlsx, etc.).
5. (Optional) Arduino sensors are used in the main script; if no Arduino is used, remove all accociated "arduino" code from main2.py (use Control+F).
6. Run server.py on the server computer.
7. Run main2.py on the main computer. Wait for startup and homing sequence.
8. Update consumables status using the "update" command (e.g. "update small_pipette_id 5").
9. Update support files/add jobs to make_cells.xlsx. Close Excel sheets — Python cannot access file if already open in Excel and will crash.
10. Start coin cell assembly and cycling with command "makeCell"; if active material mass is different than the one set in server.py, use "makeCell *\[mg active material\]*"
