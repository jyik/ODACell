from database_functions import get_electrolyte, dispense_electrolyte, get_job, change_coinCell_status, get_mixing_volumes, add_coinCell, get_trial_id, aq_solv_percent, get_status, get_composition
import polars as pl
import pickle
import random
from dobbie_crimp import D_CRIMP
from dobbie_grip import D_GRIP
from OT2_class import OT2
from background_processes import worker, live_status_updater, cycler_status, trial_saver, myround
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
            otto.RawInput("pipette_right.move_to(location=s_tiprack.wells()[64].top(z=120.0))")
            print('shutting down...')
            time.sleep(1)
            otto.ssh_channel.send("exit()\n".encode())
            time.sleep(0.5)
            otto.ssh_channel.send("exit\n".encode())
            otto.get_output()
            otto.ssh.close()

            dcrimp.dashboard.DO(10,0)
            #dcrimp.dashboard.DisableRobot()
            #dgrip.dashboard.DisableRobot()
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
    try:
        toremove_cycler_id = rest_of_cmds[0]
        name_id = send('Q cellID '+toremove_cycler_id)
        opt_client, opt_trial = get_trial_id(name_id)
        returnMsg = send('C exportCelldata '+toremove_cycler_id)
        #returnMsg = send('C stopCell '+name_id)
        #returnMsg = send('C registerResults '+name_id+' '+str(opt_trial))
        change_coinCell_status(3, name_id)
        dgrip.remove_from_cycler('Neware C'+toremove_cycler_id)
        newaredf = pl.read_parquet('Neware_cycler_state.parquet').with_columns(
            pl.when(pl.col("Neware Channel") == toremove_cycler_id)
            .then(False)
            .otherwise(pl.col("Occupied"))
            .alias("Occupied"))
        newaredf.write_parquet('Neware_cycler_state.parquet')
    except:
        print('Could not remove Cell. Double check the Neware_cycler_state.parquet and if files are exported / Trial has been completed')
        raise Exception

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
        except KeyError:
            pass
        if not type(well) == int:
            print("No well associated with electrolyte, please check.")
            return
        #returnMsg = send('C prepareCell '+cell_id)

        # Make sure astrol has prepared cycler before continuing (sometimes astrol is bugged) - if wait for more than [sleep timer]*[prepare_cell_timer limit], cancel commad
        prepare_cell_timer = 0
        while True:
            listofcells = send('Q listCells')
            neware_chls = [i for i in listofcells if type(i) == tuple]
            neware_chls = cycler_status(neware_chls, 'neware')
            astrol_chls = [i for i in listofcells if type(i) == str]
            cycler_stat = cycler_status(astrol_chls, 'astrol')
            try:
                chl = neware_chls.filter((pl.col('State') == 'finish') & (pl.col('Occupied') == False)).head(1)['Neware Channel'][0]
                cycle_pos = 'Neware C'+chl
                break
            except pl.ComputeError:
                # Get Cycler Holder ID for Gripper to place cell in correct cycling slot
                #chl = duckdb.execute("SELECT CyclerSlot FROM cycler_stat WHERE Name = ?;", [cell_id]).fetchone()[0]
                #astrol prepareCell command deprecated 
                #break
                print("Unable to create job on cycler; check cycler server")
                return
            except TypeError:
                prepare_cell_timer += 1
                time.sleep(2.5)
            if prepare_cell_timer == 5:
                print("Unable to create job on cycler; check cycler server")
                return
        
        # if mass is specified in makeCell command (i.e. 'makeCell 1.57mg'), change active material mass in astrol
        # DEPRECATED
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
        dcrimp.collect_pos_components(track_objs.rowID.current_state_value, filename=cell_id)
        dgrip.collect_separator(track_objs.rowID.current_state_value, filename=cell_id)
        dcrimp.get_electrolyte()
        otto.odacell_dispense_electrolyte("wellplate_odacell.wells()["+str(well)+"]", track_objs.electrolyte_vol_int, cell_id)
        dispense_electrolyte(elec_id, track_objs.electrolyte_vol_int)
        dcrimp.leave_otto()
        dgrip.collect_neg_components(track_objs.rowID.current_state_value, filename=cell_id)
        dcrimp.load_crimper()
        dcrimp.crimp()
        time.sleep(2)
        dcrimp.wait_crimper()
        dcrimp.unload_crimper()
        dgrip.holder_to_slide()
        dgrip.slide_to_cycler(cycle_pos)
        # start cycling cell
        returnMsg = send('C startCell '+cell_id+' '+chl)
        dcrimp.home()
        # if tray is empty (assembled cell from tray_row_id 3), take away empty tray, otherwise update tray_row_id 
        if track_objs.rowID.current_state_value == 4:
            dcrimp.emptytray_to_bin()
            track_objs.working_area_loaded_int = 0
        track_objs.rowID.send('change_row')
        # update status in coinCells table
        change_coinCell_status(1, cell_id)
        # update cycler holder status file
        time.sleep(0.45)
        pl.scan_parquet('Neware_cycler_state.parquet').with_columns(pl.when(pl.col("Neware Channel") == chl).then(True).otherwise(pl.col("Occupied")).alias("Occupied")).collect().write_parquet('Neware_cycler_state.parquet')
        print('Cell ID '+cell_id+' successfully assembled and is cycling')

