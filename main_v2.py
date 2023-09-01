from concurrent.futures import thread
from glob import glob
from http import server
from multiprocessing.sharedctypes import Value

import duckdb
from dobbie_crimp import D_CRIMP
from dobbie_grip import D_GRIP
from OT2_class import OT2
from odacell_states import Trackables
from database_functions import get_electrolyte, dispense_electrolyte, get_job, update_stock, add_new_material
import time
import threading
import socket
import os, sys
import random
import re
import polars as pl
import numpy as np
import pickle
import sqlite3
import datetime

# ---
# -----Astrol Client Setup-----
# ---

HEADER = 64
PORT = 5051
FORMAT = 'utf-8'
SERVER = "130.238.197.94"
ADDR = (SERVER, PORT)

def send(msg):
    """Sends commands to the Astrol server"""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)
    message = msg.encode(FORMAT)
    msg_length = len(message)
    send_length = str(msg_length).encode(FORMAT)
    send_length += b' ' * (HEADER - len(send_length))
    client.send(send_length)
    client.send(message)
    returnMsg = client.recv(2048).decode(FORMAT)
    client.close()
    return returnMsg

# ---
# ----- Establish Robot and Server Connections-----
# ---
try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)
    client.close()
except:
    sys.exit('Cannot connect to Astrol server')

try:
    dgrip = D_GRIP('192.168.1.6')
    dcrimp = D_CRIMP('192.168.2.6')
    otto = OT2('192.168.5.5')
    #arduino = arduino_ObjDetect("COM4")
except:
    sys.exit('Connection to Robot(s) failed')



# ---
# -----Set Trackable States-----
# ---

track_objs = Trackables()
track_objs.load()

otto.small_tip_index = track_objs.small_pipette_int
otto.large_tip_index = track_objs.large_pipette_int
otto.odacell_well_index = track_objs.wellIndex_int

# ---
# ----- Connect to Jobs Database -----
# ---

conn = duckdb.connect('odaCell_DB.duckdb')

# ---
# -----Setup and Start Worker Queue-----
# ---

serverRunning = True
Queue = []
dobots_positions = {'crimp': dcrimp.pos, 'grip': dgrip.pos}

