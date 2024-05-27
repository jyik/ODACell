import sys
import pandas as pd
import numpy as np
from data_analyzer import get_CE, get_capacity
import ax
sys.path.append(r"C:\Users\renrum\Desktop\code\MyBOmain")
sys.path.append(r"C:\Users\renrum\Desktop\code\MyBOmain\mybo")
from mybo.interface import register_results, add_trial, get_designs, cancel_trials
import botorch
AX_PATH = r"C:\Users\renrum\Desktop\code\MyBOmain\results\coSolv\coSolvents_202405\DWIT\seed28"
#print(botorch.__version__)
#print(ax.__version__)


#x_data = np.array([(144.51282564550638, 42.980256490409374, 119.67280972748995, 41.22462868690491, 48.47923666238785, 225.96579138189554, 149.18158296495676, 22.03905489295721), #13825
#                 (80.0,120.0,120.0,60.0,20.0,480.0,540.0,200.0), #31119
#                 (60.0, 800.0, 60.0, 200.0, 20.0, 380.0, 40.0, 160.0), #67845
#                 (120.0, 20.0, 420.0, 260.0, 20.0, 420.0, 340.0, 20.0), #89169
#                 (100.0,20.0,20.0,80.0,120.0,880.0,260.0,240.0), #24529
#                 (244.4731742143631, 257.4099451303482, 76.05094090104103, 236.28828302025795, 96.39550372958183, 118.72252635657787, 121.2811041623354, 40.05530849099159), #19606
#                 (121.00896798074245, 40.61293415725231, 85.66323667764664, 400.3726774826646, 62.89815157651901, 150.71825589984655, 263.4501587599516, 64.9626161903143), #22517
#                 (135.0470194593072,122.66373913735151,38.59358374029398,140.00867772847414,108.4718881174922,141.6660789400339,116.39864929020405,346.20439168065786), #52619
#                 (393.008622340858, 212.58415654301643, 89.22983519732952, 56.361302733421326, 91.68356377631426, 44.820028357207775, 45.4218965023756, 163.95326424390078) #13524
#])
#x_data = np.array([(220.0, 500.0, 200.0, 160.0, 0.0, 140.0, 0.0),# 40.0),
#               (60.0, 500.0, 220.0, 20.0, 0.0, 80.0, 100.0),#0.0),
#               (1000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),# 0.0),
#               (0.0, 0.0, 500.0, 60.0, 0.0, 0.0, 200.0),# 0.0),
#               (0.0, 0.0, 200.0, 100.0, 300.0, 0.0, 400.0),# 0.0),
#               (100.0, 0.0, 100.0, 60.0, 200.0, 0.0, 0.0)]) #60.0)])
#x_df = pd.DataFrame(x_data, columns=['x0_liclo4_dmso', 'x1_liclo4_tmp', 'x2_liclo4_acn', 'x3_liclo4_h2o', 'x4_litfsi_dmso', 'x5_litfsi_tmp', 'x6_litfsi_acn'])

#y_data = np.array([(0.349387, 0.976836, 280.098306), #13825
#                   (0.744751, 0.1, 0.000482), #31119
#                   (1.495091, 0.892077, 246.797444), #67845
#                   (0.789881, 0.748421, 167.737432), #89169
#                   (1.113798, 0.1, 0.780997), #24529
#                   (1.32016, 0.63269, 253.66658), #19606
#                   (2.45351, 0.1, 10.0), #22517
#                   (3.066768, 0.1, 10.0), #52619
#                   (1.00186, 0.343509, 197.354566) #13524
#])

#y_data = np.array([(0.349387, 3.976836, 2.124), #13825
#                   (0.544751, 0.9, -0.123), #31119
#                   (0.895091, 2.892077, 1.48), #67845
#                   (0.389881, 1.748421, 0.2), #89169
#                   (0.713798, 0.468, 0.780997), #24529
#                   (0.62016, 1.23269, 1.7) #19606
#])
#y_df = pd.DataFrame(y_data, columns=['aq_solvent_mol_percent', 'coulombic_eff', 'discharge_capacity'])
ce = get_CE('22588')
energy_density_discharge = get_capacity('22588')
#AX_PATH = r"C:\Users\renrum\Desktop\code\MyBOmain\results\coSolv\coSolvents_202402\DWIT\seed5"

opt_output_dic = {'y0': 'coulombic_eff', 'y1': 'discharge_capacity', 'y2': 'aq_solvent_mol_percent'}
#register_results([({opt_output_dic['y0']: ce, opt_output_dic['y1']: energy_density_discharge, opt_output_dic['y2']:0.0}, 10)], client_path=AX_PATH)

#opt_output_dic = {'y0': 'coulombic_eff', 'y1': 'discharge_energy_density', 'y2': 'aq_to_non_aq'}


#print(ce)
#print(energy_density_discharge)
register_results([({opt_output_dic['y0']: ce, opt_output_dic['y1']: energy_density_discharge, opt_output_dic['y2']: 0.24968514045077111}, 51)], client_path=AX_PATH)
#for i in [44,45]:
#    cancel_trial(i, client_path=AX_PATH)
#add_trial(x_df, y_df, client_path=AX_PATH)
#points = get_designs(6, client_path=AX_PATH)
#cancel_trials([48,], client_path=AX_PATH)

#print(ce)
#print(energy_density_discharge)