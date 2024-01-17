import socket 
import threading
from typing import List

from pywinauto import WindowNotFoundError, WindowAmbiguousError
from pywinauto.application import Application
from pywinauto.findwindows import find_elements, find_window
from pywinauto.keyboard import send_keys
import time
import os
import pandas as pd
from datetime import datetime
import shutil
import shortuuid
import random
import pickle
from data_analyzer import get_CE, get_capacity

import sys
sys.path.append(r"C:\Users\renrum\Desktop\code\MyBOmain")
sys.path.append(r"C:\Users\renrum\Desktop\code\MyBOmain\mybo")
from mybo.interface import register_results, get_designs, cancel_trials
AX_PATH = r"C:\Users\renrum\Desktop\code\MyBOmain\results\coSolv\coSolvents_20240110\DWIT\seed11"

opt_output_dic = {'y0': 'coulombic_eff', 'y1': 'discharge_capacity', 'y2': 'aq_solvent_mol_percent'}


class batteryCycler:

    def __init__(self):
        # Connect to main Astrol App and primary window
        self.astrolApp = Application(backend='win32').connect(title="Astrol Battery Cycler")
        self.astrolW=self.astrolApp.window(title="Astrol Battery Cycler")
        # Number of available channels in total
        self.nrChannels = 16
    
    def prepareCell(self, file_template, name, comments):
        """
        Creates new measurement in Astrol and attaches the right protocol file to the measurement
        """
        new_file = self.prepareFile(file_template, name, comments)
        # Prepare measurement
        self.astrolW.set_focus()
        self.astrolW.wait('Ready')
        self.astrolW.send_keystrokes('^N')
        print('Preparing to start: '+name)
        Preparing=self.astrolApp.window(title="Preparing new measurement")
        Preparing.wait('Ready')
        Preparing.Select2.click_input()
        open_dlg=self.astrolApp.window(title='Open')
        open_dlg.wait('ready')
        open_dlg.Edit1.type_keys(new_file)
        open_dlg.Open.click_input()
        Preparing.Ok.click_input()
        print('Starting cell: '+name)
        starting=self.astrolApp.window(title=name)
        starting.close()
        print('startcell_end')
        
    def prepareFile(self, template_file, name, remarks):
        """
        Creates new .mpr protocol file based on template_file
        """
        # Create data folder if needed
        print('Create new folder if needed')
        data_folder='C:'+os.sep+"DATA"+os.sep
        date=datetime.today().strftime('%Y-%m-%d')
        if not os.path.exists(data_folder+date):
            os.makedirs(data_folder+date)
        # Creating new file
        print('Creating new file for: '+name)
        uniqeid=str(shortuuid.uuid())
        new_file=data_folder+date+os.sep+date+"_"+name+"_"+uniqeid+".mpr"
        shutil.copy(data_folder+template_file,new_file)
        shutil.copy(data_folder+'empty.txt', new_file.replace('.mpr', '.txt', 1))
        # Open new file for edit
        print('Opeing new file for edit: '+name)
        try:
            self.astrolApp.window(handle=find_window(title_re="Battery cycler - Measurement program and Data editor")).close()
        except WindowAmbiguousError:
            while True:
                try:
                    self.astrolApp.window(title="Battery cycler - Measurement program and Data editor").type_keys('%{F4}')
                except WindowNotFoundError:
                    break
        except WindowNotFoundError:
            pass
        astrolOpenApp = Application(backend='win32').start(r"C:\Program Files\CCCC\cccctool.exe")
        astrolOpenW = astrolOpenApp.window(title='Battery cycler - Measurement program and Data editor')
        astrolOpenW.wait('ready')
        astrolOpenW.Open.click_input()
        Select = astrolOpenApp.window(title="Select measurement program or measurement data file")
        Select.wait('ready')
        Select.Edit1.type_keys(new_file)
        Select.Open.click_input()
        # Edit new file
        print('Editing file: '+name)
        editAstrol = astrolOpenApp.window(title=new_file)
        editAstrol.wait('ready')
        editAstrol.Edit5.type_keys(name)
        editAstrol.Edit2.type_keys('0.00884 g')
        editAstrol.Edit4.type_keys(remarks)
        editAstrol.Edit2.type_keys('8.84 mg')
        editAstrol.send_keystrokes('{TAB}')
        # Save and close file
        print('Save and close file: '+name)
        #time.sleep(3)
        astrolOpenW.Save.click_input()
        #time.sleep(3)
        astrolOpenW.Button4.click_input()
        astrolOpenApp.kill()
        return new_file
    
    def selectCell(self, name):
        """
        Selects/highlights measurement with the corresponding name
        """
        cell_items = self.astrolW.treeview1.item_count()
        for i in range(cell_items-1):
            item = str(self.astrolW.treeview1.get_item([0, i]).text())
            if item.split()[0] == name:
                self.astrolW.treeview1.get_item([u'Odacell', item]).select()
                break

    def stopCellName(self, name):
        """
        Stops and removes measurement with name
        """
        self.selectCell(name)
        if self.getCellStatus(name) == 'Busy':
            self.astrolW.menu_select('Measurements->Show measurement and control window')
            cellw=self.astrolApp.window(title=name)
            cellw.wait('ready')
            cellw.Pause.click_input()
            cellw.Stop.click_input()
            confirm=self.astrolApp.window(title='Confirm')
            confirm.Ok.click_input()
        self.astrolW.menu_select('Measurements->Remove measurement')
        print('Removing: '+name)
    
    def startCellName(self, name):
        """
        Starts measurement of Cell with name
        """
        self.selectCell(name)
        self.astrolW.menu_select('Measurements->Show measurement and control window')
        cellw=self.astrolApp.window(title=name)
        print('Starting: '+name)
        cellw.wait('ready')
        cellw.Start.click_input()
        cellw.close()
    
    def getCellStatus(self, name):
        """
        Gets status of cell - cycling (Busy), paused, or finished (check mark)
        """
        cell_items = self.astrolW.treeview1.item_count()
        for i in range(cell_items-1):
            if name == str(self.astrolW.treeview1.get_item([0, i]).text()).split()[0]:
                state_nr = int(self.astrolW.treeview1.get_item([0, i]).state())
                if state_nr < 25000:
                    return 'Busy'
                elif state_nr > 39000:
                    return'Finished'
                else:
                    return 'Paused'

    def listCells(self):
        """
        Returns list of measurements
        """
        cellList = []
        cell_items = self.astrolW.treeview1.item_count()
        for i in range(cell_items-1):
            cellList.append(str(bcycler.astrolW.treeview1.get_item([0, i]).text())+' '+self.getCellStatus(str(bcycler.astrolW.treeview1.get_item([0, i]).text()).split()[0]))
        return cellList
    
    def stopAllCells(self):
        """
        StopCell function applied to every measurement
        """
        cell_items = self.astrolW.treeview1.item_count()-1
        print('Stopping '+str(cell_items)+' cells')
        for i in range(cell_items):
            j=cell_items-i-1
            self.stopCellName(str(bcycler.astrolW.treeview1.get_item([0, j]).text()).split()[0])
    
    def exportCelldata(self, name):
        """
        Exports data with default/current settings into the same folder as protocol
        """
        self.selectCell(name)
        self.astrolW.menu_select('Measurements->Show data')
        datW = self.astrolApp.window(handle=find_window(title_re=".*dat.*"))
        #datW=self.astrolOpenApp.window(title_re=".*dat.*")
        datW.set_focus()
        datW.Button4.click_input()
        expW = self.astrolApp.window(handle=find_window(title_re=".*export.*"))
        #expW=self.astrolOpenApp.window(title_re=".*export.*")
        expW.Save.click_input()
        try:
            window_hndl = find_window(title="Confirm Save As")
            conW = self.astrolApp.window(handle=window_hndl)
        #conW=self.astrolOpenApp.window(title_re=".*Confirm.*")
            conW.Yes.click_input()
        except WindowNotFoundError:
            pass
        time.sleep(2)
        datW.wait('ready')
        datW.close()
        try:
            self.astrolApp.window(handle=find_window(title_re="Battery cycler - Measurement program and Data editor")).close()
        except WindowNotFoundError:
            pass
    
    def availableCapacity(self):
        """
        Returns a string for the value of available channels
        """
        return str(self.nrChannels-(self.astrolW.treeview1.item_count()-1))
    
    def changeMass(self, name, mass):
        """
        Changes the mass (and corresponding current) for cell with name
        """
        # mass should be string type
        self.selectCell(name)
        self.astrolW.menu_select('Measurements->Edit measurement program')
        EditW = self.astrolApp.window(handle=find_window(title_re=".*"+str(name)+".*"))
        EditW.wait('ready')
        #check the box "Adjust current values proportionally"
        EditW.CheckBox.check_by_click()
        time.sleep(0.5)
        #Change mass in mg
        if "mg" in mass:
            EditW.Edit2.type_keys(mass)
        else:
            EditW.Edit2.type_keys(mass+' mg')
        EditW.send_keystrokes("{TAB}")
        time.sleep(0.2)
        # make changes immediate
        self.astrolApp.window(handle=find_window(title_re="Confirm"))['&YesButton'].click()
        self.astrolApp.window(handle=find_window(title_re="Battery cycler - Measurement program and Data editor")).Save.click_input()
        self.astrolApp.window(handle=find_window(title_re="Warning"))['&YesButton'].click()
        EditW.close()
        self.astrolApp.window(handle=find_window(title_re="Battery cycler - Measurement program and Data editor")).close()
        
