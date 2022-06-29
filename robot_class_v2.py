from logging import raiseExceptions
from multiprocessing.sharedctypes import Value
from typing import List

from pyrsistent import b
from dobot_api_v2 import *
import paramiko
import numpy as np
import pandas as pd
import time
from dataclasses import dataclass
from threading import Thread

@dataclass
class Robot_Position:
    __slots__ = ['x', 'y', 'z', 'r1', 'pos']
    x: float
    y: float
    z: float
    r1: float
    pos: np.ndarray

    def update_pos(self, coord_list):
        self.pos = coord_list[:4]
        self.x = coord_list[0]
        self.y = coord_list[1]
        self.z = coord_list[2]
        self.r1 = coord_list[3]


class Dobot:
    def __init__(self, ip_address):
        self.dashboard = DobotApiDashboard(ip_address, 29999)
        self.command = DobotApiMove(ip_address, 30003)
        self.feedback = DobotApi(ip_address, 30004)
        self.connected = True
        self.pos = Robot_Position(*[0.0, 0.0, 0.0, 0.0, 0.0])
        self.di = 0
        self.pos_theta = 0
        self.set_feedback()
        self.dashboard.EnableRobot()
        #self.dashboard.ClearError()
        # Set collision detection level
        #self.collision_level(3)
        #self.dashboard.EnableRobot()
        #self.dashboard.User(0)
        #self.dashboard.Tool(0)
        ##self.homed_status = False
        #self.default_speed = 25
        #self.dashboard.SpeedFactor(self.default_speed)
        #self.speed(self.default_speed)

    def set_feedback(self):
        thread = Thread(target=self.feedback_thread)
        thread.setDaemon(True)
        thread.start()
    
    def feedback_thread(self):
        """Updates Dobot coordinates and other information every 5ms based on feedback port"""
        hasRead = 0
        print_counter = 0
        while True:
            if not self.connected:
                break
            data = bytes()
            while hasRead < 1440:
                temp = self.feedback.socket_dobot.recv(1440 - hasRead)
                if len(temp) > 0:
                    hasRead += len(temp)
                    data += temp
            hasRead = 0
            
            a = np.frombuffer(data, dtype=MyType)
            if hex((a['test_value'][0])) == '0x123456789abcdef':
                # print('tool_vector_actual',
                #       np.around(a['tool_vector_actual'], decimals=4))
                # print('q_actual', np.around(a['q_actual'], decimals=4))

                # Refresh Properties
                #self.label_feed_speed["text"] = a["speed_scaling"][0]
                #self.label_robot_mode["text"] = LABEL_ROBOT_MODE[a["robot_mode"][0]]
                #self.label_di_input["text"] = bin(a["digital_input_bits"][0])[
                #    2:].rjust(64, '0')
                #self.label_di_output["text"] = bin(a["digital_output_bits"][0])[
                #    2:].rjust(64, '0')

                # Refresh coordinate points
                #self.set_feed_joint(LABEL_JOINT, a["q_actual"])
                self.pos.update_pos(a["tool_vector_actual"][0])
                self.di = a["digital_input_bits"][0]
                self.pos_theta = a["q_actual"][0][0]
                #print(self.di)
                #print(self.pos)

                # check alarms
                if a["robot_mode"] == 9:
                    print("error")

            time.sleep(0.005)
            #testing
            #print_counter += 1
            #if print_counter == 150:
            #    print_counter = 0
            #    print("{}:{}:{}|     DI: {}".format(*time.localtime()[3:6], self.di))

    
    def update_default_speed(self, speed):
        """
        Changes default speed of the Dobot.\n
        Input:\n
        speed (int)-> speed from (0,100]\n
        Output:\n
        none (default_speed attribute changes and the current default_speed is printed)
        """
        self.default_speed = speed
        print('default speed: {}'.format(self.default_speed))

    def mov(self, mode, pnt, blocking=False):
        """
        Move the Dobot to point defined by pnt.\n
        Inputs:\n
        mode (str 'j'/'l')-> 'j' for MovJ and 'l' for MovL\n
        pnt (list)-> list containing the coordinates for the point the Dobot moves to [X,Y,Z,Rx,Ry,Rz]\n
        Output:\n
        none
        """
        if (isinstance(mode, str) and isinstance(pnt, (list, np.ndarray))):
            if mode.lower() == 'j':
                self.command.MovJ(*pnt)
            elif mode.lower() == 'l':
                self.command.MovL(*pnt)
            if blocking:
                while True:
                    time.sleep(0.7)
                    pnt_distance = np.linalg.norm(np.array(self.pos.pos[:3])-np.array(pnt[:3]))
                    #print(pnt_distance)
                    if pnt_distance < 1.0:
                        break
        else:
            print("Wrong arugment types")
        
    
    def RawInput(self, cmd, srvr):
        """
        Directly sends a string (command) to one of the Dobot servers (dashboard/command).\n
        Inputs:\n
        cmd (str)-> Command to send to the Dobot. Defined commands are available in the Dobot SDK github.\n
        srvr (str 'd'/'c')-> send command cmd to dashboard server ('d') or feedback server ('c')\n
        Output:\n
        none but probably Dobot will return/print 'receive...'
        """
        if srvr == 'd':
            self.dashboard.send_data(cmd)
        elif srvr == 'c':
            self.command.send_data(cmd)
        else:
            return

    def __del__(self):
        self.dashboard.DisableRobot()

