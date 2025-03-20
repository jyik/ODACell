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
        self.RawInput("pipette_right.transfer("+str(volume)+", "+electrolyte_location+", cell_holder.wells()[0], new_tip='never', blow_out=True, blowout_location='destination well', mix_before=(2, 250), air_gap=20)")
        self.RawInput("pipette_right.drop_tip()")
        self.small_tip_index += 1
        time.sleep(2)
        self.RawInput("print('dispensed electrolyte for "+name_id+"')")
        check_1 = 0
        while True:
            otto_output = self.get_output()
            if isinstance(otto_output, str):
                #print(otto_output)
                #if otto_output[-4:] == '>>> ':
                if (name_id in otto_output) and check_1 == 1:
                    break
                if "print(" and name_id in otto_output:
                    check_1 += 1
            time.sleep(0.4)

    def prepare_electrolyte(self, stock_vol, electrolyte_location):
    
        #example stock_vol = [('0', 100), ('1', 200), ('2', 300)]
        stock_vol = [(key, value) for key, value in stock_vol if value != 0.0]
        print("OT 2 preparing electrolyte...")
        print(stock_vol)
        if all(19.999<=i[1]<=1800.0 for i in stock_vol):
            final_stock = stock_vol.pop()
            for well, vol in stock_vol:
                if 20.0 <= vol < 280.0:
                    self.RawInput("pipette_right.pick_up_tip(s_tiprack.wells()["+str(self.small_tip_index)+"])")
                    self.RawInput("pipette_right.transfer("+str(round(vol, 2))+", stock_solutions.wells()["+str(well)+"], "+electrolyte_location+", new_tip='never', air_gap=20)")
                    self.RawInput("protocol.delay(seconds=1)")
                    self.RawInput("pipette_right.move_to("+electrolyte_location+".top(z=-2))") 
                    self.RawInput("protocol.delay(seconds=2)")
                    self.RawInput("pipette_right.blow_out("+electrolyte_location+")")
                    self.RawInput("pipette_right.drop_tip()")
                    self.small_tip_index += 1
                elif 280.0 <= vol <= 900.0:
                    self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
                    self.RawInput("pipette_left.transfer("+str(round(vol, 2))+", stock_solutions.wells()["+str(well)+"], "+electrolyte_location+", new_tip='never', air_gap=100)")
                    self.RawInput("protocol.delay(seconds=1)")
                    self.RawInput("pipette_left.move_to("+electrolyte_location+".top(z=-2))") 
                    self.RawInput("protocol.delay(seconds=2)")
                    self.RawInput("pipette_left.blow_out("+electrolyte_location+")")
                    self.RawInput("pipette_left.drop_tip()")
                    self.large_tip_index += 1
                elif vol > 900.0:
                    if (vol - 800.0) < 20.0:
                        stock_vol.append((well, 700))
                        stock_vol.append((well, vol-700))
                    else:
                        stock_vol.append((well, 800))
                        stock_vol.append((well, vol-800))
                    
            if 20.0 <= final_stock[1] < 280.0:
                self.RawInput("pipette_right.pick_up_tip(s_tiprack.wells()["+str(self.small_tip_index)+"])")
                self.RawInput("pipette_right.transfer("+str(round(final_stock[1], 2))+", stock_solutions.wells()["+str(final_stock[0])+"], "+electrolyte_location+", new_tip='never', air_gap=20)")
                self.RawInput("protocol.delay(seconds=1)")
                self.RawInput("pipette_right.move_to("+electrolyte_location+".top(z=-2))") 
                self.RawInput("protocol.delay(seconds=2)")
                self.RawInput("pipette_right.blow_out("+electrolyte_location+")")
                self.RawInput("pipette_right.drop_tip()")
                self.small_tip_index += 1

                self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
                self.RawInput("pipette_left.mix(30, 1000, "+electrolyte_location+", 3.0)")
                self.RawInput("protocol.delay(seconds=1)")
                self.RawInput("pipette_left.move_to("+electrolyte_location+".top(z=-2))") 
                self.RawInput("protocol.delay(seconds=2)")
                self.RawInput("pipette_left.blow_out("+electrolyte_location+")")
                self.RawInput("pipette_left.drop_tip()")
                self.large_tip_index += 1
            elif 280.0 <= final_stock[1] <= 900.0:
                self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
                self.RawInput("pipette_left.transfer("+str(round(final_stock[1], 2))+", stock_solutions.wells()["+str(final_stock[0])+"], "+electrolyte_location+", new_tip='never', air_gap=100)")
                self.RawInput("pipette_left.mix(30, 1000, "+electrolyte_location+", 3.0)")
                self.RawInput("protocol.delay(seconds=1)")
                self.RawInput("pipette_left.move_to("+electrolyte_location+".top(z=-2))") 
                self.RawInput("protocol.delay(seconds=2)")
                self.RawInput("pipette_left.blow_out("+electrolyte_location+")")
                self.RawInput("pipette_left.drop_tip()")
                self.large_tip_index += 1
            elif final_stock[1] > 900.0:
                if (final_stock[1] - 800.0) < 20.0:
                    self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
                    self.RawInput("pipette_left.transfer("+str(700)+", stock_solutions.wells()["+str(final_stock[0])+"], "+electrolyte_location+", new_tip='never', air_gap=100)")
                    self.RawInput("protocol.delay(seconds=1)")
                    self.RawInput("pipette_left.move_to("+electrolyte_location+".top(z=-2))") 
                    self.RawInput("protocol.delay(seconds=2)")
                    self.RawInput("pipette_left.blow_out("+electrolyte_location+")")
                    self.RawInput("pipette_left.drop_tip()")
                    self.large_tip_index += 1
                    if (final_stock[1] - 700.0) < 280.0:
                        self.RawInput("pipette_right.pick_up_tip(s_tiprack.wells()["+str(self.small_tip_index)+"])")
                        self.RawInput("pipette_right.transfer("+str(round(final_stock[1]-700, 2))+", stock_solutions.wells()["+str(final_stock[0])+"], "+electrolyte_location+", new_tip='never', air_gap=20)")
                        self.RawInput("protocol.delay(seconds=1)")
                        self.RawInput("pipette_right.move_to("+electrolyte_location+".top(z=-2))") 
                        self.RawInput("protocol.delay(seconds=2)")
                        self.RawInput("pipette_right.blow_out("+electrolyte_location+")")
                        self.RawInput("pipette_right.drop_tip()")
                        self.small_tip_index += 1

                        self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
                        self.RawInput("pipette_left.mix(30, 1000, "+electrolyte_location+", 3.0)")
                        self.RawInput("protocol.delay(seconds=1)")
                        self.RawInput("pipette_left.move_to("+electrolyte_location+".top(z=-2))") 
                        self.RawInput("protocol.delay(seconds=2)")
                        self.RawInput("pipette_left.blow_out("+electrolyte_location+")")
                        self.RawInput("pipette_left.drop_tip()")
                        self.large_tip_index += 1
                    else:
                        self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
                        self.RawInput("pipette_left.transfer("+str(round(final_stock[1]-700, 2))+", stock_solutions.wells()["+str(final_stock[0])+"], "+electrolyte_location+", new_tip='never', air_gap=100)")
                        self.RawInput("pipette_left.mix(30, 1000, "+electrolyte_location+", 3.0)")
                        self.RawInput("protocol.delay(seconds=1)")
                        self.RawInput("pipette_left.move_to("+electrolyte_location+".top(z=-2))") 
                        self.RawInput("protocol.delay(seconds=2)")
                        self.RawInput("pipette_left.blow_out("+electrolyte_location+")")
                        self.RawInput("pipette_left.drop_tip()")
                        self.large_tip_index += 1
                else:
                    self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
                    self.RawInput("pipette_left.transfer("+str(800)+", stock_solutions.wells()["+str(final_stock[0])+"], "+electrolyte_location+", new_tip='never', air_gap=100)")
                    self.RawInput("protocol.delay(seconds=1)")
                    self.RawInput("pipette_left.move_to("+electrolyte_location+".top(z=-2))") 
                    self.RawInput("protocol.delay(seconds=2)")
                    self.RawInput("pipette_left.blow_out("+electrolyte_location+")")
                    self.RawInput("pipette_left.drop_tip()")
                    self.large_tip_index += 1
                    if (final_stock[1] - 800.0) < 280.0:
                        self.RawInput("pipette_right.pick_up_tip(s_tiprack.wells()["+str(self.small_tip_index)+"])")
                        self.RawInput("pipette_right.transfer("+str(round(final_stock[1]-800, 2))+", stock_solutions.wells()["+str(final_stock[0])+"], "+electrolyte_location+", new_tip='never', air_gap=20)")
                        self.RawInput("protocol.delay(seconds=1)")
                        self.RawInput("pipette_right.move_to("+electrolyte_location+".top(z=-2))") 
                        self.RawInput("protocol.delay(seconds=2)")
                        self.RawInput("pipette_right.blow_out("+electrolyte_location+")")
                        self.RawInput("pipette_right.drop_tip()")
                        self.small_tip_index += 1

                        self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
                        self.RawInput("pipette_left.mix(30, 1000, "+electrolyte_location+", 3.0)")
                        self.RawInput("protocol.delay(seconds=1)")
                        self.RawInput("pipette_left.move_to("+electrolyte_location+".top(z=-2))") 
                        self.RawInput("protocol.delay(seconds=2)")
                        self.RawInput("pipette_left.blow_out("+electrolyte_location+")")
                        self.RawInput("pipette_left.drop_tip()")
                        self.large_tip_index += 1
                    else:
                        self.RawInput("pipette_left.pick_up_tip(l_tiprack.wells()["+str(self.large_tip_index)+"])")
                        self.RawInput("pipette_left.transfer("+str(round(final_stock[1]-800, 2))+", stock_solutions.wells()["+str(final_stock[0])+"], "+electrolyte_location+", new_tip='never', air_gap=100)")
                        self.RawInput("pipette_left.mix(30, 1000, "+electrolyte_location+", 3.0)")
                        self.RawInput("protocol.delay(seconds=1)")
                        self.RawInput("pipette_left.move_to("+electrolyte_location+".top(z=-2))") 
                        self.RawInput("protocol.delay(seconds=2)")
                        self.RawInput("pipette_left.blow_out("+electrolyte_location+")")
                        self.RawInput("pipette_left.drop_tip()")
                        self.large_tip_index += 1
        else:
            print('Mixing volume exceeds OT2 range.')
            raise ValueError
        clear_cache = self.get_output()
    
    def get_mixing_volumes(self, init_molals, final_molals, molar_masses, densities, solvent_mass = 1.3):
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

        if (solvent_vol_to_transfer < 0.02) or (sum(volumes_to_transfer)+solvent_vol_to_transfer > 1.9) or (not all(0.020 < x < 1.0 for x in volumes_to_transfer)):
            print(init_molals)
            print(final_molals)
            print(densities)
            print(volumes_to_transfer)
            print(solvent_vol_to_transfer)
            raise ValueError
        else:
            return volumes_to_transfer+[solvent_vol_to_transfer]