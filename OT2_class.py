from logging import raiseExceptions
from multiprocessing.sharedctypes import Value
from typing import List

import paramiko
import numpy as np

import time

import re

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
        time.sleep(1)
        self.ssh_channel.send(str(cmd+"\n").encode())
        time.sleep(1)
        #output_str = self.get_output()
        #if isinstance(output_str, str):
        #    print(output_str)
    
    def odacell_dispense_electrolyte(self, electrolyte_location, volume, name_id=""):
        """
        Otto gets electrolyte from a well and dispenses it to the cell holder.
        A new tip will be picked up each time this function is run and will be dropped into the trash at the end of the function. Otto will then home.\n
        Inputs:\n
        electrolyte_location (str)-> full name of the python-defined well location (i.e. "wellplate_odacell.wells()[0]")\n
        volume (int)-> volume of liquid to transfer in uL.\n
        Example code: otto.odacell_dispense_electrolyte("wellplate_odacell.wells()[0]", 70)\n
        Output:\n
        none but the outputs will be printed.
        """
        clear_cache = self.get_output()
        self.RawInput("pipette_right.pick_up_tip(s_tiprack.wells()["+str(self.small_tip_index)+"])")
        self.RawInput("pipette_right.transfer("+str(volume)+", "+electrolyte_location+", cell_holder.wells()[0], new_tip='never', blow_out=True, blowout_location='destination well')")
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

    def prepare_electrolyte(self, stock_wells, transfer_volumes, electrolyte_location):
        # NEEDS TO BE UPDATED; NOT WORKING!
        #dilution_factors = [liquid[1]/stock_solutions[stock_solutions.index(n)][-1] for liquid in electrolyte_comp[1:] for n in stock_solutions if liquid[0] in n]
        #stock_ids = [n[0] for liquid in electrolyte_comp[1:] for n in stock_solutions if liquid[0] in n]
        #transfer_volumes = [i * electrolyte_comp[0] for i in dilution_factors]
        #solvent_volume = electrolyte_comp[0] - np.sum(transfer_volumes)


        for v in transfer_volumes:
            if v < 20 or v > 1000:
                raise ValueError
        final_vol = transfer_volumes.pop()
        final_well = stock_wells.pop()
        for i, vol in zip(stock_wells, transfer_volumes):
            if 20 <= vol <= 300:
                self.RawInput("pipette_right.pick_up_tip(s_tiprack.wells()["+str(self.small_tip_index)+"])")
                self.RawInput("pipette_right.transfer("+str(round(vol, 2))+", stock_solutions.wells()["+str(i)+"], "+electrolyte_location+", new_tip='never')")
                self.RawInput("pipette_right.drop_tip()")
                self.small_tip_index += 1
            elif vol > 300:
                self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
                self.RawInput("pipette_left.transfer("+str(round(vol, 2))+", stock_solutions.wells()["+str(i)+"], "+electrolyte_location+", new_tip='never')")
                self.RawInput("pipette_left.drop_tip()")
                self.large_tip_index += 1
                
        if 20 <= final_vol <= 300:
            self.RawInput("pipette_right.pick_up_tip(s_tiprack.wells()["+str(self.small_tip_index)+"])")
            self.RawInput("pipette_right.transfer("+str(round(final_vol, 2))+", stock_solutions.wells()["+str(final_well)+"], "+electrolyte_location+", new_tip='never', mix_after=(9,275))")
            self.RawInput("pipette_right.drop_tip()")
            self.small_tip_index += 1
        elif final_vol > 300:
            self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
            self.RawInput("pipette_left.transfer("+str(round(final_vol, 2))+", stock_solutions.wells()["+str(final_well)+"], "+electrolyte_location+", new_tip='never', mix_after=(9,800))")
            self.RawInput("pipette_left.drop_tip()")
            self.large_tip_index += 1
        
        self.odacell_well_index += 1
        clear_cache = self.get_output()
    
    def get_mixing_volumes(self, init_molals, final_molals, molar_masses, densities, solvent_mass = 0.95):
        """
        Calculates the volumes required to create an electrolyte.\n
        Inputs:\n
        init_molals (list/iterable)-> list of stock concentrations in molal (m), e.g. [2.0, 0.5, 0.50]
        final_molals (list/iterable)-> list of electrolyte component concentrations in molal. The first element is the conducting salt, the ones after are additives, e.g. [1.5, 0.02, 0.02]
        molar_masses (list/iterable)-> list of stock molar masses of salt/additive corresponding to concentrations in g/mol, e.g. [106.39, 109.94, 68.946]
        densities (list/iterable)-> list of stock densities in g/mL. The last element is the density of only solvent (no salt/additives, pure), e.g. [1.8, 1.13, 1.41, 1.00]
        solvent_mass (float)-> grams (g) of solvent in the new electrlyte composition. Keep around 1.0, e.g. 0.95
        """
        init_solvent_masses = [final_molal*solvent_mass/init_molal for final_molal, init_molal in zip(final_molals, init_molals)]
        volumes_to_transfer = [(init_molal*molar_mass+1000)*init_solvent_mass/density/1000 for init_molal,molar_mass,init_solvent_mass,density in zip(init_molals, molar_masses, init_solvent_masses, densities[:-1])]
        solvent_vol_to_transfer = (solvent_mass - sum(init_solvent_masses))/densities[-1]

        if (solvent_vol_to_transfer < 0.02) or (sum(volumes_to_transfer)+solvent_vol_to_transfer > 1.0) or (not all(0.020 < x < 1.0 for x in volumes_to_transfer)):
            raise ValueError
        else:
            return volumes_to_transfer+[solvent_vol_to_transfer]