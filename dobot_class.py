from logging import raiseExceptions
from multiprocessing.sharedctypes import Value
from typing import List

from dobot_api_v2 import *
from coordinate_funcs import *
import numpy as np
import time
from dataclasses import dataclass
from threading import Thread, Event


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
        self.feedback = DobotApi(ip_address, 30005)
        self.Stop_Event = Event() 
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
        """Starts live feedback thread"""
        #Initialize position dataclass
        self.pos = Robot_Position(*[0.0, 0.0, 0.0, 0.0, 0.0])
        self.di = 0
        self.pos_theta = 0
        #create and start feedback thread
        thread = Thread(target=self.feedback_thread, args=([self.Stop_Event]))
        thread.setDaemon(True)
        thread.start()
    
    def feedback_thread(self, stop_event):
        """Updates Dobot coordinates and other information every 5ms based on feedback port"""
        hasRead = 0
        print_counter = 0
        while not stop_event.is_set():
            data = bytes()
            while hasRead < 1440:
                temp = self.feedback.socket_dobot.recv(1440 - hasRead)
                if len(temp) > 0:
                    hasRead += len(temp)
                    data += temp
            hasRead = 0
            
            a = np.frombuffer(data, dtype=MyType)
            if hex((a['test_value'][0])) == '0x123456789abcdef':
            #other possible parameters to update; check Dobot Github for options
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
                    self.dashboard.ClearError()
                    self.dashboard.DisableRobot()

            time.sleep(0.15)

    
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
        
    def vacuum(self, isOn):
        """
        Turns on and off the vacuum. Has a bit of added delays before and after the execution command\n
        Input:\n
        isOn (Boolean)-> True = turn on; False = turn off \n
        Output:\n
        none
        """
        if isOn == True:
            self.dashboard.DO(2, 1)
            time.sleep(0.5)
        elif isOn == False:
            self.dashboard.DO(2, 0)
            time.sleep(0.5)
        
    
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
        
    def pick_n_place(self, pick_location, place_location, ref_h=105.0, intermediate_h=-77.0, pushdown=False, slowdown=False):
        """
        Picks up a component from the component tray in working area and puts it into the cell holder position. Can be used more generally for different pickup and drop off locations.\n
        Inputs:\n
        pick_location (list)-> list of [x,y,z,Rx]\n
        place_location (list)-> list of [x,y,z,Rx]\n
        ref_h (float)-> value of z (height) that the robot will bring the picked up component before going to place location\n
        intermediate_h (float)-> value of z (height) just before pick up location that the robot will go to (at default/full speed) before slowing down to pick up component\n
        pushdown (Boolean)-> True = will push down by 4 units (mm) after placing component, False = no push down after placing component\n
        Output: \n
        none
        """

        # move to above the component and then drop to above the working area tray
        self.mov('j', movetoheight(pick_location, ref_h))
        self.mov('l', movetoheight(pick_location, intermediate_h))
        # move to pickup component
        self.mov('l', pick_location)
        self.vacuum(True)
        self.command.Sync()
        time.sleep(1)
        self.dashboard.SpeedFactor(5)
        # move to above the component
        self.mov('l', movetoheight(pick_location, ref_h))
        # move to above the place location
        if not slowdown:
            self.dashboard.SpeedFactor(self.default_speed)
        self.mov('j', movetoheight(place_location, ref_h))
        self.mov('l', place_location)
        self.dashboard.SpeedFactor(self.default_speed)
        if pushdown:
            self.vacuum(False)
            time.sleep(0.3)
            self.command.RelMovL(0,0,-4.0)
            time.sleep(0.3)
            self.command.RelMovL(0,0,4.0)
        else:
            self.vacuum(False)
        self.command.Sync()
        time.sleep(1)
        # after vacuum off, move up to reference height
        self.mov('l', movetoheight(place_location, ref_h))
        self.command.Sync()


    def load_working_area(self, num_trays, stack, ref_h=105.0):
        """
        Brings a tray from the Middle stack to the working area.\n
        Input:\n
        num_trays (int [1,10])-> how many loaded trays are there currently in the stack (excludes the bottom-most tray)?
        I.e. If there are two trays in total (one tray loaded with parts and the (empty) bottom-most tray) then the stack_id = 1\n
        stack (int [0, inf]) -> which stack to take from, i.e. 0 is closest to working area, 1 is beside 0, etc.
        Output:\n
        none
        """
        # calculate stack height/what height to move to to pick up tray
        stack_height = (num_trays-1)*6.45 #relative height of the stack
        placedown_location = get_pnt('Working Tray Location', self.coord) #define the working area drop off point
        pickup_location = get_pnt('Stack Location '+str(stack), self.coord) #define stack pickup point (only for the x and y)
        pickup_height = pickup_location[2] + stack_height
        pickup_location[2] = pickup_height #replace middle stack pickup point height (z) with calculated pickup_height
        self.mov('j', movetoheight(pickup_location, ref_h))
        self.pick_n_place(pick_location=pickup_location, place_location=placedown_location, ref_h=3.7, intermediate_h=pickup_height+8.0, slowdown=True)

    def emptytray_to_bin(self, ref_h=105.0):
        """
        Moves the empty tray in the working area to the bin; clears empty tray from working area
        """
        Pick_loc = get_pnt('Working Tray Location', self.coord)
        Pick_loc[2] -= 9.5 
        Place_loc = get_pnt('Empty Tray Bin', self.coord)
        self.pick_n_place(pick_location=Pick_loc, place_location=Place_loc, ref_h=ref_h, intermediate_h=Pick_loc[2]+15.0, slowdown=True)
        

    def close(self):
        self.command.close()
        self.dashboard.close()
        self.Stop_Event.set()
        time.sleep(0.2)
        self.feedback.close()