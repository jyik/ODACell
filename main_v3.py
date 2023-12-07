from database_functions import get_electrolyte, dispense_electrolyte, get_job, change_coinCell_status, volConc_to_mol, add_coinCell, get_trial_id, water_mol_ratio

import pickle
import random
import duckdb
from dobbie_crimp import D_CRIMP
from dobbie_grip import D_GRIP
from OT2_class import OT2
from background_processes import worker, live_status_updater, cycler_status
from server_connection import send
from odacell_states import Trackables
import time
import threading
import sys

# ---
# ----- Establish Robot and Server Connections-----
# ---
try:
    send('Q listCells')
except: # Don't know/cannot catch socket timeout exception...
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

# ---
# -----Setup Worker and Queue-----
# ---

Queue = []
worker1 = worker()
try:
    with open('elec_mixing_volumes.pkl', 'rb') as f:
        elec_mixing_queue = pickle.load(f)
except FileNotFoundError:
    elec_mixing_queue = {}
#dobots_positions = {'crimp': dcrimp.pos, 'grip': dgrip.pos}

# ---
# -----Setup commandline user interface-----
# ---

def keyboard_input():
    """Setup thread function for recieving input commands without blocking worker - passes commands to worker thread"""
    workerThread = threading.Thread(target=worker1, args=(Queue,))
    workerThread.setDaemon(True)
    workerThread.start()
    liveupdateThread = threading.Thread(target=live_status_updater, args=(track_objs, otto, Queue,))
    liveupdateThread.setDaemon(True)
    liveupdateThread.start()

    while True:
        print("Input commands to add to queue; Press q to quit\n")
        keystrk = input()
        # thread doesn't continue until key is pressed
        print("You entered: " + keystrk)
        if keystrk == 'q':
            otto.RawInput("pipette_right.move_to(location=s_tiprack.wells()[7].top(z=120.0))")
            print('shutting down...')
            time.sleep(1)
            otto.ssh_channel.send("exit()\n".encode())
            time.sleep(0.5)
            otto.ssh_channel.send("exit\n".encode())
            otto.ssh.close()

            dcrimp.dashboard.DO(10,0)
            dcrimp.dashboard.DisableRobot()
            dgrip.dashboard.DisableRobot()
            dgrip.close()
            dcrimp.close()
            break
        else:
            if keystrk:
                Queue.append(keystrk)

# ---
# -----Main (custom) worker commands-----
# ---

def removeCell(rest_of_cmds):
    name_id, toremove_cycler_id = rest_of_cmds
    opt_client, opt_trial = get_trial_id(name_id)
    returnMsg = send('C exportCelldata '+name_id)
    returnMsg = send('C stopCell '+name_id)
    returnMsg = send('C registerResults '+name_id+' '+str(opt_trial)+' '+str(water_mol_ratio(name_id)))
    change_coinCell_status(3, name_id)
    dgrip.remove_from_cycler('Cycling Station '+toremove_cycler_id)


def assembleCell(rest_of_cmds):
    global elec_mixing_queue
    # if there is no available capacity (all channels in use), place command back into queue
    if track_objs.CyclingState.current_state_value == 0:
        Queue.append('assembleCell')
        return
    else:
        # takes the first available cell (status 0) in make cells tables; if none then just pass
        try:
            cell_id, elec_id, well = get_job()
            otto.prepare_electrolyte(elec_mixing_queue[cell_id][0], "wellplate_odacell.wells()["+str(well)+"]")
            del elec_mixing_queue[cell_id]
            with open('elec_mixing_volumes.pkl', 'wb') as f:
                pickle.dump(elec_mixing_queue, f)
        except TypeError:
            print("No more jobs available; please add to list")
            return
        except ValueError:
            print('Cannot make specified electrolyte with current stock solutions.')
            change_coinCell_status(404, cell_id)
            return
        if not well:
            print("No well associated with electrolyte, please check.")
            return
        returnMsg = send('C prepareCell '+cell_id)

        # Make sure astrol has prepared cycler before continuing (sometimes astrol is bugged) - if wait for more than [sleep timer]*[prepare_cell_timer limit], cancel commad
        prepare_cell_timer = 0
        while True:
            time.sleep(2.5)
            listofcells = send('Q listCells')
            cycler_stat = cycler_status(listofcells)
            try:
                # Get Cycler Holder ID for Gripper to place cell in correct cycling slot
                cycler_id = duckdb.execute("SELECT CyclerSlot FROM cycler_stat WHERE Name = ?;", [cell_id]).fetchone()[0]
                break
            except TypeError:
                prepare_cell_timer += 1
            if prepare_cell_timer == 5:
                print("Unable to create job on cycler; check cycler server")
                return
        
        # if mass is specified in makeCell command (i.e. 'makeCell 1.57mg'), change active material mass in astrol
        if rest_of_cmds:
            working_mass = rest_of_cmds[0]
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
        dispense_electrolyte(elec_id, track_objs.electrolyte_vol_int)
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
        # update status in coinCells table
        change_coinCell_status(1, cell_id)
        print('Cell ID '+cell_id+' successfully assembled and is cycling')