def worker():
    while serverRunning:
        if len(Queue) > 0:
            command = Queue.pop(0)
            print("\nElement dequeued from queue: "+command)
            # define command actions below (makeCell probably the most important)
            if "makeCell" in command.split():
                if len(command.split()) > 1:
                    mass = command.split(maxsplit=1)[1]
                    results = makeCell(mass)
                else:
                    results = makeCell()
                if results == "add_queue":
                    Queue.append(command)
            elif "addjob" in command.split():
                add_job()
            elif "makeSeries" in command.split():
                pass

            # "startCell CellID" starts cell on astrol - already assembled and in place
            elif "startCell" in command.split():
                rand_name = command.split()[1]
                returnMsg = send('C startCell '+rand_name)
                print(returnMsg)
            
            # stops all cells and removes them all from astrol
            elif command == "stopAllCells":
                returnMsg = send('C stopAllCells')
                print(returnMsg)
            
            # prints list of cells cycling
            elif command == 'listCells':
                print(cycler_status)

            # "prepareCell CellID" prepares astrol
            elif command == 'prepareCell':
                rand_name = "{:05d}".format(random.randint(0,99999))
                returnMsg = send('C prepareCell '+rand_name)
                print(returnMsg)
            
            # "stopCell CellID" stops and removes the cell from astrol
            elif "stopCell" in command.split():
                rand_name = command.split()[1]
                returnMsg = send('C stopCell '+rand_name)
            
            # prints liveupdate of astrol cells
            elif command == 'liveupdate':
                print(cycler_status)

            # "update variable value" updates trackable objects
            elif "update" in command.split():
                var_to_update = command.split()[1]
                var_val = command.split()[2]
                if var_to_update == "num_trays":
                    track_objs.numTrays.set_state(int(var_val))
                    print("update successful; current number of trays in stack: {}".format(track_objs.numTrays.current_state_value))
                elif var_to_update == "stack_id":
                    track_objs.stackID.send('to_stack'+var_val)
                    print("update successful")
                elif var_to_update == "tray_row_id":
                    track_objs.rowID.set_row(int(var_val))
                    print("update successful; current tray row ID: {}".format(track_objs.rowID.current_state_value))
                elif var_to_update == "area_loaded":
                    if var_val.lower() == "t":
                        track_objs.working_area_loaded_int = 1
                    elif var_val.lower() == "f":
                        track_objs.working_area_loaded_int = 0
                    print("update successful; working area is loaded: {}".format(track_objs.working_area_loaded_int))
                elif var_to_update == "small_pipette_id":
                    track_objs.small_pipette_int = int(var_val)
                    otto.small_tip_index = int(var_val)
                    print("update successful; small_tip_index = {}".format(track_objs.small_pipette_int))
                elif var_to_update == "large_pipette_id":
                    track_objs.large_pipette_int = int(var_val)
                    otto.large_tip_index = int(var_val)
                    print("update successful; large_tip_index = {}".format(track_objs.large_pipette_int))
                elif var_to_update == "elec_vol":
                    track_objs.electrolyte_vol_int = int(var_val)
                    print("update successful; OT2 dispensing volume: {} uL".format(track_objs.electrolyte_vol_int))
                elif var_to_update == "well_id":
                    otto.odacell_well_index = int(var_val)
                    track_objs.wellIndex_int = int(var_val)
                    print("update successful; OT2 new well index: {}".format(otto.odacell_well_index))
                else:
                    print("command not found")
                track_objs.write_to_file()

            # "changeMass CellID mass" changes mass on astrol for CellID
            elif "changeMass" in command.split():
                rand_name = command.split(maxsplit=2)[1]
                mass = command.split(maxsplit=2)[2]
                returnMsg = send('C changeMass '+rand_name+' '+mass)
            
            elif "printTable" in command.split():
                tableName = command.split(maxsplit=2)[1]
                try:
                    print(conn.execute("SELECT * FROM "+tableName).fetch_df().to_string())
                except duckdb.CatalogException as e:
                    print(e)
            
            elif "update_stock" == command:
                update_stock(conn)
            
            elif "add_material" == command:
                add_new_material(conn)

    print("Worker is stopping.")

workerThread = threading.Thread(target=worker)
workerThread.start()

def live_status_updater():
    """Updates every x seconds status of astrol and trackable objects i.e. num of available channels, which cells are running, which are done, status of crimper, number of trays"""
    global cycler_status
    global track_objs
    temp_trackobjs = Trackables()
    while serverRunning:
        # Check and Update Available Astrol Channels
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(ADDR)
        message = "Q listCells".encode(FORMAT)
        msg_length = len(message)
        send_length = str(msg_length).encode(FORMAT)
        send_length += b' ' * (HEADER - len(send_length))
        client.send(send_length)
        client.send(message)
        # recieves list via pickle
        listofcells = pickle.loads(client.recv(2048))
        client.close()
        # update available capacity
        availableCapacity = 16 - len(listofcells)
        if (availableCapacity == 0 and track_objs.CyclingState.current_state_value == 1) | (availableCapacity != 0 and track_objs.CyclingState.current_state_value == 0):
            track_objs.CyclingState.cycle()
        # create new cycler_status table to overwrite
        nam = []
        chan = []
        stat = []
        for cell in listofcells:
            cellList = re.split(r"\(Astrol1.|\)", cell)
            nam.append(cellList[0][:-1])
            chan.append(cellList[1][1:].replace('.','-'))
            stat.append(cellList[2][1:])
        if chan:
            cycler_status = pl.DataFrame({'CyclerSlot': [str(a)+'-'+str(b) for a in range(2) for b in range(1,9)]})
            cycler_status = cycler_status.join(pl.DataFrame({'CyclerSlot': chan, 'Name': nam, 'Status': stat}), on='CyclerSlot', how='left')
        else:
            cycler_status = pl.DataFrame({'CyclerSlot': [str(a)+'-'+str(b) for a in range(2) for b in range(1,9)], 'Name': None, 'Status': None}, schema=[('CyclerSlot', pl.Utf8), ('Name', pl.Utf8), ('Status', pl.Utf8)])

        # Check and Update trackables
        if otto.small_tip_index != track_objs.small_pipette_int or otto.large_tip_index != track_objs.large_pipette_int:
            track_objs.small_pipette_int = otto.small_tip_index
            track_objs.large_pipette_int = otto.large_tip_index


        temp_trackobjs.load()
        if not track_objs.to_pl().select(pl.exclude(['crimper_state', 'CyclingState'])).frame_equal(temp_trackobjs.to_pl().select(pl.exclude(['crimper_state', 'CyclingState']))):
            track_objs.write_to_file()
        time.sleep(2.5)