class Dobbie_Crimp(Dobot):
    def __init__(self, ip_address):
        super().__init__(ip_address)
        self.update_default_speed(40)
        self.dashboard.SpeedFactor(self.default_speed)
        # loaded_state = [Is Dobbie carrying a holder: True/False, which holder: 0/1]
        self.loaded_state = [False, 0]
        # holder_state = what should the next step be:
        # 0 -> need to get P casing, cathode, separator
        # 1 -> need to get electrolyte
        # 2 -> need to get anode, spacer&spring, N casing
        # 3 -> need to be crimped 
        self.holder_state = [0, 0]
        # load coordinates
        self.coord = get_coords('Crimp')

    # Low Level API
    def crimp(self):
        """
        Function to start crimping. Turns on the Digital Output (DO) 1 to ON for 2.5 seconds then switches OFF.
        """
        self.dashboard.DO(1, 1)
        time.sleep(2.5)
        self.dashboard.DO(1, 0)

    def wait_crimper(self):
        """
        Blocks and returns when crimping is finished
        """
        if self.di == 1:
            while True:
                time.sleep(1)
                if self.di == 0:
                    break
        #else:
        #    raise Exception("Nothing is being crimpped")
            
    def reset_holder_state(self, holder):
        """
        Resets the state of holder X to 0 = has nothing/need to collect P casing, etc...\n
        Input:\n
        holder (int)-> which holder? [0, 1]\n
        Output:\n
        none
        """
        self.holder_state[holder] = 0
    
    def update_coord(self):
        """
        Updates the coordinates - to be used when changes to the excel file is made.
        """
        self.coord = get_coords('Crimp')

    #High Level API
    def pickup_cellholder(self):
        """
        Move Dobot just outside of Otto -> inside Otto -> pickup cell holder -> outside Otto with cell holder
        """
        self.mov('j', get_pnt(0, self.coord))
        self.mov('l', get_pnt(1, self.coord))
        self.mov('l', get_pnt(2, self.coord))
        self.mov('l', get_pnt(3, self.coord))
        self.command.Sync()

    def load_components(self):
        """
        Move Dobot to outside Otto with cell holder and then to meeting position with Dobie Cell.
        """
        self.mov('l', get_pnt(3, self.coord))
        self.mov('j', get_pnt(8, self.coord))
        self.command.Sync()
    
    def get_electrolyte(self):
        """
        Move Dobot to outside Otto with cell holder and then inside Otto for getting electrolyte.
        """
        self.mov('j', get_pnt(3, self.coord))
        self.mov('l', get_pnt(2, self.coord))
        self.command.Sync()

    def load_crimper(self):
        """
        Move Dobot to in front of Crimper (loaded) -> drop cell holder into Crimper hole -> in front of Crimper (unloaded)
        """
        self.mov('j', get_pnt(4, self.coord))
        self.dashboard.SpeedFactor(20)
        self.mov('l', get_pnt(5, self.coord))
        self.mov('l', get_pnt(6, self.coord))
        self.mov('l', get_pnt(7, self.coord))
        self.dashboard.SpeedFactor(self.default_speed)
        self.command.Sync()

    def to_slide(self):
        """
        Move Dobot to in front of Crimper (unloaded) -> pickup crimped cell & cell holder -> meeting position with Dobie Cell
        """
        self.mov('j', get_pnt(7, self.coord))
        self.dashboard.SpeedFactor(20)
        self.mov('l', get_pnt(6, self.coord))
        self.mov('l', get_pnt(5, self.coord))
        self.dashboard.SpeedFactor(self.default_speed)
        self.mov('l', get_pnt(4, self.coord))
        self.mov('j', get_pnt(8, self.coord))
        self.command.Sync()

 
    def return_cellholder(self):
        """
        Move Dobot to outside of Otto (loaded) -> inside Otto (loaded) -> drop cell holder into holder in Otto -> outside Otto (unloaded)
        """
        self.mov('j', get_pnt(3, self.coord))
        self.mov('l', get_pnt(2, self.coord))
        self.mov('l', get_pnt(1, self.coord))
        self.mov('l', get_pnt(0, self.coord))
        self.command.Sync()
        self.loaded_state[0] = False
        
    def home(self):
        """
        Moves Dobot to outside Otto (loaded) position.\n
        \nFirst moves Dobot closer to the origin keeping constant angle, until the radius is the same as the rotation radius for moving between Crimper and Otto.
        Then rotates to outside Otto (loaded). 
        """
        # calculate radius we want to move to
        target_r = get_r(*get_pnt(3, self.coord)[0:2])
        # calculate radius and angle of current position
        current_zRxRyRz = self.pos.pos[2:]
        # decrease radius with same angle until radius same as target_r (using MovL)
        moveto_pnt = get_xy(target_r, self.pos_theta)
        moveto_pnt.extend(current_zRxRyRz)
        self.mov('l', moveto_pnt)
        # rotate to desired 'home' position
        self.mov('j', get_pnt(3, self.coord))
        self.command.Sync()

