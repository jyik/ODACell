from logging import raiseExceptions
from multiprocessing.sharedctypes import Value
from typing import List

from dobot_api_v2 import *
from coordinate_funcs import *
import numpy as np
import time
from dataclasses import dataclass
from threading import Thread, Event
from camera import take_img, find_outer_circle, cam_offset_to_robot, find_latest_top_img, get_similarity


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
        self.dashboard.ClearError()
        self.camera_center_offset = np.array([0.0, 0.0, 0.0, 0.0])
        self.robot_id = ""
        #self.collision_level(3)        # Set collision detection level. If unset, it is equal to the level on software 
        
    def set_feedback(self):
        """Starts live feedback thread"""
        #Initialize position dataclass
        self.pos = Robot_Position(*[0.0, 0.0, 0.0, 0.0, 0.0])
        self.di = 0
        self.pos_theta = 0
        self.robot_status = 1
        #create and start feedback thread
        thread = Thread(target=self.feedback_thread, args=([self.Stop_Event]))
        thread.setDaemon(True)
        thread.start()
    
    def feedback_thread(self, stop_event):
        """Updates Dobot coordinates and other information every 0.2s based on feedback port"""
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
            
            self.feedInfo = np.frombuffer(data, dtype=MyType)
            if hex((self.feedInfo['test_value'][0])) == '0x123456789abcdef':
            #other possible parameters to update; check Dobot Github for options

                self.pos.update_pos(self.feedInfo["tool_vector_actual"][0])
                self.di = self.feedInfo["digital_input_bits"][0]
                self.pos_theta = self.feedInfo["q_actual"][0][0]
                self.robot_status = self.feedInfo["robot_mode"][0]
                self.get_speed = self.feedInfo["speed_scaling"][0]

                if self.robot_status == 9:
                    print("error")
                    self.dashboard.ClearError()
                    self.dashboard.DisableRobot()

            time.sleep(0.1)

    
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

    def mov(self, mode, pnt, blocking=False, dynParams=None):
        """
        Move the Dobot to point defined by pnt.\n
        Inputs:\n
        mode (str 'j'/'l')-> 'j' for MovJ and 'l' for MovL\n
        pnt (list)-> list containing the coordinates for the point the Dobot moves to [X,Y,Z,Rx,Ry,Rz]\n
        blocking (bol)-> whether to block the program until position is reached, i.e. do not run any code before the robot reaches the designated point\n
        dynParams (tuple)-> tuple of extra parameters for MovJ/MovL functions, e.g. mov('j', pnt_example, blocking=False, dynParams=('CP=0',)) Note the comma after, very important for one parameter\n
        Output:\n
        none
        """
        if (isinstance(mode, str) and isinstance(pnt, (list, np.ndarray))):
            if mode.lower() == 'j':
                if dynParams:
                    self.command.MovJ(*pnt, *dynParams)
                else:
                    self.command.MovJ(*pnt)
            elif mode.lower() == 'l':
                if dynParams:
                    self.command.MovL(*pnt, *dynParams)
                else:
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

    def wait_arrive(self, pnt):
        while True:
            time.sleep(0.7)
            pnt_distance = np.linalg.norm(np.array(self.pos.pos[:3])-np.array(pnt[:3]))
            #print(pnt_distance)
            if pnt_distance < 1.0:
                break
        
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
        
    def pick_n_place(self, pick_location, place_location, ref_h=105.0, intermediate_h=-77.0, pushdown=False, slowdown=False, picture=False, picture_location=None, picture_fit_parms=((None, None, None), (None, None, None)), robot=None, filename=''):
        """
        Picks up a component from the component tray in working area and puts it into the cell holder position. Can be used more generally for different pickup and drop off locations.\n
        Inputs:\n
        pick_location (list)-> list of [x,y,z,Rx]\n
        place_location (list)-> list of [x,y,z,Rx]\n
        ref_h (float)-> value of z (height) that the robot will bring the picked up component before going to place location\n
        intermediate_h (float)-> value of z (height) just before pick up location that the robot will go to (at default/full speed) before slowing down to pick up component\n
        pushdown (Boolean)-> True = will push down by 3.5 units (mm) after placing component, False = no push down after placing component\n
        Output: \n
        none
        """
        if slowdown:
            spd = 20
        else:
            spd = 100
        place_r = place_location[3]
        # move to above the component and then drop to above the working area tray
        self.mov('j', movetoheight(pick_location, ref_h))
        self.mov('l', movetoheight(pick_location, intermediate_h))
        # move to pickup component
        self.mov('l', pick_location)
        self.vacuum(True)
        self.wait_arrive(pick_location)
        time.sleep(0.5)
        # move to above the component
        self.mov('l', movetoheight(pick_location, ref_h), False, ("CP=80", "SpeedL={:d}".format(spd),))
        # move to above the place location
        if picture:
            self.mov('j', picture_location, False, ("CP=80", "SpeedJ={:d}".format(spd),))
            if pushdown:
                self.command.RelMovL(0, 0, 1.2, 0)
                self.wait_arrive(pnt_offset(picture_location, [0, 0, 1.2, 0]))
            else:
                self.wait_arrive(picture_location)
            #self.command.Sync()
            try:
                filepath = take_img('btm', filename)
                offset = find_outer_circle(filepath, picture_fit_parms[0][0], picture_fit_parms[0][1], picture_fit_parms[0][2], camera='btm')
                adjustment = cam_offset_to_robot(offset, robot)*-1 - self.camera_center_offset
                if np.linalg.norm(adjustment) < 1.9:
                    place_location = [place_location[i]-adjustment[i] for i in range(len(adjustment))]
            except:
                print("Camera failed. Skipping...")
        self.mov('j', movetoheight(place_location, ref_h), False, ("CP=80", "SpeedJ={:d}".format(spd)))
        self.mov('l', place_location, True, ("CP=0", "SpeedL={:d}".format(spd)))
        if pushdown:
            self.vacuum(False)
            time.sleep(0.1)
            self.command.RelMovL(0,0,-3.5,0)
        else:
            self.vacuum(False)
        #self.command.Sync()
        time.sleep(0.2)
        # after vacuum off, move up to reference height
        self.mov('l', movetoheight(place_location, ref_h), blocking=True)
        if picture:
            self.mov('l', picture_location, blocking=True)
            #self.command.Sync()
            try:
                filepath = take_img('top', filename)
                previous_top_img = find_latest_top_img(filepath)
                if previous_top_img:
                    similatiry_score = get_similarity(filepath, previous_top_img)
                    if similatiry_score < 100:
                        print('Possible missing component detected. Continue? (y/n, default y)')
                        response = input('')
                        if 'n' in response.lower():
                            raise Exception
                find_outer_circle(filepath, picture_fit_parms[1][0], picture_fit_parms[1][1], picture_fit_parms[1][2], camera='top')
                filepath = take_img('btm')
                offset = find_outer_circle(filepath, 100, 300, 100, 'btm') # recenter camera reference offset
                self.camera_center_offset = np.round(cam_offset_to_robot(offset, robot), decimals=2)*-1
            except:
                print("Camera failed. Skipping...")
            finally:
                self.wait_arrive(picture_location)

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
        Pick_loc[2] -= 8.3 
        Place_loc = get_pnt('Empty Tray Bin', self.coord)
        self.pick_n_place(pick_location=Pick_loc, place_location=Place_loc, ref_h=ref_h, intermediate_h=Pick_loc[2]+15.0, slowdown=True)
        
    def offset_camera_center(self, robot='', cam='btm') -> None:
        if not robot:
            if self.robot_id.lower() == "grip":
                robot = 'grip'
            elif self.robot_id.lower() == "crimp":
                robot = 'crimp'
            else:
                print("No robot ID detected, please use the robot arguement option.")
                return
        self.mov('j', get_pnt("Dobie "+robot.capitalize()+" Camera", self.coord), True)
        try:
            filepath = take_img(cam, "cam_centre_offset")
            offset = find_outer_circle(filepath, 100, 300, 100, camera=cam)
            self.camera_center_offset = np.round(cam_offset_to_robot(offset, robot), decimals=2)*-1
        except:
            print("Camera not working, camera center offset not updated.")
        finally:
            self.mov('j', get_pnt("Dobie "+robot.capitalize()+" Home", self.coord), True)

    def close(self):
        self.dashboard.DisableRobot()
        self.command.close()
        self.dashboard.close()
        self.Stop_Event.set()
        time.sleep(0.2)
        self.feedback.close()

    def __del__(self):
        self.close()