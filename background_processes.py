
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
        availableCapacity = 16 - len(listofcells)
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
        
        # check for finished cells
        cycler_stat = cycler_status(listofcells)
        temp_finished = duckdb.execute("SELECT Name, CyclerSlot FROM cycler_stat WHERE Status = 'Finished'").fetchall()
        if len(temp_finished):
            for (name_id, toremove_cycler_id) in temp_finished:
                if name_id+' ' not in finished_str:
                    Queue.append('removeCell '+name_id+' '+toremove_cycler_id)
                    finished_str += name_id+' '
                if len(finished_str) > 50:
                    finished_str = finished_str[-6:]
        time.sleep(3)

def cycler_status(listofCells):
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
        