class Dobbie_Cell(Dobot):
    def __init__(self, ip_address):
        super().__init__(ip_address)
        self.update_default_speed(30)
        self.dashboard.SpeedFactor(self.default_speed)
        #component tray status
        self.tray_status = [0,0,0,0,0,0]
        # load coordinates - cell components, stacks, and cycler/slide
        self.coord = get_coords('Cell components')
        self.stack_coord = get_coords('Stacks')

    def update_coord(self):
        """
        Updates the coordinates - to be used when changes to the excel file is made.
        """
        self.coord = get_coords('Cell components')
        self.stack_coord = get_coords('Stacks')
        self.cycler_coord = get_coords('Cycler')

    def vacuum(self, isOn):
        """
        Turns on and off the vacuum. Has a bit of added delays before and after the execution command\n
        Input:\n
        isOn (Boolean)-> True = turn on; False = turn off \n
        Output:\n
        none
        """
        if isOn == True:
            self.dashboard.DO(10, 1)
            time.sleep(0.5)
        elif isOn == False:
            self.dashboard.DO(10, 0)
            time.sleep(0.5)
    
    def blow(self):
        """
        Reverses vacuum for a short amount of time - blows air out of nozzles. Has a bit of added delays before and after the execution command.
        """
        self.dashboard.DO(9, 1)
        time.sleep(0.2)
        self.dashboard.DO(9, 0)
    
    def pick_n_place(self, cell, component):
        """
        Picks up a component from the component tray in working area and puts it into the cell holder meeting position.\n
        Inputs:\n
        cell (int [1,4])-> which cell of the tray to take the component from - MUST correspond to naming convention in excel file of coordinates\n
        component (str) -> Must be 'P casing'=cathode casing, 'cath'=cathode, 'sep'=separator, 'ano'=anode, 'space'=spacer&spring, or 'N casing'=anode casing\n
        MUST correspond to naming convention in excel file of coordinates!\n
        Output: \n
        none
        """
        if component not in ['P casing', 'cath', 'sep', 'ano', 'space', 'N casing']:
            print("use component keywords:\nP casing\ncath\nsep\n4:ano\nspace\nN casing")
        else:
            # move to above the component and then drop to above the working area tray
            self.mov('j', movetoheight(get_pnt('Cell '+str(cell)+': '+component, self.coord), 34))
            self.mov('l', movetoheight(get_pnt('Cell '+str(cell)+': '+component, self.coord), -30.464))
            # move to pickup component
            self.mov('l', get_pnt('Cell '+str(cell)+': '+component, self.coord))
            self.vacuum(True)
            self.command.Sync()
            time.sleep(1)
            self.dashboard.SpeedFactor(5)
            # move to above the component
            self.mov('l', movetoheight(get_pnt('Cell '+str(cell)+': '+component, self.coord), 34))
            if component in ['P casing', 'cath', 'sep']:
                nozzle = 'Large'
            elif component in ['ano', 'space', 'N casing']:
                nozzle = 'Small'
            # move to above the cell holder
            self.dashboard.SpeedFactor(self.default_speed)
            self.mov('j', movetoheight(get_pnt(nozzle+' nozzle drop', self.coord), 34))
            # move to cell holder drop component position
            self.mov('l', get_pnt(nozzle+' nozzle drop', self.coord))
            if component == 'P casing':
                self.vacuum(False)
                self.command.Sync()
                self.dashboard.DO(9, 1)
                time.sleep(0.3)
                self.command.RelMovL(0,0,-2.9)
                self.command.Sync()
                time.sleep(0.7)
                self.dashboard.DO(9,0)
            elif component == 'cath':
                self.command.RelMovL(0,0,-2.8)
                self.vacuum(False)
            else:
                self.vacuum(False)
            self.command.Sync()
            time.sleep(1)
            # if the component is the separator then blow, otherwise do not blow after turning off vacuum and then move up a bit
            if component in ['sep']:
                self.blow()
            self.mov('l', movetoheight(get_pnt(nozzle+' nozzle drop', self.coord), 34))
            self.command.Sync()
            # if the last component (anode casing) is being picked up then run corrector which helps position anode casing correctly
            if component == 'N casing':
                self.corrector()
                #time.sleep(3)
        
    def holder_to_slide(self):
        """
        Transfers crimped cell from the cell holder (on Dobie Crimp) to the slide for flipping.
        Drops cell into slide and is ready to pick up for cell cycling.\n
        """
        self.mov('j', movetoheight(get_pnt('Small nozzle drop', self.coord), 34))
        holder_pickup_z = get_pnt('Small nozzle drop', self.coord)
        holder_pickup_z[2] -= 1.8
        self.mov('l', holder_pickup_z)
        self.dashboard.SpeedFactor(5)
        self.vacuum(True)
        self.command.Sync()
        time.sleep(1)
        self.mov('l', movetoheight(get_pnt('Small nozzle drop', self.coord), 50))
        self.dashboard.SpeedFactor(self.default_speed)
        self.mov('j', get_pnt('Slide intermediate', self.coord))
        self.mov('l', get_pnt('Slide drop', self.coord))
        self.vacuum(False)
        self.command.Sync()
        time.sleep(1)
        self.dashboard.SpeedFactor(15)
        #Corrector for slide - not to be confused with corrector function below
        self.mov('l', get_pnt('Slide correct 1', self.coord))
        self.mov('l', get_pnt('Slide correct 2', self.coord))
        self.mov('l', get_pnt('Slide correct 3', self.coord))
        self.mov('l', get_pnt('Slide correct 4', self.coord))
        self.mov('l', get_pnt('Slide correct 5', self.coord))
        self.dashboard.SpeedFactor(self.default_speed)
        self.mov('j', get_pnt('Slide intermediate', self.coord))
        self.command.Sync()

    def corrector(self):
        """
        Pushes the negative (anode) casing into place for crimping if it was dropped slightly off center.
        Performs 4 sets of pushing/dragging moves (edge to center).
        Points are defined in the excel file (same sheet as component locations).
        """
        for pnt in ['Corrector point 2', 'Corrector point 1', 'Corrector point 3']:
            self.mov('j', get_pnt(pnt, self.coord))
            self.mov('l', get_pnt('Small nozzle drop', self.coord))
            if pnt == "Corrector point 3":
                self.command.RelMovL(0,0,-1.0)
                self.command.Sync()
            self.mov('l', movetoheight(get_pnt('Small nozzle drop', self.coord), 34.0))
        self.command.Sync()
        time.sleep(0.2)

    def home(self):
        """
        Ensure the vacuum is off and moves up from its current position to a height of 50. Then rotates to the position specified by the second index position in the Stacks sheet of the excel file 
        """
        self.vacuum(False)
        self.command.RelMovL(0,0,15)  
        self.mov('j', movetoheight(get_pnt(1, self.stack_coord), 50))
        self.command.Sync()

    def load_workingarea(self, stack_id, stack):
        """
        Brings a tray from the Middle stack to the working area.\n
        Input:\n
        stack_id (int [0,10])-> how many trays are there currently in the stack excluding the bottom-most tray?
        I.e. If there are two trays in total (one tray loaded with parts and the (empty) bottom-most tray) then the stack_id = 0\n
        stack (int [0, inf]) -> which stack to take from, i.e. 0 is closest to working area, 1 is beside 0, etc.
        Output:\n
        none
        """
        # Dictionary mapping stack (int) to name in excel sheet (str)
        stack_name = {0: 'Middle stack pickup',
                      1: 'Centre stack pickup'}

        # home Dobbie Cell first because home should be around the same location as the trays
        self.home()
        # calculate stack height/what height to move to to pick up tray
        stack_height = stack_id*6.45 #relative height of the stack
        drop_pnt = get_pnt('working drop', self.stack_coord) #define the working area drop off point
        pickup_height = stack_height + drop_pnt[2] - 5.7 #calculate the height to turn on vacuum = stack height + working area drop off point height - arbitrary offset/displacement to reach the tray
        pickup_pnt = get_pnt(stack_name[stack], self.stack_coord) #define stack pickup point (only for the x and y)
        pickup_pnt[2] = pickup_height #replace middle stack pickup point height (z) with calculated pickup_height
        # move to 15mm above the pick up point (where the vacuum will be turned on) and then drop to pickup point
        self.mov('j', movetoheight(pickup_pnt, pickup_height+15))
        self.mov('l', pickup_pnt)
        self.vacuum(True)
        self.dashboard.SpeedFactor(5)
        self.command.Sync()
        time.sleep(1)
        self.mov('l', movetoheight(pickup_pnt, pickup_height+15))
        self.mov('j', movetoheight(drop_pnt, pickup_height+15))
        self.mov('l', drop_pnt)
        self.vacuum(False)
        self.command.Sync()
        time.sleep(0.5)
        self.blow()
        self.dashboard.SpeedFactor(self.default_speed)
        self.mov('l', movetoheight(drop_pnt, 50))

    def stack_to_bin(self):
        self.mov('j', movetoheight(get_pnt('working pickup', self.stack_coord), 50))
        self.mov('l', get_pnt('working pickup', self.stack_coord))
        self.vacuum(True)
        self.command.Sync()
        time.sleep(1)
        self.dashboard.SpeedFactor(5)
        self.command.RelMovL(0, 0, 15)
        self.mov('j', movetoheight(get_pnt('Bin', self.stack_coord), get_pnt('working pickup', self.stack_coord)[2]+15))
        self.dashboard.SpeedFactor(self.default_speed)
        self.mov('l', get_pnt('Bin', self.stack_coord))
        self.vacuum(False)
        self.command.Sync()
        time.sleep(1)
        self.blow()
        self.command.RelMovL(0, 0, 55)
        self.home()