"""

Main

"""
# Start bcycler
bcycler = batteryCycler()

# Queue initialisation
queue = []
ListCells = []

# Socket specifics
HEADER = 64
PORT = 5051
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

def handle_client(conn, addr):
    """
    Organizes recieved messages as querry or commands. If querry, handles it immediately, if command sends to queue for worker.
    """
    print(f"[NEW CONNECTION] {addr} connected.")
    msg_length = conn.recv(HEADER).decode(FORMAT)
    if msg_length:
        msg_length = int(msg_length)
        msg = conn.recv(msg_length).decode(FORMAT)
        
        # Messages are being structured accordingly
        # Q/C request additional_comments
        print(f"[{addr}] {msg}")
        typ = str(msg).split()[0]
        req = str(msg).split()[1]
        if len(str(msg).split())>2:
            ac = str(msg).split(maxsplit=2)[2]
        else:
            ac = 'no_additional_comments'

        # Two messages can be received: 1. Query or 2. Command.
        returnMsg='No comment'
        if typ == 'Q':
            # Querries are being replied to
            if req == 'availableCapacity':
                returnMsg = bcycler.availableCapacity()
                conn.send(returnMsg.encode(FORMAT))
            elif req == 'listCells':
                returnMsg = pickle.dumps(ListCells)
                conn.send(returnMsg)
            elif req == 'opt_get_designs':
                num_points = ac.split()[-1]
                points = get_designs(int(num_points), client_path=AX_PATH)
                returnMsg = pickle.dumps(points)
                conn.send(returnMsg)
        elif typ == 'C':
            # Commands are being enqueued
            queue.append([req, ac])
            print('req: '+req)
            print('ac: '+ac)
            print('addr: '+str(addr))
            returnMsg='[Command] '+req+' with '+ac+' has been received from '+str(addr)
            conn.send(returnMsg.encode(FORMAT))
    conn.close()