# ---
# -----Home Dobots-----
# ---

dcrimp.home()
dgrip.home()

# ---
# -----Input Worker-----
# ---

def keyboard_input():
    """Setup thread function for recieving input commands without blocking worker - passes commands to worker thread"""
    global serverRunning
    # start the astrol cycler update thread
    liveupdateThread = threading.Thread(target=live_status_updater)
    liveupdateThread.setDaemon(True)
    liveupdateThread.start()

    while serverRunning:
        print("Input commands to add to queue; Press q to quit\n")
        keystrk = input()
        # thread doesn't continue until key is pressed
        print("You entered: " + keystrk)
        if keystrk == 'q':
            otto.RawInput("pipette_right.move_to(location=s_tiprack.wells()[7].top(z=120.0))")
            serverRunning = False
            conn.close()
            print("Server is stopping..")
            time.sleep(0.5)
            otto.ssh_channel.send("exit()\n".encode())
            otto.ssh_channel.send("exit\n".encode())
            otto.ssh.close()

            dcrimp.dashboard.DO(10,0)
            dcrimp.dashboard.DisableRobot()
            dgrip.dashboard.DisableRobot()
            dgrip.close()
            dcrimp.close()
            os._exit(0)
        else:
            Queue.append(keystrk)

keyboardThread = threading.Thread(target=keyboard_input)
keyboardThread.start()


