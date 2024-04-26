from logging import raiseExceptions
from multiprocessing.sharedctypes import Value
from typing import List

from dobot_api_v2 import *
from coordinate_funcs import *
from dobot_class import Dobot
import numpy as np
import pandas as pd
import time


class D_CRIMP(Dobot):
    def __init__(self, ip_address):
        super().__init__(ip_address)
        self.update_default_speed(20)
        self.dashboard.SpeedFactor(self.default_speed)
        if int(self.dashboard.RobotMode().split(',')[1][1]) == 4:
            self.dashboard.EnableRobot()
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
        self.dashboard.DO(10, 1)

    # Low Level API
    def crimp(self):
        """
        Function to start crimping. Turns on the Digital Output (DO) 1 to ON for 2.5 seconds then switches OFF.
        """
        self.dashboard.DO(1, 1)
        self.dashboard.wait(2500)
        self.dashboard.DO(1, 0)

    def wait_crimper(self):
        """
        Blocks and returns when crimping is finished
        """
        time.sleep(5) #Delay to make sure crimp has started
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
    def pickup_cellholder(self, ref_h=105.0):
        """
        Move Dobot to pickup cellholder from active site. 
        """
        self.mov('j', movetoheight(get_pnt('Dobie Crimp Outside Active Site - Unloaded', self.coord), ref_h))
        self.mov('l', get_pnt('Dobie Crimp Outside Active Site - Unloaded', self.coord))
        self.mov('l', get_pnt('Dobie Crimp Inside Active Site - Loaded', self.coord))
        self.command.RelMovL(0, 0, 6.5)
        for _ in range(10):
            self.command.RelMovL(0.1,0.3,0.2,('CP=0', 'AccL=100', 'SpeedL=100'))
            self.command.RelMovL(-0.1,-0.3,0.2,('CP=0', 'AccL=100', 'SpeedL=100'))
        self.mov('l', get_pnt('Dobie Crimp Above Active Site - Loaded', self.coord), blocking=True)
        #self.command.Sync()
    
    def get_electrolyte(self, cell_holder='Active Site'):
        """
        Move Dobot to outside Otto with cell holder and then inside Otto for getting electrolyte.
        """
        if cell_holder=='Active Site':
            self.pickup_cellholder()
        self.mov('j', get_pnt('Dobie Crimp outside Otto', self.coord))
        self.mov('l', get_pnt('Dobie Crimp Inside Otto', self.coord), blocking=True)
        #self.command.Sync()
    
    def leave_otto(self, return_cellholder='Active Site'):
        """
        Move to Intermediate point before returning cell holder (run after get_electrolyte()).
        """
        self.mov('l', get_pnt('Dobie Crimp outside Otto', self.coord))
        if return_cellholder=='Active Site':
            self.return_cellholder()

    def load_crimper(self, cell_holder='Active Site'):
        """
        Move Dobot to in front of Crimper (loaded) -> drop cell holder into Crimper hole -> in front of Crimper (unloaded)
        """
        if cell_holder=='Active Site':
            self.pickup_cellholder()
        self.mov('j', get_pnt('Dobie Crimp Crimping Intermediate', self.coord))
        self.mov('j', get_pnt('Dobie Crimp in Front of Crimper - Loaded', self.coord), blocking=True)
        self.dashboard.SpeedFactor(15)
        self.mov('l', get_pnt('Dobie Crimp Over Crimper Hole - Loaded', self.coord))
        self.mov('l', get_pnt('Dobie Crimp Over Crimper Hole - Unloaded', self.coord))
        self.mov('l', get_pnt('Dobie Crimp in Front of Crimper - Unloaded', self.coord), blocking=True)
        self.dashboard.SpeedFactor(self.default_speed)
        self.mov('j', get_pnt('Dobie Crimp Crimping Intermediate', self.coord), blocking=True)
        
    def unload_crimper(self, return_cellholder='Active Site'):
        if np.linalg.norm(self.pos.pos[:-1]-np.array(get_pnt('Dobie Crimp in Front of Crimper - Unloaded', self.coord))[:-1])>50:
            self.home()
            #self.mov('j', get_pnt('Dobie Crimp Crimping Intermediate', self.coord))
        self.mov('j', get_pnt('Dobie Crimp in Front of Crimper - Unloaded', self.coord))
        self.dashboard.SpeedFactor(15)
        self.mov('l', get_pnt('Dobie Crimp Over Crimper Hole - Unloaded', self.coord))
        self.command.RelMovL(0,0,6.0,0)
        for _ in range(10):
            self.command.RelMovL(0.1,-0.3,0.3,('CP=0', 'AccL=100', 'SpeedL=100'))
            self.command.RelMovL(-0.1,0.3,0.3,('CP=0', 'AccL=100', 'SpeedL=100'))
            self.command.RelMovL(0,0,-0.15,('CP=0', 'AccL=100', 'SpeedL=100'))
        self.mov('l', get_pnt('Dobie Crimp Over Crimper Hole - Loaded', self.coord))
        self.mov('l', get_pnt('Dobie Crimp in Front of Crimper - Loaded', self.coord))
        self.dashboard.SpeedFactor(self.default_speed)
        self.mov('j', get_pnt('Dobie Crimp Crimping Intermediate', self.coord))
        if return_cellholder=='Active Site':
            self.return_cellholder()

 
    def return_cellholder(self, ref_h=105.0):
        """
        Move Dobot to outside of Otto (loaded) -> inside Otto (loaded) -> drop cell holder into holder in Otto -> outside Otto (unloaded)
        """
        self.mov('j', get_pnt('Dobie Crimp Above Active Site - Loaded', self.coord))
        self.dashboard.SpeedFactor(15)
        self.mov('l', get_pnt('Dobie Crimp Inside Active Site - Loaded', self.coord))
        self.mov('l', get_pnt('Dobie Crimp Outside Active Site - Unloaded', self.coord))
        self.dashboard.SpeedFactor(self.default_speed)
        self.command.RelMovL(0, 0, ref_h-get_pnt('Dobie Crimp Outside Active Site - Unloaded', self.coord)[2])
        self.loaded_state[0] = False
        self.mov('j', get_pnt('Dobie Crimp Home', self.coord), blocking=True)

    def home(self):
        """
        Moves Dobot to above coin cell component holder position.\n
        \nFirst moves Dobot closer to the origin keeping constant angle, until the radius is the same as the rotation radius for moving between Crimper and Otto.
        Then rotates to outside Otto (loaded). 
        """
        self.vacuum(False)
        home_pnt = get_pnt('Dobie Crimp Home', self.coord)
        # calculate radius we want to move to
        target_r = get_r(*home_pnt[0:2])
        # move up to reference height first
        #self.command.Sync()
        self.command.RelMovL(0, 0, home_pnt[2]-self.pos.z)
        # decrease radius with same angle until radius same as target_r (using MovL)
        moveto_pnt = get_xy(target_r, self.pos_theta)
        moveto_pnt.extend(home_pnt[2:])
        self.mov('l', moveto_pnt)
        # rotate to desired 'home' position
        self.mov('j', get_pnt('Dobie Crimp Home', self.coord), blocking=True)
        #self.command.Sync()

    def collect_pos_components(self, row_id, ref_h=50.0, filename=''):
        place_pnt = get_pnt('Dobie Crimp Component Placement in Active Site', self.coord)
        self.pick_n_place(get_pnt('Cell {}: P casing'.format(row_id), self.coord), place_pnt, ref_h, picture=True, picture_location=get_pnt('Dobie Crimp Camera', self.coord), picture_fit_parms=((650, 720, 100), (260, 290, 100)), robot='crimp', filename=filename)
        self.pick_n_place(get_pnt('Cell {}: cath'.format(row_id), self.coord), place_pnt, ref_h, picture=True, picture_location=get_pnt('Dobie Crimp Camera', self.coord), picture_fit_parms=((500, 590, 100), (260, 290, 100)), robot='crimp', filename=filename)
        self.home()