class Dobbie_Grip(Dobot):
    def __init__(self, ip_address):
        super().__init__(ip_address)
        self.update_default_speed(25)
        self.dashboard.SpeedFactor(self.default_speed)
        self.coord = get_coords('Cycler')

    def slide_to_cycler(self, cycler_id):
        """
        Move cell from slide to cell cycling station.
        Assumes flip successful coin cell in vertical position.
        Input:\n
        cycler_id (str)-> name of cycler as defined in the excel file.\n
        Output:\n
        none
        """
        self.mov('j', movetoheight(get_pnt('slide', self.coord), 110))
        self.grip(False)
        self.mov('l', get_pnt('slide', self.coord))
        self.command.Sync()
        time.sleep(1)
        self.grip()
        time.sleep(1)
        self.mov('l', movetoheight(get_pnt('slide', self.coord), 110))
        cycler_pnt = get_pnt(cycler_id, self.coord)
        # move to above the specified cycler location
        self.mov('j', movetoheight(cycler_pnt, 110))
        self.mov('l', cycler_pnt)
        self.command.Sync()
        time.sleep(0.5)
        self.grip(False)
        time.sleep(0.75)
        # move back up to above the specified cycler location
        self.mov('l', movetoheight(cycler_pnt, 110))
        self.command.Sync()
        self.grip()

    def grip(self, state=True):
        if state:
            self.dashboard.DO(9,0)
        elif state==False:
            self.dashboard.DO(9,1)

    def remove_from_cycler(self, cycler_id):
        """
        Removes cycled cell from cycler station and drops into the waste bin.\n
        Input:\n
        cycler_id (str)-> name of cycler as defined in the excel file.\n
        Output:\n
        none
        """
        self.mov('j', movetoheight(get_pnt(cycler_id, self.coord), 110))
        self.grip(False)
        self.mov('l', get_pnt(cycler_id, self.coord))
        self.command.Sync()
        time.sleep(1)
        self.grip()
        time.sleep(1)
        self.mov('l', movetoheight(get_pnt(cycler_id, self.coord), 110))
        self.mov('j', movetoheight(get_pnt('bin', self.coord), 110))
        self.mov('l', get_pnt('bin', self.coord))
        self.grip(False)
        self.command.Sync()
        time.sleep(1)
        self.grip()
        self.mov('l', movetoheight(get_pnt('bin', self.coord), 110))
        self.command.Sync()

    def home(self):
        self.mov('l', movetoheight(self.pos.pos, 95))
        self.grip()
        self.mov('j', movetoheight(get_pnt('1-1', self.coord), 110))
        self.command.Sync()

