from concurrent.futures import thread
from glob import glob
from http import server
from multiprocessing.sharedctypes import Value

from robot_class_v2 import Dobbie_Cell, Dobbie_Crimp, OT2, Dobbie_Grip, arduino_ObjDetect
import time
import threading
import socket
import os, sys
import random
import pandas as pd
import numpy as np
import pickle
import sqlite3
from dataclasses import dataclass, field
import datetime

# ---
# -----Astrol Client Setup-----
# ---

HEADER = 64
PORT = 5051
FORMAT = 'utf-8'
SERVER = "130.238.197.123"
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
    return returnMsg

# ---
# -----ODACell Robot Connections-----
# ---

try:
    dcell = Dobbie_Cell('192.168.1.6')
    dcrimp = Dobbie_Crimp('192.168.2.6')
    dgrip = Dobbie_Grip('192.168.3.6')
except:
    sys.exit('Connection to Dobot failed')

otto = OT2('192.168.5.5')
arduino = arduino_ObjDetect("COM4")

# ---
# -----Set Trackable States-----
# ---

@dataclass
class Trackables:
    stack_id: int = field(default=0, metadata={'description': 'stack to pick up next tray from after tray in working area is empty.', 'limits': '[0,1]'})
    num_trays: int  = field(default=5, metadata={'description': 'number of trays in the current stack_id', 'limits': '[0,5]'})
    tray_row_id: int = field(default=0, metadata={'description': 'row of components to build coin cell from; always increasing from this number - right to left', 'limits': '[0,3]'})
    area_not_loaded: bool = field(default=True, metadata={'description': 'True = working area not loaded/ready with tray, False = tray already present in working area'})
    electrolyte_vol: int = field(default=45, metadata={'description': 'volume of electrolyte to use', 'limits': '[20,100]'})

track_objs = Trackables()

# ---
# -----Setup SQL Database Functions (INCOMPLETE IMPLEMENTATION)-----
# ---

def sql_update_nameid(conn, nameid):
    #replaces the first name that has 0
    cur = conn.cursor()
    command = """UPDATE [Electrolyte Compositions] SET [Cell Name]={} WHERE ID=(SELECT MIN(ID) FROM [Electrolyte Compositions] WHERE [Cell Name]='0')""".format(nameid)
    cur.execute(command)
    conn.commit()
    cur.close()

def sql_get_electrolyte_comp(conn, nameid):
    cur = conn.cursor()
    command = """SELECT * FROM [Electrolyte Compositions] WHERE "Cell Name" = '{}'""".format(nameid)
    table=cur.execute(command)
    electrolyte_comp_table=table.fetchone()
    electrolyte_comp_list = [i for i in electrolyte_comp_table[3:] if i is not None]
    electrolyte_comp_arrayed = [(electrolyte_comp_list[i],electrolyte_comp_list[i+1]) for i in range(0,len(electrolyte_comp_list),2)]
    return electrolyte_comp_arrayed

def get_electrolyte_comp(electrolyte_array, vol=1000):
    electrolyte_array.insert(0,vol)

# ---
# ----- Load Tables -----
# ---

stock_list = pd.read_excel(r'C:\Users\renrum\Desktop\CobotPlatform\stock_list.xlsx')
stock_list = [stock_list.iloc[i].tolist() for i in range(len(stock_list))]
makecells_table = pd.read_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx')
electrolyte_table = pd.read_excel(r'C:\Users\renrum\Desktop\CobotPlatform\electrolyte_list.xlsx')

def update_tables_from_file():
    """Updates current tables with information for their respective files in case files have been edited"""
    global stock_list, makecells_table, electrolyte_table
    stock_list = pd.read_excel(r'C:\Users\renrum\Desktop\CobotPlatform\stock_list.xlsx')
    stock_list = [stock_list.iloc[i].tolist() for i in range(len(stock_list))]
    makecells_table = pd.read_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx')
    electrolyte_table = pd.read_excel(r'C:\Users\renrum\Desktop\CobotPlatform\electrolyte_list.xlsx')

# ---
# -----Setup OT2 Electrolyte Tracking Functions-----
# ---