def makeCell(working_mass=0.0):
    temp_finished = duckdb.execute("SELECT Name, CyclerSlot FROM cycler_status WHERE Status = 'Finished'").fetchall()
    if len(temp_finished):
        for (name_id, toremove_cycler_id) in temp_finished:
            returnMsg = send('C exportCelldata '+name_id)
            returnMsg = send('C stopCell '+name_id)
            conn.execute("UPDATE coinCells SET Status = 3 WHERE ID = ?;", [name_id])
            dgrip.remove_from_cycler('Cycling Station '+toremove_cycler_id)
        # if there is no available capacity (all channels in use), place command back into queue
    if track_objs.CyclingState.current_state_value == 0:
        return "add_queue"
    else:
        # takes the first available cell (status 0) in make cells tables; if none then just pass
        try:
            cell_id, elec_id = conn.execute("SELECT ID, Electrolyte_ID FROM coinCells WHERE Status == 0").fetchone()
        except TypeError:
            print("No more jobs available; please add to list")
            return
        well = conn.execute("SELECT Well FROM Electrolytes WHERE Electrolyte_ID = ? AND Active = TRUE", [elec_id]).fetchall()[0][0]
        if not well:
            additive_list = conn.execute("SELECT Material_ID, Additive, Additive_Conc FROM Additives WHERE Electrolyte_ID = ?", [elec_id]).fetchall()
            electrolyte_cache = conn.execute("SELECT Solvent_Material_ID, Solvent_Name, Salt_Material_ID, Salt_Name, Salt_Conc FROM Electrolytes WHERE Electrolyte_ID = ?;", [elec_id]).fetchone()
            elec_id, well = get_electrolyte(conn, additive_list, track_objs.wellIndex_int, 1000, *electrolyte_cache)
            if well == track_objs.wellIndex_int:
                base_electrolyte = conn.execute("SELECT wellPosition, Component1_Conc, Density_gmL, Volume_uL FROM stockSolutions WHERE Solvent_Material_ID = ? AND Component1_Material_ID = ?", [electrolyte_cache[0], electrolyte_cache[2]]).fetchone()
                solvent_stock = conn.execute("SELECT wellPosition, Density_gmL, Volume_uL FROM stockSolutions WHERE Solvent_Material_ID = ? AND Component1_Name IS NULL", [electrolyte_cache[0]]).fetchone()
                if (not base_electrolyte) or (not solvent_stock):
                    print("No base electrolyte and solvent well for dilution")
                    conn.execute("DELETE FROM Electrolytes WHERE Electrolyte_ID = ?", [elec_id])
                    return
                stock_densities = [base_electrolyte[2]]
                stock_conc = [base_electrolyte[1]]
                stock_vol = [base_electrolyte[3]]
                stock_wells = [base_electrolyte[0]]
                electrolyte_conc = [electrolyte_cache[-1]]
                molar_mass = [conn.execute("SELECT molarMass FROM Materials WHERE Material_ID = ?", [electrolyte_cache[2]]).fetchone()[0]]
                if additive_list:
                    electrolyte_conc += [i[-1] for i in additive_list]
                    molar_mass += [conn.execute("SELECT molarMass FROM Materials WHERE Material_ID = ?", [i[0]]).fetchone()[0] for i in additive_list]

                    for additive in additive_list:
                        add_stock = conn.execute("SELECT wellPosition, Component1_Conc, Density_gmL, Volume_uL FROM stockSolutions WHERE Solvent_Material_ID = ? AND Component1_Material_ID = ?", [electrolyte_cache[0], additive[0]]).fetchone()
                        if add_stock:
                            stock_densities.append(add_stock[2])
                            stock_conc.append(add_stock[1])
                            stock_vol.append(add_stock[3])
                            stock_wells.append(add_stock[0])
                        else:
                            print("Not all additives present in stock solutions.")
                            conn.execute("DELETE FROM Electrolytes WHERE Electrolyte_ID = ?", [elec_id])
                            return
                stock_densities.append(solvent_stock[1])
                stock_vol.append(solvent_stock[2])
                stock_wells.append(solvent_stock[0])
                if (not additive_list) and (stock_conc[0] == electrolyte_conc[0]):
                    if (stock_vol[0] < 1000):
                        print("Not enough volume in stock solution")
                        conn.execute("DELETE FROM Electrolytes WHERE Electrolyte_ID = ?", [elec_id])
                        return
                    else:
                        otto.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(otto.large_tip_index)+"])")
                        otto.RawInput("pipette_left.transfer(1000, stock_solutions.wells()["+str(stock_wells[0])+"], wellplate_odacell.wells()["+str(well)+"], new_tip='never')")
                        otto.RawInput("pipette_left.drop_tip()")
                        otto.get_output()
                        otto.large_tip_index += 1
                        otto.odacell_well_index += 1
                        track_objs.wellIndex_int = otto.odacell_well_index
                else:
                    transferVols = otto.get_mixing_volumes(stock_conc, molar_mass, stock_densities, electrolyte_conc)
                    if sum([1 for i in range(len(transferVols)) if transferVols[i]>stock_vol[i]]):
                        print("Not enough volumes in stock solutions")
                        conn.execute("DELETE FROM Electrolytes WHERE Electrolyte_ID = ?", [elec_id])
                        return
                    try:
                        otto.prepare_electrolyte(stock_wells, [i*1000 for i in transferVols], "wellplate_odacell.wells()["+str(well)+"]")
                        otto.get_output()
                    except ValueError:
                        print('Cannot make specified electrolyte with current stock solutions.')
                        conn.execute("DELETE FROM Electrolytes WHERE Electrolyte_ID = ?", [elec_id])
                        return
                    otto.odacell_well_index += 1
                    track_objs.wellIndex_int = otto.odacell_well_index
            conn.execute("UPDATE coinCells SET Electrolyte_ID = ? WHERE ID = ?;", [elec_id, cell_id])
        
        # if all goes well, generate Cell ID - random 5 digit number and tell astrol to prepare the cycler for it
        #rand_name = "{:05d}".format(random.randint(0,99999))
        returnMsg = send('C prepareCell '+cell_id)

        # update status in coinCells table
        conn.execute("UPDATE coinCells SET Status = 1 WHERE ID = ?;", [cell_id])
        # Make sure astrol has prepared cycler before continuing (sometimes astrol is bugged) - if wait for more than [sleep timer]*[prepare_cell_timer limit], cancel commad
        prepare_cell_timer = 0
        while len(duckdb.execute("SELECT * FROM cycler_status WHERE Name = ?;", [cell_id]).fetchall()) == 0:
            time.sleep(0.5)
            prepare_cell_timer += 1
            if prepare_cell_timer == 35:
                break
        if prepare_cell_timer == 35:
            print("Unable to create job on cycler; check cycler server")
            # Roll back coinCell Status
            conn.execute("UPDATE coinCells SET Status = 0 WHERE ID = ?;", [cell_id])
            return
        # get cycler holder for gripper to place assembled cell for cycling
        cycler_id = duckdb.execute("SELECT CyclerSlot FROM cycler_status WHERE Name = ?;", [cell_id]).fetchone()[0]
        # if mass is specified in makeCell command (i.e. 'makeCell 1.57mg'), change active material mass in astrol
        if working_mass != 0.0:
            returnMsg = send('C changeMass '+cell_id+' '+working_mass)
        # if working area is not loaded, load with next tray and update trackable values accordingly
        if not track_objs.working_area_loaded_int:
            dcrimp.load_working_area(track_objs.numTrays.current_state_value, track_objs.stackID.current_state_value)
            if track_objs.numTrays.current_state_value == 1:
                track_objs.stackID.send('cycle')
            track_objs.working_area_loaded_int = 1
            track_objs.numTrays.send('remove_one')
                    
        # start assemble cell process (blocking)
        dcrimp.collect_pos_components(track_objs.rowID.current_state_value)
        dgrip.collect_separator(track_objs.rowID.current_state_value)
        dcrimp.get_electrolyte()
        otto.odacell_dispense_electrolyte("wellplate_odacell.wells()["+str(well)+"]", track_objs.electrolyte_vol_int, cell_id)
        dispense_electrolyte(conn, elec_id, track_objs.electrolyte_vol_int)
        dcrimp.leave_otto()
        dgrip.collect_neg_components(track_objs.rowID.current_state_value)
        dcrimp.load_crimper()
        dcrimp.crimp()
        time.sleep(2)
        dcrimp.wait_crimper()
        dcrimp.unload_crimper()
        dgrip.holder_to_slide()
        dgrip.slide_to_cycler('Cycling Station '+cycler_id)
        # get astrol to start cycling cell
        returnMsg = send('C startCell '+cell_id)
        dcrimp.home()
        # if tray is empty (assembled cell from tray_row_id 3), take away empty tray, otherwise update tray_row_id 
        if track_objs.rowID.current_state_value == 4:
            dcrimp.emptytray_to_bin()
            track_objs.working_area_loaded_int = 0
        track_objs.rowID.send('change_row')
        #print(returnMsg)
        print('Cell ID '+cell_id+' successfully assembled and is cycling')