class OT2:
    def __init__(self, ip_addr):
        self.keyfilename = 'C:\\Users\\renrum\\ot2_ssh_key'
        try:
            self.k = paramiko.RSAKey.from_private_key_file(self.keyfilename, 'otto')
        except FileNotFoundError:
            print("No such file or directory: "+self.keyfilename)
            self.keyfilename = input("Enter correct directory and file name\n")
            self.k = paramiko.RSAKey.from_private_key_file(self.keyfilename, 'otto')
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname=ip_addr, username='root', pkey=self.k)
        self.ssh_channel = self.ssh.invoke_shell()
        #change working directory
        self.ssh_channel.send('cd /var/lib/jupyter/notebooks\n'.encode())
        time.sleep(0.3)
        #start the startup.py file which defines all the labware and homes Otto so it is ready to go
        self.ssh_channel.send('python -i startup.py\n'.encode())
        time.sleep(0.3)
        print(self.get_output())
        self.small_tip_index = 0
        self.large_tip_index = 0
        self.odacell_well_index = 0


    def get_output(self):
        """
        returns the output string from Otto that was stored in the stdout of the ssh client
        """
        if self.ssh_channel.recv_ready():
            output = self.ssh_channel.recv(1024)
            return output.decode()
        if  self.ssh_channel.recv_stderr_ready():
            output = self.ssh_channel.recv_stderr(1024)
            return output.decode()

    def RawInput(self, cmd):
        """
        Directly sends a string (python command) to the python program opened in the pseudo terminal shell of the Otto ssh client.\n
        Inputs:\n
        cmd (str)->python command. The characters "backslash n" is appended to the end of the command which executes it (pressing Enter in the terminal)\n
        Output:\n
        none but probably will print output from get_output() function
        """
        self.ssh_channel.send(str(cmd+"\n").encode())
        #output_str = self.get_output()
        #if isinstance(output_str, str):
        #    print(output_str)
    
    def odacell_dispense_electrolyte(self, electrolyte_location, volume, name_id=""):
        """
        Otto gets electrolyte from a well and dispenses it to the cell holder.
        A new tip will be picked up each time this function is run and will be dropped into the trash at the end of the function. Otto will then home.\n
        Inputs:\n
        electrolyte_location (str)-> full name of the python-defined well location (i.e. "wellplate_odacell['A1']")\n
        volume (int)-> volume of liquid to transfer in uL.\n
        Example code: otto.odacell_dispense_electrolyte("wellplate_odacell['A1']", 70)\n
        Output:\n
        none but the outputs will be printed.
        """
        clear_cache = self.get_output()
        self.RawInput("pipette_right.pick_up_tip(s_tiprack.wells()["+str(self.small_tip_index)+"])")
        self.RawInput("pipette_right.transfer("+str(volume)+", "+electrolyte_location+", cell_holder.wells()[0], new_tip='never')")
        self.RawInput("pipette_right.drop_tip()")
        self.small_tip_index += 1
        time.sleep(2)
        self.RawInput("print('dispensed electrolyte for "+name_id+"')")
        check_1 = 0
        while True:
            otto_output = self.get_output()
            if isinstance(otto_output, str):
                print(otto_output)
                #if otto_output[-4:] == '>>> ':
                if (("dispensed electrolyte for "+name_id) in otto_output) and check_1 == 1:
                    break
                if ("print('dispensed electrolyte for "+name_id+"')") in otto_output:
                    check_1 += 1
            time.sleep(0.5)

    def prepare_electrolyte(self, stock_solutions, electrolyte_comp, electrolyte_location):

        dilution_factors = [liquid[1]/stock_solutions[stock_solutions.index(n)][-1] for liquid in electrolyte_comp[1:] for n in stock_solutions if liquid[0] in n]
        stock_ids = [n[0] for liquid in electrolyte_comp[1:] for n in stock_solutions if liquid[0] in n]
        transfer_volumes = [i * electrolyte_comp[0] for i in dilution_factors]
        solvent_volume = electrolyte_comp[0] - np.sum(transfer_volumes)
        if solvent_volume < 20:
            raise ValueError
        for vol in transfer_volumes:
            if vol < 20:
                raise ValueError

        for k,s in zip(transfer_volumes,stock_ids):
            if 20 <= k <= 300:
                self.RawInput("pipette_right.pick_up_tip(s_tiprack.wells()["+str(self.small_tip_index)+"])")
                self.RawInput("pipette_right.transfer("+str(k)+", stock_solutions.wells()["+str(s)+"], "+electrolyte_location+", new_tip='never')")
                self.RawInput("pipette_right.drop_tip()")
                self.small_tip_index += 1
            elif k > 300:
                self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
                self.RawInput("pipette_left.transfer("+str(k)+", stock_solutions.wells()["+str(s)+"], "+electrolyte_location+", new_tip='never')")
                self.RawInput("pipette_left.drop_tip()")
                self.large_tip_index += 1
            elif k < 20:
                raise ValueError
                
        
        if 20 <= solvent_volume <= 300:
            self.RawInput("pipette_right.pick_up_tip(s_tiprack.wells()["+str(self.small_tip_index)+"])")
            self.RawInput("pipette_right.transfer("+str(solvent_volume)+", stock_solutions.wells()[0], "+electrolyte_location+", new_tip='never', mix_after=(6,275))")
            self.RawInput("pipette_right.drop_tip()")
            self.small_tip_index += 1
        elif solvent_volume > 300:
            self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
            self.RawInput("pipette_left.transfer("+str(solvent_volume)+", stock_solutions.wells()[0], "+electrolyte_location+", new_tip='never', mix_after=(6,800))")
            self.RawInput("pipette_left.drop_tip()")
            self.large_tip_index += 1
        
        self.odacell_well_index += 1
        clear_cache = self.get_output()

