from logging import raiseExceptions
from multiprocessing.sharedctypes import Value
from typing import List

from dobot_class import Dobot
from dobot_api_v2 import *
from coordinate_funcs import *
import numpy as np
import pandas as pd
import time

set_speed = 40


class D_GRIP(Dobot):
    def __init__(self, ip_address):
        super().__init__(ip_address)
        self.update_default_speed(set_speed)
        self.dashboard.SpeedFactor(self.default_speed)
        #component tray status
        self.tray_status = [0,0,0,0,0,0]
        # load coordinates - cell components, stacks, and cycler/slide
        self.coord = get_coords('Grip')
        self.robot_id = 'grip'

    def update_coord(self):
        """
        Updates the coordinates - to be used when changes to the excel file is made.
        """
        self.coord = get_coords('Grip')
        
    def holder_to_slide(self, ref_h=62.0):
        """
        Transfers crimped cell from the cell holder to the slide for flipping.
        Drops cell into slide and is ready to pick up for cell cycling.\n
        """
        self.mov('j', movetoheight(get_pnt('Dobie Grip Component Placement in Active Site', self.coord), ref_h))
        self.mov('l', get_pnt('Dobie Grip Component Placement in Active Site', self.coord))
        self.command.RelMovL(0,0,-2.0) # Offset if needed
        self.vacuum(True)
        self.wait_arrive(pnt_offset(get_pnt('Dobie Grip Component Placement in Active Site', self.coord),[0, 0, -2.0, 0]))
        time.sleep(0.2)
        self.mov('l', movetoheight(get_pnt('Dobie Grip Component Placement in Active Site', self.coord), ref_h), True, ("CP=5", "SpeedL=5"))
        self.mov('j', movetoheight(get_pnt('Slide Drop Location', self.coord), ref_h), True, ("CP=100", "SpeedJ=100"))
        self.mov('l', get_pnt('Slide Drop Location', self.coord), True)
        time.sleep(0.1)
        self.vacuum(False)
        time.sleep(0.5)
        #Corrector for slide - not to be confused with corrector function below
        self.mov('l', get_pnt('Slide Corrector 1', self.coord))
        self.mov('l', get_pnt('Slide Corrector 2', self.coord))
        self.mov('l', get_pnt('Slide Corrector 3', self.coord), blocking=True)
        #self.command.Sync()

    def corrector(self):
        """
        !!!DEPRICATED!!!
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
        Ensures the vacuum is off and moves up from its current position to a reference height. Then rotates to the specified home position.\n
        Inputs:\n
        ref_h (float)-> reference height for safe movement.\n
        Outputs:\n
        None
        """
        if self.pos_theta > 67.5:
            self.vacuum(False)
            self.command.RelMovL(0, 0, 50.0 - self.pos.z)
            self.mov('j', movetoheight(get_pnt('Dobie Grip Home', self.coord), 50.0))
            self.mov('l', get_pnt('Dobie Grip Home', self.coord))
            self.grip(False)
            time.sleep(0.9)
            self.grip()
        else:
            self.vacuum(False)
            self.grip(False)
            self.command.RelMovL(0, 0, 7.0 - self.pos.z)
            self.grip()
            self.mov('j', movetoheight(get_pnt('Dobie Grip Home', self.coord), 7.0))
            self.mov('l', get_pnt('Dobie Grip Home', self.coord))
        self.wait_arrive(get_pnt('Dobie Grip Home', self.coord))

    def slide_to_cycler(self, cycler_id, ref_h=7.0):
        """
        Move cell from slide to cell cycling station.
        Assumes flip successful coin cell in vertical position.
        Input:\n
        cycler_id (str)-> name of cycler as defined in the excel file.\n
        Output:\n
        none
        """
        self.mov('j', movetoheight(get_pnt('Slide Pickup Location', self.coord), get_pnt('Slide Corrector 3', self.coord)[2]))
        self.grip(False)
        self.mov('l', get_pnt('Slide Pickup Location', self.coord), blocking=True)
        #self.command.Sync()
        time.sleep(0.5)
        self.grip()
        time.sleep(0.5)
        self.mov('l', movetoheight(get_pnt('Slide Pickup Location', self.coord), ref_h))
        cycler_pnt = get_pnt(cycler_id, self.coord)
        # move to above the specified cycler location
        self.mov('j', movetoheight(cycler_pnt, ref_h))
        self.mov('l', cycler_pnt, blocking=True)
        #self.command.Sync()
        time.sleep(0.5)
        self.grip(False)
        time.sleep(0.5)
        # move back up to above the specified cycler location
        self.mov('l', movetoheight(cycler_pnt, ref_h), True)
        #self.command.Sync()
        self.grip()
        self.mov('j', get_pnt("Dobie Grip Home", self.coord), True)

    def grip(self, state=True):
        if state:
            self.dashboard.DO(1,0)
        elif state==False:
            self.dashboard.DO(1,1)

    def remove_from_cycler(self, cycler_id, ref_h=7.0):
        """
        Removes cycled cell from cycler station and drops into the waste bin.\n
        Input:\n
        cycler_id (str)-> name of cycler as defined in the excel file.\n
        Output:\n
        none
        """
        self.mov('j', movetoheight(get_pnt(cycler_id, self.coord), ref_h))
        self.grip(False)
        self.mov('l', get_pnt(cycler_id, self.coord), blocking=True)
        #self.command.Sync()
        time.sleep(1)
        self.grip()
        time.sleep(0.75)
        self.mov('l', movetoheight(get_pnt(cycler_id, self.coord), ref_h))
        self.mov('j', movetoheight(get_pnt('Finished Cell Bin', self.coord), ref_h))
        self.mov('l', get_pnt('Finished Cell Bin', self.coord), blocking=True)
        self.grip(False)
        #self.command.Sync()
        time.sleep(0.2)
        self.grip()
        self.command.RelMovL(0, 0, 15)
        self.mov('j', get_pnt('Dobie Grip Home', self.coord), True)
        #self.command.Sync()
        
    def collect_neg_components(self, row_id, ref_h=45.0, filename=''):
        place_pnt = get_pnt('Dobie Grip Component Placement in Active Site', self.coord)
        self.pick_n_place(get_pnt('Cell {}: ano'.format(row_id), self.coord), place_pnt, ref_h, picture=True, picture_location=get_pnt('Dobie Grip Camera', self.coord), picture_fit_parms=((430, 445, 100), (260, 290, 100)), robot='grip', filename=filename)
        self.pick_n_place(get_pnt('Cell {}: space'.format(row_id), self.coord), place_pnt, ref_h, picture=True, picture_location=get_pnt('Dobie Grip Camera', self.coord), picture_fit_parms=((500, 545, 100), (260, 290, 100)), robot='grip', filename=filename)
        self.pick_n_place(get_pnt('Cell {}: N casing'.format(row_id), self.coord), place_pnt, ref_h, pushdown=True, picture=True, picture_location=get_pnt('Dobie Grip Camera', self.coord), picture_fit_parms=((645, 685, 100), (260, 290, 100)), robot='grip', filename=filename)
        self.mov('j', get_pnt('Dobie Grip Home', self.coord), True)

    def collect_separator(self, row_id, ref_h=45.0, filename=''):
        place_pnt = get_pnt('Dobie Grip Component Placement in Active Site', self.coord)
        self.pick_n_place(get_pnt('Cell {}: sep'.format(row_id), self.coord), place_pnt, ref_h, picture=True, picture_location=get_pnt('Dobie Grip Camera', self.coord), picture_fit_parms=((600, 700, 100), (260, 290, 100)), robot='grip', filename=filename)
        self.mov('j', get_pnt('Dobie Grip Home', self.coord), True)