def add_job():
    try:
        repeats, electrode_ids, additive_list, electrolyte_cache = get_job(conn)
        elec_id, well = get_electrolyte(conn, additive_list, track_objs.wellIndex_int, 1000, *electrolyte_cache)
        if well == track_objs.wellIndex_int:
            base_electrolyte = conn.execute("SELECT wellPosition, Component1_Conc, Density_gmL, Volume_uL FROM stockSolutions WHERE Solvent_Material_ID = ? AND Component1_Material_ID = ?", [electrolyte_cache[0], electrolyte_cache[2]]).fetchone()
            solvent_stock = conn.execute("SELECT wellPosition, Density_gmL, Volume_uL FROM stockSolutions WHERE Solvent_Material_ID = ? AND Component1_Name IS NULL", [electrolyte_cache[0]]).fetchone()
            if (not base_electrolyte) or (not solvent_stock):
                print("No base electrolyte and solvent well for dilution")
                conn.execute("DELETE FROM Electrolytes WHERE Electrolyte_ID = ?", [elec_id])
                return
            stock_densities = [base_electrolyte[2]]
            stock_conc = [base_electrolyte[1]]
            stock_vol = [base_electrolyte[3]]
            stock_wells = [base_electrolyte[0]]
            electrolyte_conc = [electrolyte_cache[-1]]
            molar_mass = [conn.execute("SELECT molarMass FROM Materials WHERE Material_ID = ?", [electrolyte_cache[2]]).fetchone()[0]]
            if additive_list:
                electrolyte_conc += [i[-1] for i in additive_list]
                molar_mass += [conn.execute("SELECT molarMass FROM Materials WHERE Material_ID = ?", [i[0]]).fetchone()[0] for i in additive_list]
                
                for additive in additive_list:
                    add_stock = conn.execute("SELECT wellPosition, Component1_Conc, Density_gmL, Volume_uL FROM stockSolutions WHERE Solvent_Material_ID = ? AND Component1_Material_ID = ?", [electrolyte_cache[0], additive[0]]).fetchone()
                    if add_stock:
                        stock_densities.append(add_stock[2])
                        stock_conc.append(add_stock[1])
                        stock_vol.append(add_stock[3])
                        stock_wells.append(add_stock[0])
                    else:
                        print("Not all additives present in stock solutions.")
                        conn.execute("DELETE FROM Electrolytes WHERE Electrolyte_ID = ?", [elec_id])
                        return
            stock_densities.append(solvent_stock[1])
            stock_vol.append(solvent_stock[2])
            stock_wells.append(solvent_stock[0])
            if (not additive_list) and (stock_conc[0] == electrolyte_conc[0]):
                if (stock_vol[0] < 1000):
                    print("Not enough volume in stock solution")
                    conn.execute("DELETE FROM Electrolytes WHERE Electrolyte_ID = ?", [elec_id])
                    return
                else:
                    otto.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(otto.large_tip_index)+"])")
                    otto.RawInput("pipette_left.transfer(1000, stock_solutions.wells()["+str(stock_wells[0])+"], wellplate_odacell.wells()["+str(well)+"], new_tip='never')")
                    otto.RawInput("pipette_left.drop_tip()")
                    otto.get_output()
                    otto.large_tip_index += 1
                    otto.odacell_well_index += 1
                    track_objs.wellIndex_int = otto.odacell_well_index
                    conn.executemany("INSERT INTO coinCells (ID, Electrolyte_ID, Electrode1_ID, Electrode2_ID) VALUES (?, ?, ?, ?);", [["{:05d}".format(random.randint(0,99999)), elec_id, int(electrode_ids[0]), int(electrode_ids[1])] for i in range(repeats)])
                    return
            transferVols = otto.get_mixing_volumes(stock_conc, molar_mass, stock_densities, electrolyte_conc)
            if sum([1 for i in range(len(transferVols)) if transferVols[i]>stock_vol[i]]):
                print("Not enough volumes in stock solutions")
                conn.execute("DELETE FROM Electrolytes WHERE Electrolyte_ID = ?", [elec_id])
                return
            try:
                otto.prepare_electrolyte(stock_wells, [i*1000 for i in transferVols], "wellplate_odacell.wells()["+str(well)+"]")
                otto.get_output()
            except ValueError:
                print('Cannot make specified electrolyte with current stock solutions.')
                conn.execute("DELETE FROM Electrolytes WHERE Electrolyte_ID = ?", [elec_id])
                return
            otto.odacell_well_index += 1
            track_objs.wellIndex_int = otto.odacell_well_index
        conn.executemany("INSERT INTO coinCells (ID, Electrolyte_ID, Electrode1_ID, Electrode2_ID) VALUES (?, ?, ?, ?);", [["{:05d}".format(random.randint(0,99999)), elec_id, int(electrode_ids[0]), int(electrode_ids[1])] for i in range(repeats)])
    except TypeError:
        print('canceled, no jobs added')