def get_coords(Sheet_Name = 'Crimp', file_loc = r'C:\Users\renrum\Desktop\Coordinates\coordinates.xlsx'):
    """
    Loads relevant point locations for specific robots into a pandas dataframe.\n
    Inputs: \n
    Sheet_Name (str)-> Sheet names can be: \n
    'Crimp' \n
    'Cell components' \n
    'Stacks' \n
    'Cycler' \n
    \n
    file_loc (str)-> file location. Must be an excel file.\n
    Output: \n
    coords (pandas dataframe)-> dataframe containing the [Name, X,Y,Z,Rx,Ry,Rz] coordinates.
    """
    return pd.read_excel(file_loc, sheet_name=Sheet_Name)

def get_pnt(p, df):
    """
    Get the point [x,y,z,Rx] from the coordinate dataframe. \n
    Input: \n
    p (int/str)-> int for indexing; str for mapping using the corresponding Name column of dataframe \n
    df (pandas dataframe)-> coordinate dataframe - default variable name is self.coord \n
    Output: \n
    pnt (list)-> list of [x,y,z,Rx] \n
    """
    if isinstance(p, int):
        return df.loc[p, ['X', 'Y', 'Z', 'Rx']].values.flatten().tolist()
    elif isinstance(p, str):
        return df.loc[df.Name == p, ['X', 'Y', 'Z', 'Rx']].values.flatten().tolist()