def addto_electrolyte_table(electrolyte_table, electrolyte_comp, well_id, initial_vol):
    """Adds new electrolyte mixture onto the electrolyte table"""
    # extract electrolyte composition
    new_elecid = electrolyte_table.ElecID.max() + 1
    electrolyte_comp_list = [item for sublist in electrolyte_comp for item in sublist]
    row_toadd = [new_elecid, datetime.date.today().strftime("%Y/%m/%d"), 1, well_id, initial_vol, initial_vol]
    row_toadd.extend(electrolyte_comp_list)
    #take care of blank columns (NAs)
    if len(row_toadd) != len(electrolyte_table.columns):
        while len(row_toadd) < len(electrolyte_table.columns):
            row_toadd.append(np.nan)
    electrolyte_table.loc[len(electrolyte_table)] = row_toadd
    # save to file
    electrolyte_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\electrolyte_list.xlsx', index=False)
    return new_elecid

def electrolyte_table_manager(makecells_table, electrolyte_table, stock_list, working_index, electrolyte_comp, dispense_vol):
    """Manages consistency between makecells table and electrolyte table - checks if the desired electrolyte in makecells table needs to be mixed or now"""
    # update odacell class well_index with well index of table
    otto.odacell_well_index = electrolyte_table.Well.max() + 1
    # if no active electrolyte available, don't bother looking through table, just make new mixture 
    if len(electrolyte_table[electrolyte_table.Active == 1]) == 0:
        new_elecid = addto_electrolyte_table(electrolyte_table, electrolyte_comp, otto.odacell_well_index, 1000)
        makecells_table.at[working_index, "ElecID"] = new_elecid
        makecells_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx', index=False)
    else:
        # for every active electrolyte mixture, check to see if it is the same as the desired makeCell electrolyte composition
        for i in range(len(electrolyte_table[electrolyte_table.Active == 1])):
            # record row_id of current active composition in the electrolyte table and convert the list
            row = electrolyte_table[electrolyte_table.Active == 1].iloc[i]
            existing_elec = [x for x in row.tolist()[6:] if not pd.isnull(x)]
            existing_elec = [(existing_elec[::2][i], existing_elec[1::2][i]) for i in range(int(len(existing_elec)/2))]
            # if the number of salts of the active electrolyte match the number of salts of the desired electrolyte, check if the concentration also matches
            if len(existing_elec) == len(electrolyte_comp):
                counter = 0
                for match in electrolyte_comp:
                    if match in existing_elec:
                        counter += 1
                if counter == len(existing_elec):
                    if (row.CurrentVolume - dispense_vol - 20) > 0:
                        # if everything matches and the current available volume is 20uL greater than the dispense volume, use it (change Elec ID in make cells table)
                        makecells_table.at[working_index, "ElecID"] = row.ElecID
                        makecells_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx', index=False)
                        return row.Well
                    else:
                        electrolyte_table.loc[electrolyte_table.loc[electrolyte_table.Active == 1].index[i], 'Active'] = 0
                        break
        # if none of the active electrolytes in the electrolyte table matches, make new electrolyte mixture and save to file
        new_elecid = addto_electrolyte_table(electrolyte_table, electrolyte_comp, otto.odacell_well_index, 1000)
        makecells_table.at[working_index, "ElecID"] = new_elecid
        makecells_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx', index=False)
    electrolyte_comp.insert(0,1000)
    return_wellid = otto.odacell_well_index
    # otto start to make new electrolyte
    try:
        otto.prepare_electrolyte(stock_list, electrolyte_comp, "wellplate_odacell.wells()["+str(otto.odacell_well_index)+"]")
    except ValueError:
        # if concentrations too low, a ValueError will occur - delete newly added entry of the electrolyte table (raise ValueError is connected to worker thread to deal with)
        print("Composition has too low concentrations for OT2")
        electrolyte_table.drop(electrolyte_table[electrolyte_table.ElecID == new_elecid].index[0])
        electrolyte_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\electrolyte_list.xlsx', index=False)
        raise ValueError
    return return_wellid

def change_elec_current_vol(electrolyte_location, dispense_vol):
    """Change the Current Volume column in electrolyte table given well ID"""
    well_id = electrolyte_location.split('[')[1][:-1]
    electrolyte_table.loc[electrolyte_table.loc[(electrolyte_table.Active == 1) & (electrolyte_table.Well == int(well_id))].index[0], 'CurrentVolume'] -= dispense_vol
    electrolyte_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\electrolyte_list.xlsx', index=False)

# ---
# -----Setup and Start Worker Queue-----
# ---

