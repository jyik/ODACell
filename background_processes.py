
from typing import Any
from server_connection import send
from database_functions import update_stock, add_new_material, print_table
from odacell_states import Trackables
import re
import polars as pl
import time
import duckdb

# Define default worker commands:
def cmd_not_found(rest_of_cmd):
    print('Command not found!')

def startCell(rest_of_cmd):
    returnMsg = send('C startCell '+rest_of_cmd[0])
    print(returnMsg)

def stopAllcycle(rest_of_cmd):
    returnMsg = send('C stopAllCells')
    print(returnMsg)

def prepareCell(rest_of_cmd):
    returnMsg = send('C prepareCell '+rest_of_cmd[0])
    print(returnMsg)

def stopCell(rest_of_cmd):
    returnMsg = send('C stopCell '+rest_of_cmd[0])
    print(returnMsg)

def changeMass(rest_of_cmd):
    returnMsg = send('C changeMass '+' '.join(rest_of_cmd))
    print(returnMsg)

def printTable(rest_of_cmd):
    print_table(rest_of_cmd[0])

def updateStock(rest_of_cmd):
    update_stock()

def add_newMaterial(rest_of_cmd):
    add_new_material()
def listCells(rest_of_cmd):
    returnMsg = send('Q listCells')
    print(returnMsg)

# Create worker commands dictionary
cmnds = {
    'startCell': startCell,
    'stopAllCells': stopAllcycle,
    'prepareCell': prepareCell,
    'stopCell': stopCell,
    'changeMass': changeMass,
    'printTable': printTable,
    'updateStock': updateStock,
    'newMaterial': add_newMaterial,
    'listCells': listCells,
}

# Define worker class
class worker:
    def __init__(self):
        self.cmnds = cmnds

    def __call__(self, Queue):
        while True:
            if len(Queue) > 0:
                command = Queue.pop(0)
                print("\nElement dequeued from queue: "+command)
                main_cmd = command.split()[0]
                sub_vars = command.split()[1:]
                run_cmnd = self.cmnds.get(main_cmd, cmd_not_found)
                try:
                    run_cmnd(sub_vars)
                except:
                    print('command failed...')
    def add_cmnd(self, append_dic):
        self.cmnds.update(append_dic) # WARNING, if key already exists, it will be replaced


# Define track_objs and if-cell-finished-cycling checker
def live_status_updater(track_objs, otto, Queue):
    """Updates every x seconds status of astrol and trackable objects i.e. num of available channels, which cells are running, which are done, status of crimper, number of trays"""
    finished_str = ''
    while True:
        temp_track_objs = Trackables()
        temp_track_objs.load()
        # Check and Update trackables:
        # available channels
        listofcells = send('Q listCells')
        try:
            neware_chls = [i for i in listofcells if type(i) == tuple]
            neware_chls = cycler_status(neware_chls, 'neware')
            chl_tofreeup = neware_chls.filter((pl.col('State') == 'finish') & (pl.col('Occupied') == True)).head(1)['Neware Channel'][0]
            #Queue.append('removeCell '+chl)
            #neware_chls = neware_chls.with_columns(pl.when(pl.col("Neware Channel") == chl).then(False).otherwise(pl.col("Occupied")).alias("Occupied"))
        except pl.ComputeError:
            pass

        availableCapacity_neware = len(neware_chls.filter((pl.col('State') == 'finish') & (pl.col('Occupied') == False)))
        ## Astrol Commands
        astrol_chls = [i for i in listofcells if type(i) == str]
        availableCapacity_astrol = 0
        # availableCapacity_astrol = 16 - len(astrol_chls)
        availableCapacity = availableCapacity_astrol + availableCapacity_neware

        if (availableCapacity == 0 and track_objs.CyclingState.current_state_value == 1) | (availableCapacity != 0 and track_objs.CyclingState.current_state_value == 0):
            track_objs.CyclingState.cycle()
        # pipette tips
        if otto.small_tip_index != track_objs.small_pipette_int or otto.large_tip_index != track_objs.large_pipette_int:
            track_objs.small_pipette_int = otto.small_tip_index
            track_objs.large_pipette_int = otto.large_tip_index
        # Rewrite file if current values are not up to date
        if not track_objs.to_pl().select(pl.exclude(['crimper_state', 'CyclingState'])).frame_equal(temp_track_objs.to_pl().select(pl.exclude(['crimper_state', 'CyclingState']))):
            track_objs.write_to_file()
        
        # Check and Update Available Astrol Channels
        
        # check for finished astrol cells
        #cycler_stat = cycler_status(astrol_chls, 'astrol')
        #temp_finished = duckdb.execute("SELECT Name, CyclerSlot FROM cycler_stat WHERE Status = 'Finished'").fetchall()
        #if len(temp_finished):
        #    for (name_id, toremove_cycler_id) in temp_finished:
            # need finished_str so that the function does not continuously add the removeCell command while the robot is removing the cell.
        #        if name_id+' ' not in finished_str:
        #            Queue.append('removeCell '+name_id+' '+toremove_cycler_id)
        #            finished_str += name_id+' '
        #        if len(finished_str) > 50:
        #            finished_str = finished_str[-6:]
        time.sleep(3)

def cycler_status(listofCells, cycler='astrol'):
    if cycler.lower() == 'astrol':
        nam = []
        chan = []
        stat = []
        for cell in listofCells:
            cellList = re.split(r"\(Astrol1.|\)", cell)
            nam.append(cellList[0][:-1])
            chan.append(cellList[1][1:].replace('.','-'))
            stat.append(cellList[2][1:])
        if chan:
            cycler_status = pl.DataFrame({'CyclerSlot': [str(a)+'-'+str(b) for a in range(2) for b in range(1,9)]})
            cycler_status = cycler_status.join(pl.DataFrame({'CyclerSlot': chan, 'Name': nam, 'Status': stat}), on='CyclerSlot', how='left')
        else:
            cycler_status = pl.DataFrame({'CyclerSlot': [str(a)+'-'+str(b) for a in range(2) for b in range(1,9)], 'Name': None, 'Status': None}, schema=[('CyclerSlot', pl.Utf8), ('Name', pl.Utf8), ('Status', pl.Utf8)])
        return cycler_status
    elif cycler.lower() == 'neware':
        pl_df = pl.DataFrame(listofCells, schema=['Neware Channel', 'State'], orient='row')
        try:
            previous_state_df = pl.read_parquet('Neware_cycler_state.parquet')
        except FileNotFoundError:
            #TO DO: create file if not found
            pass
        pl_df = pl_df.join(previous_state_df.select(['Neware Channel', 'Occupied']), on='Neware Channel', how='left')
        if not pl_df.frame_equal(previous_state_df):
            pl_df.write_parquet('Neware_cycler_state.parquet')
        return pl_df


def myround(x, base=20.0):
    return round(base * round(x/base), 1)

def trial_saver(trial, data_points, file_name='default.csv'):
    trial_dict = {'trial':trial}
    trial_dict.update({i: myround(data_points[i], 0.1) for i in data_points})
    try:
        pl.read_csv(file_name)
        with open(file_name, mode="ab") as f:
            pl.from_dict(trial_dict).write_csv(f, has_header=False)
    except FileNotFoundError:
        with open(file_name, mode="ab") as f:
            pl.from_dict(trial_dict).write_csv(f)