def get_r(x,y):
    """
    Convert 2D x,y Cartesian coordinates to radius r. \n
    Input: \n
    x (float)-> x coordinate in mm \n
    y (float)-> y coordinate in mm \n
    Output: \n
    r (float)-> radius/hypotenuse in mm \n
    """
    return np.sqrt(x**2 + y**2)

def get_xy(r,theta):
    """
    Convert 2D radial coordinates to Cartesian coordinates \n
    Input: \n
    r (float)-> radius in mm \n
    theta (float)-> angle in degrees \n
    Output: \n
    xy (list)-> [x,y] coordinates in mm \n
    """
    return [r*np.cos(theta*np.pi/180), r*np.sin(theta*np.pi/180)]

def movetoheight(pnt, z):
    """
    Takes a list and absolute height and returns the list with that height (in index 2) \n
    Input: \n
    pnt (list)-> list of a coordinate point [X,Y,Z,Rx] \n
    z (float)-> desired height \n
    Output: \n
    temp_pnt (list)-> list with new z replacing old Z [X,Y,z,Rx] \n
    """
    if isinstance(pnt, (list, np.ndarray)):
        temp_pnt = list(pnt).copy()
        temp_pnt[2] = z
        return temp_pnt
    else:
        print("Coordinate point is not a list [x,y,z,rx]")

# Sample Code
#dcrimp = Dobbie_Crimp('192.168.2.6')
#dcell = Dobbie_Cell('192.168.1.6')

#dcrimp.mov('l', dcrimp.p1)