serverRunning = True
Queue = []
cycler_status = pd.DataFrame(columns=['Name','CyclerSlot','Status'])
availableCapacity = 0
dobots_positions = {'crimp': dcrimp.pos, 'cell': dcell.pos, 'grip': dgrip.pos}

def worker():
    while serverRunning:
        if len(Queue) > 0:
            command = Queue.pop(0)
            print("\nElement dequeued from queue: "+command)
            update_tables_from_file()
            # define command actions below (makeCell probably the most important)
            if "makeCell" in command.split():
                if len(command.split()) > 1:
                    mass = command.split(maxsplit=1)[1]
                    results = makeCell(mass)
                else:
                    results = makeCell()
                if results == "add_queue":
                    Queue.append(command)

            elif "makeSeries" in command.split():
                
                if len(command.split()) == 2:
                    stock_reservoir = command.split(maxsplit=1)[1]
                    otto.odacell_well_index = electrolyte_table.Well.max()
                    working_well = electrolyte_table.Well.max() + 1
                    if (working_well+4) < 97:
                        electrolyte_comp = [('liclo4', 2.0), ('h2o', 0.16)]
                        otto.RawInput("pipette_right.pick_up_tip(s_tiprack.wells()["+str(otto.small_tip_index)+"])")
                        otto.RawInput("pipette_right.transfer(160, stock_solutions.wells()[2], wellplate_odacell.wells()["+str(working_well)+"], new_tip='never', blow_out=True, blowout_location='destination well')")
                        new_elecid = addto_electrolyte_table(electrolyte_table, electrolyte_comp, working_well, 1000)
                        otto.RawInput("pipette_right.drop_tip()")
                        otto.small_tip_index += 1

                        otto.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(otto.large_tip_index)+"])")
                        otto.RawInput("pipette_left.transfer(840, stock_solutions.wells()["+stock_reservoir+"], wellplate_odacell.wells()["+str(working_well)+"], new_tip='never', mix_after=(20,700), blow_out=True, blowout_location='destination well')")
                        otto.RawInput("pipette_left.drop_tip()")
                        otto.large_tip_index += 1
                        
                        electrolyte_comp_list = [item for sublist in electrolyte_comp for item in sublist]
                        row_toadd = [0, np.nan, np.nan]
                        row_toadd.extend(electrolyte_comp_list)
                        #take care of blank columns (NAs)
                        if len(row_toadd) != len(makecells_table.columns):
                            while len(row_toadd) < len(makecells_table.columns):
                                row_toadd.append(np.nan)
                        for i in range(4):
                            makecells_table.loc[len(makecells_table)] = row_toadd
                        # save to file
                        makecells_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx', index=False)
                        for i in range(4):
                            makeCell()
                        working_well += 1

                        # Second Dilution
                        electrolyte_comp = [('liclo4', 2.0), ('h2o', 0.08)]
                        otto.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(otto.large_tip_index)+"])")
                        otto.RawInput("pipette_left.transfer(500, wellplate_odacell.wells()["+str(working_well-1)+"], wellplate_odacell.wells()["+str(working_well)+"], new_tip='never', blow_out=True, blowout_location='destination well')")
                        new_elecid = addto_electrolyte_table(electrolyte_table, electrolyte_comp, working_well, 1000)
                        change_elec_current_vol("wellplate_odacell.wells()["+str(working_well-1)+"]",500)
                        otto.RawInput("pipette_left.drop_tip()")
                        otto.large_tip_index += 1

                        otto.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(otto.large_tip_index)+"])")
                        otto.RawInput("pipette_left.transfer(500, stock_solutions.wells()["+stock_reservoir+"], wellplate_odacell.wells()["+str(working_well)+"], new_tip='never', mix_after=(20,700), blow_out=True, blowout_location='destination well')")
                        otto.RawInput("pipette_left.drop_tip()")
                        otto.large_tip_index += 1
                        
                        electrolyte_comp_list = [item for sublist in electrolyte_comp for item in sublist]
                        row_toadd = [0, np.nan, np.nan]
                        row_toadd.extend(electrolyte_comp_list)
                        #take care of blank columns (NAs)
                        if len(row_toadd) != len(makecells_table.columns):
                            while len(row_toadd) < len(makecells_table.columns):
                                row_toadd.append(np.nan)
                        for i in range(4):
                            makecells_table.loc[len(makecells_table)] = row_toadd
                        # save to file
                        makecells_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx', index=False)
                        for i in range(4):
                            makeCell()
                        working_well += 1

                        # Third Dilution
                        electrolyte_comp = [('liclo4', 2.0), ('h2o', 0.04)]
                        otto.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(otto.large_tip_index)+"])")
                        otto.RawInput("pipette_left.transfer(500, wellplate_odacell.wells()["+str(working_well-1)+"], wellplate_odacell.wells()["+str(working_well)+"], new_tip='never', blow_out=True, blowout_location='destination well')")
                        new_elecid = addto_electrolyte_table(electrolyte_table, electrolyte_comp, working_well, 500)
                        change_elec_current_vol("wellplate_odacell.wells()["+str(working_well-1)+"]",250)
                        otto.RawInput("pipette_left.drop_tip()")
                        otto.large_tip_index += 1

                        otto.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(otto.large_tip_index)+"])")
                        otto.RawInput("pipette_left.transfer(500, stock_solutions.wells()["+stock_reservoir+"], wellplate_odacell.wells()["+str(working_well)+"], new_tip='never', mix_after=(20,700), blow_out=True, blowout_location='destination well')")
                        otto.RawInput("pipette_left.drop_tip()")
                        otto.large_tip_index += 1
                        
                        electrolyte_comp_list = [item for sublist in electrolyte_comp for item in sublist]
                        row_toadd = [0, np.nan, np.nan]
                        row_toadd.extend(electrolyte_comp_list)
                        #take care of blank columns (NAs)
                        if len(row_toadd) != len(makecells_table.columns):
                            while len(row_toadd) < len(makecells_table.columns):
                                row_toadd.append(np.nan)
                        for i in range(4):
                            makecells_table.loc[len(makecells_table)] = row_toadd
                        # save to file
                        makecells_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx', index=False)
                        for i in range(4):
                            makeCell()
                        working_well += 1

                        # Fourth Dilution
                        electrolyte_comp = [('liclo4', 2.0), ('h2o', 0.02)]
                        otto.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(otto.large_tip_index)+"])")
                        otto.RawInput("pipette_left.transfer(500, wellplate_odacell.wells()["+str(working_well-1)+"], wellplate_odacell.wells()["+str(working_well)+"], new_tip='never', blow_out=True, blowout_location='destination well')")
                        new_elecid = addto_electrolyte_table(electrolyte_table, electrolyte_comp, working_well, 1000)
                        change_elec_current_vol("wellplate_odacell.wells()["+str(working_well-1)+"]",500)
                        otto.RawInput("pipette_left.drop_tip()")
                        otto.large_tip_index += 1

                        otto.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(otto.large_tip_index)+"])")
                        otto.RawInput("pipette_left.transfer(500, stock_solutions.wells()["+stock_reservoir+"], wellplate_odacell.wells()["+str(working_well)+"], new_tip='never', mix_after=(20,700), blow_out=True, blowout_location='destination well')")
                        otto.RawInput("pipette_left.drop_tip()")
                        otto.large_tip_index += 1
                        
                        electrolyte_comp_list = [item for sublist in electrolyte_comp for item in sublist]
                        row_toadd = [0, np.nan, np.nan]
                        row_toadd.extend(electrolyte_comp_list)
                        #take care of blank columns (NAs)
                        if len(row_toadd) != len(makecells_table.columns):
                            while len(row_toadd) < len(makecells_table.columns):
                                row_toadd.append(np.nan)
                        for i in range(4):
                            makecells_table.loc[len(makecells_table)] = row_toadd
                        # save to file
                        makecells_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx', index=False)
                        for i in range(4):
                            makeCell()

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
                returnMsg = send('Q listCells')
                print(returnMsg)

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
                    track_objs.num_trays = int(var_val)
                    print("update successful")
                elif var_to_update == "stack_id":
                    track_objs.stack_id = int(var_val)
                    print("update successful")
                elif var_to_update == "tray_row_id":
                    track_objs.tray_row_id = int(var_val)
                    print("update successful")
                elif var_to_update == "area_not_loaded":
                    if var_val.lower() == "t":
                        track_objs.area_not_loaded = True
                    elif var_val.lower() == "f":
                        track_objs.area_not_loaded = False
                    print("update successful")
                elif var_to_update == "small_pipette_id":
                    otto.small_tip_index = int(var_val)
                    print("update successful")
                elif var_to_update == "large_pipette_id":
                    otto.large_tip_index = int(var_val)
                    print("update successful")
                elif var_to_update == "elec_vol":
                    track_objs.electrolyte_vol = int(var_val)
                    print("update successful")
                else:
                    print("command not found")

            # "changeMass CellID mass" changes mass on astrol for CellID
            elif "changeMass" in command.split():
                rand_name = command.split(maxsplit=2)[1]
                mass = command.split(maxsplit=2)[2]
                returnMsg = send('C changeMass '+rand_name+' '+mass)
    print("Worker is stopping.")

