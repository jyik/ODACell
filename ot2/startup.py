import opentrons.execute
import json

protocol = opentrons.execute.get_protocol_api('2.12')

labware_names = {}
#load regular labware
s_tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', location='11')
s_tiprack.set_offset(x=0.00, y=1.30, z=-0.10)
l_tiprack = protocol.load_labware('opentrons_96_tiprack_1000ul', location='7')
l_tiprack.set_offset(x=-0.90, y=1.30, z=-0.60)
stock_solutions = protocol.load_labware('nest_12_reservoir_15ml', location='4')
stock_solutions.set_offset(x=0.40, y=0.00, z=0.00)
wellplate_qcm = protocol.load_labware('nest_96_wellplate_2ml_deep', location='10')

wellplate_odacell = protocol.load_labware('nest_96_wellplate_2ml_deep', location='5')
wellplate_odacell.set_offset(x=0.50, y=1.00, z=0.60)

#load custom labware
with open('cellholder_wellplate.json') as labware_file:
    labware_def = json.load(labware_file)
cell_holder = protocol.load_labware_from_definition(labware_def, location='6')
cell_holder.set_offset(x=-1.10, y=0.60, z=0.10)

#pipettes
pipette_right = protocol.load_instrument('p300_single_gen2', mount='right', tip_racks=[s_tiprack])
pipette_left = protocol.load_instrument('p1000_single_gen2', mount='left', tip_racks=[l_tiprack])

#Set variable names for reference later
labware_names[11] = 'tiprack'
labware_names[4] = 'resevoir'
labware_names[6] = 'cell_holder'
labware_names[5] = 'wellplate_odacell'
labware_names[10] = 'wellplate_qcm'
labware_names['left'] = 'pipette_left'
labware_names['right'] = 'pipette_right'


protocol.home()