def prepare_electrolyte(rest_of_cmds):
    global elec_mixing_queue
    try:
        for name_id in elec_mixing_queue.keys():
            if get_status(name_id) == 0:
                otto.prepare_electrolyte(elec_mixing_queue[name_id][0], "wellplate_odacell.wells()["+str(elec_mixing_queue[name_id][1])+"]")
                print('Preparing/Mixing electrolyte for '+name_id+' in well '+str(elec_mixing_queue[name_id][1])+'.')
                del elec_mixing_queue[name_id]
                with open('elec_mixing_volumes.pkl', 'wb') as f:
                    pickle.dump(elec_mixing_queue, f)
                break
    except TypeError:
        print("No more jobs available; please add to list")
        return
    except ValueError:
        print('Cannot make specified electrolyte with current stock solutions.')
        change_coinCell_status(404, name_id)
        return
    except KeyError:
        pass

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
        electrode_ids = [2, 3]
        for trial in trials:
            components, trial_num = trial
            # components will be a dictionary of {'optimization_parameter_name': ConcValue}
            wells_list, desiredConc_list = zip(*[(key[1], components[key]) for key in components])
            wellVol_list = get_mixing_volumes(wells_list, desiredConc_list)
            query_comp_list = get_composition(wells_list, desiredConc_list)
            #wellVol_list = [(key, myround(value, 0.1)) for key, value in wellVol_list]
            print(wellVol_list)
            trial_saver_dict = dict(zip(components.keys(), [x[1] for x in wellVol_list][:-1]))
            trial_saver_dict['solvent'] = wellVol_list[-1][1]
            trial_saver(trial_num, trial_saver_dict, optimizer+'.csv')
            elec_id, electrolyte_well = get_electrolyte(track_objs.wellIndex_int, query_comp_list, sum(value for _, value in wellVol_list))
            name_id = "{:05d}".format(random.randint(0,99999))
            if electrolyte_well == track_objs.wellIndex_int:
                elec_mixing_queue[name_id] = [wellVol_list, electrolyte_well]
                with open('elec_mixing_volumes.pkl', 'wb') as f:
                    pickle.dump(elec_mixing_queue, f)
            add_coinCell(name_id, elec_id, 1, electrode_ids, trial_num, optimizer)
            track_objs.wellIndex_int += 1
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
worker1.add_cmnd({'removeCell': removeCell, 'assembleCell': assembleCell, 'addjob': add_job, 'update': update, 'prepareE': prepare_electrolyte})

# Home Robots
dcrimp.home()
dgrip.home()
dcrimp.offset_camera_center()
dgrip.offset_camera_center()

#dcrimp.offset_camera_center('Crimp')
#dgrip.offset_camera_center('Grip')

# Start software
keyboardThread = threading.Thread(target=keyboard_input)
keyboardThread.start()
keyboardThread.join()