workerThread = threading.Thread(target=worker)
workerThread.start()

def cycler_live_status():
    """Updates every x seconds status of astrol i.e. num of available channels, which cells are running, which are done"""
    global cycler_status
    global availableCapacity
    while serverRunning:
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
        # update available capacity
        availableCapacity = 16 - len(listofcells)
        # create new cycler_status table to overwrite
        cycler_status = pd.DataFrame(columns=['Name','CyclerSlot','Status'])
        for i in [str(a)+'-'+str(b) for a in range(2) for b in range(1,9)]:
            cycler_status = cycler_status.append({'Name': np.nan, 'CyclerSlot': i , 'Status': np.nan}, ignore_index=True)
        for cell in listofcells:
            cellList = cell.split()
            nam = cellList[0]
            chan = cellList[1].split('B')[1][:-1].replace('.','-')
            stat = cellList[2]
            cycler_status.loc[cycler_status['CyclerSlot'] == chan, ['Name', 'Status']] = [nam,stat]
        time.sleep(4)

# ---
# -----Home Dobots-----
# ---

dcell.home()
dcrimp.home()
dgrip.home()
dcrimp.pickup_cellholder()
dcrimp.load_components()

# ---
# -----Input Worker-----
# ---

def keyboard_input():
    """Setup thread function for recieving input commands without blocking worker - passes commands to worker thread"""
    global serverRunning
    # start the astrol cycler update thread
    liveupdateThread = threading.Thread(target=cycler_live_status)
    liveupdateThread.setDaemon(True)
    liveupdateThread.start()

    while serverRunning:
        print("Input commands to add to queue; Press q to quit\n")
        keystrk = input()
        # thread doesn't continue until key is pressed
        print("You entered: " + keystrk)
        if keystrk == 'q':
            otto.RawInput("pipette_right.move_to(location=s_tiprack.wells()[7].top(z=120.0))")
            dcrimp.return_cellholder()
            serverRunning = False
            print("Server is stopping..")
            
            otto.ssh_channel.send("exit()\n".encode())
            otto.ssh_channel.send("exit\n".encode())
            otto.ssh.close()

            dcrimp.__del__()
            dcell.__del__()
            dgrip.__del__()
            os._exit(0)
        else:
            Queue.append(keystrk)