def add_job(rest_of_cmds):
    global elec_mixing_queue
    optimizer = rest_of_cmds[0]
    if rest_of_cmds[1:]:
        num_trials = rest_of_cmds[1]
    else:
        num_trials = '1'
    try:
        trials = send('Q opt_get_designs '+optimizer+' '+num_trials)
        #default electrode_id for now
        electrode_ids = [1, 2]
        for trial in trials:
            components, trial_num = trial
            wellVol_list = [(key[1],components[key]*20) for key in components]
            query_comp_list = volConc_to_mol(wellVol_list)
            elec_id, well = get_electrolyte(track_objs.wellIndex_int, query_comp_list, round(sum(components.values())*20))
            name_id = "{:05d}".format(random.randint(0,99999))
            if well == track_objs.wellIndex_int:
                elec_mixing_queue[name_id] = [wellVol_list, well]
                with open('elec_mixing_volumes.pkl', 'wb') as f:
                    pickle.dump(elec_mixing_queue, f)
            add_coinCell(name_id, elec_id, electrode_ids, trial_num, optimizer)
    except TypeError:
        print('canceled, no jobs added')

def update(rest_of_cmd):
    var_to_update, var_val = rest_of_cmd
    def num_trays():
        track_objs.numTrays.set_state(int(var_val))
        print("update successful; current number of trays in stack: {}".format(track_objs.numTrays.current_state_value))
    def stack_id():
        track_objs.stackID.send('to_stack'+var_val)
        print("update successful")
    def tray_row_id():
        track_objs.rowID.set_row(int(var_val))
        print("update successful; current tray row ID: {}".format(track_objs.rowID.current_state_value))
    def area_loaded():
        if var_val.lower() == "t":
            track_objs.working_area_loaded_int = 1
        elif var_val.lower() == "f":
            track_objs.working_area_loaded_int = 0
        print("update successful; working area is loaded: {}".format(track_objs.working_area_loaded_int))
    def small_pipette_id():
        otto.small_tip_index = int(var_val)
        print("update successful; small_tip_index = {}".format(otto.small_tip_index))
    def large_pipette_id():
        otto.large_tip_index = int(var_val)
        print("update successful; large_tip_index = {}".format(otto.large_tip_index))
    def elec_vol():
        track_objs.electrolyte_vol_int = int(var_val)
        print("update successful; OT2 dispensing volume: {} uL".format(track_objs.electrolyte_vol_int))
    def well_id():
        track_objs.wellIndex_int = int(var_val)
        print("update successful; OT2 new well index: {}".format(track_objs.wellIndex_int))
    def update_cmd_not_found():
        print('Command not found!')
    updatable = {
        'num_trays': num_trays,
        'stack_id': stack_id,
        'tray_row_id': tray_row_id,
        'area_loaded': area_loaded,
        'small_pipette_id': small_pipette_id,
        'large_pipette_id': large_pipette_id,
        'elec_vol': elec_vol,
        'well_id': well_id
    }
    to_update = updatable.get(var_to_update, update_cmd_not_found)
    to_update()
    track_objs.write_to_file()


#Add functions to worker
worker1.add_cmnd({'removeCell': removeCell, 'assembleCell': assembleCell, 'addjob': add_job, 'update': update})

# Home Robots
dcrimp.home()
dgrip.home()

# Start software
keyboardThread = threading.Thread(target=keyboard_input)
keyboardThread.start()
keyboardThread.join()