# Start worker & socket & keyboard listener
serverRunning = True

def worker():
    """
    Executes commands in order of queue
    """
    global ListCells
    while serverRunning:
        if len(queue) > 0:
            print("\nElement dequeued from queue:")
            command = queue.pop(0)
            print(command)
            if command[0] == 'prepareCell':
                file_template = 'cycling-file_aq_bo_2.mpr'
                if len(command[1].split()) == 1:
                    rand_name = command[1]
                    comments = 'no_additional_comments'
                else:
                    rand_name = command[1].split()[0]
                    comments = command[1].split(maxsplit=1)[1]
                bcycler.prepareCell(file_template, rand_name, comments)
            elif command[0] == 'startCell':
                # Start cell
                #rand_name = str(random.randint(0,9999))
                rand_name = command[1]
                # Start cell run
                bcycler.startCellName(rand_name)
            elif command[0] == 'stopCell':
                rand_name = command[1]
                bcycler.stopCellName(rand_name)
            elif command[0] == 'stopAllCells':
                bcycler.stopAllCells()
            elif command[0] == 'exportCelldata':
                rand_name = command[1]
                bcycler.exportCelldata(rand_name)
            elif command[0] == 'changeMass':
                if len(command[1].split()) == 1:
                    print("not enough inputs: changeMass cell_id mass")
                else:
                    rand_name = command[1].split()[0]
                    mass_change = command[1].split(maxsplit=1)[1]
                    bcycler.changeMass(rand_name, mass_change)
            elif command[0] == 'registerResults':
                cell_id = command[1].split()[0]
                trial_id = command[1].split()[1]
                mol_ratio = command[1].split()[2]
                try:
                    ce = get_CE(cell_id)
                    cap_discharge = get_capacity(cell_id)
                    print("CE = "+str(ce))
                    print("Discharge Capacity = "+str(cap_discharge))
                    register_results([({opt_output_dic['y0']: ce, opt_output_dic['y1']: cap_discharge, opt_output_dic['y2']: float(mol_ratio)}, int(trial_id))], client_path=AX_PATH)
                except ValueError:
                    cancel_trials([int(trial_id)], client_path=AX_PATH)
                    print('failed cell/trial.')
            print(command[0]+' exeuted!')
        try:
            ListCells = bcycler.listCells()
        except IndexError:
            pass
        except TypeError:
            ListCells = []
    print('Worker is stopping.')

workerThread = threading.Thread(target=worker)
workerThread.start()


def runSocket():
    """
    Starts server
    """
    print("[STARTING] server is starting...")
    server.listen()
    print(f"[LISTENING] Server is listening on {SERVER}")
    while serverRunning:
        conn, addr = server.accept()
        #ListCells = bcycler.listCells()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
    print(f"[LISTENING] Server is stopping on {SERVER}")

socketThread = threading.Thread(target=runSocket)
socketThread.start()


def keyboard_input():
    """
    Non-blocking quit server command
    """
    global serverRunning
    while serverRunning:
        keystrk=input('Press q to interrupt \n')
        # thread doesn't continue until key is pressed
        print('You pressed: ', keystrk)
        if keystrk == 'q':
            print('Server is stopping')
            serverRunning = False
            os._exit(0)
        if keystrk == 'listcells':
            print(ListCells)


keyboardThread=threading.Thread(target=keyboard_input)
keyboardThread.start()