keyboardThread = threading.Thread(target=keyboard_input)
keyboardThread.start()


def assemble_cell(tray_row, cycler_id, electrolyte_location, cell_id=""):
    """Assemble coin cell linearly (blocking) - mainly Dobot commands with otto only dispensing"""
    #dcrimp.load_components()
    component_list1 = ['P casing', 'cath', 'sep']
    for component in component_list1:
        dcell.pick_n_place(tray_row, component)
        time.sleep(0.2)
    time.sleep(1)
    dcrimp.get_electrolyte()
    otto.odacell_dispense_electrolyte(electrolyte_location, track_objs.electrolyte_vol, cell_id)
    change_elec_current_vol(electrolyte_location, track_objs.electrolyte_vol)
    dcrimp.load_components()
    component_list2 = ['ano', 'space', 'N casing']
    for component in component_list2:
        dcell.pick_n_place(tray_row, component)
        time.sleep(0.2)
    dcrimp.load_crimper()
    dcrimp.crimp()
    time.sleep(100)
    dcrimp.wait_crimper()
    dcrimp.to_slide()
    dcell.holder_to_intermediate()
    if arduino.Obj():
        dcell.intermediate_to_slide()
        #dcrimp.return_cellholder()
        dgrip.slide_to_cycler(cycler_id)
    else:
        input("Coin Cell Stuck in holder, please fix...")
    dcell.home()


def makeCell(working_mass=0.0):
    if len(cycler_status[cycler_status.Status.isin(['Finished'])]) > 0:
        for name_id in cycler_status[cycler_status.Status.isin(['Finished'])].Name:
            toremove_cycler_id = cycler_status['CyclerSlot'].loc[cycler_status['Name'] == name_id].values[0]
            returnMsg = send('C exportCelldata '+name_id)
            returnMsg = send('C stopCell '+name_id)
            makecells_table.at[makecells_table[makecells_table.ID == int(name_id)].index[0], "Status"] = 2
            dgrip.remove_from_cycler(toremove_cycler_id)
        makecells_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx', index=False)
                # if there is no available capacity (all channels in use), place command back into queue
    if availableCapacity == 0:
        return "add_queue"
    else:
        # takes the first available cell (status 0) in make cells tables; if none then just pass
        try:
            working_index = makecells_table[makecells_table.Status == 0].index[0]
        except IndexError:
            print("No more jobs available; please add to list")
            return
        # get desired cell's electrolyte composition and check with electrolyte table to make new mixture or use existing one
        row = makecells_table.loc[working_index].tolist()
        electrolyte_comp = [x for x in row[3:] if not pd.isnull(x)]
        electrolyte_comp = [(electrolyte_comp[::2][i], electrolyte_comp[1::2][i]) for i in range(int(len(electrolyte_comp)/2))]
        try:
            dispense_wellid = electrolyte_table_manager(makecells_table, electrolyte_table, stock_list, working_index, electrolyte_comp, track_objs.electrolyte_vol)
        except ValueError:
            # if electrolyte conentrations in mixture too low to mix, a ValueError will be raised and the error status will be put on the make cell table (3)
            makecells_table.at[working_index, "Status"] = 3
            makecells_table.at[working_index, "ElecID"] = 0
            makecells_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx', index=False)
            return                  
        # if all goes well, generate Cell ID - random 5 digit number and tell astrol to prepare the cycler for it
        rand_name = "{:05d}".format(random.randint(0,99999))
        returnMsg = send('C prepareCell '+rand_name)
        # update Cell ID and status in make Cells table
        makecells_table.at[working_index, "ID"] = rand_name
        makecells_table.at[working_index, "Status"] = 1
        makecells_table.to_excel(r'C:\Users\renrum\Desktop\CobotPlatform\make_cells.xlsx', index=False)
        # Make sure astrol has prepared cycler before continuing (sometimes astrol is bugged) - if wait for more than [sleep timer]*[prepare_cell_timer limit], cancel commad
        prepare_cell_timer = 0
        while len(cycler_status['CyclerSlot'].loc[cycler_status['Name'] == rand_name].values) == 0:
            time.sleep(0.5)
            prepare_cell_timer += 1
            if prepare_cell_timer == 35:
                break
        if prepare_cell_timer == 35:
            return
        # get cycler holder for gripper to place assembled cell for cycling
        cycler_id = cycler_status['CyclerSlot'].loc[cycler_status['Name'] == rand_name].values[0]
        # if mass is specified in makeCell command (i.e. 'makeCell 1.57mg'), change active material mass in astrol
        if working_mass != 0.0:
            returnMsg = send('C changeMass '+rand_name+' '+working_mass)
        # if working area is not loaded, load with next tray and update trackable values accordingly
        if track_objs.area_not_loaded:
            dcell.load_workingarea(track_objs.num_trays, track_objs.stack_id)
            if track_objs.num_trays == 0:
                track_objs.num_trays = 5
                track_objs.stack_id += 1
                track_objs.area_not_loaded = False
            else:
                track_objs.num_trays -= 1
                track_objs.area_not_loaded = False
                    
                    # start assemble cell process (blocking)
        assemble_cell(track_objs.tray_row_id + 1, cycler_id, "wellplate_odacell.wells()["+str(dispense_wellid)+"]", rand_name)
        # get astrol to start cycling cell
        returnMsg = send('C startCell '+rand_name)
        # if tray is empty (assembled cell from tray_row_id 3), take away empty tray, otherwise update tray_row_id 
        if track_objs.tray_row_id == 3:
            track_objs.tray_row_id = 0
            dcell.stack_to_bin()
            track_objs.area_not_loaded = True
        else:
            track_objs.tray_row_id += 1
        #print(returnMsg)
        print('Cell ID '+rand_name+' successfully assembled and is cycling')