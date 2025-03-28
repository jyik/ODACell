import sqlite3
import pandas as pd
import numpy as np
import os
import re
from scipy.special import logit
from tkinter.filedialog import askopenfilenames
from scipy.integrate import trapezoid
from datetime import datetime, timedelta
from sklearn import linear_model


def add_to_db(file='C:\DATA\data.db', cycler='astrol'):
    try: 
        conn = sqlite3.connect(file)
        cur = conn.cursor()
        print("Database Sqlite3.db formed.") 
    except: 
        print("Database Sqlite3.db not formed.")
    files = askopenfilenames()
    if isinstance(files, tuple):
        # load selected files
        local_dic = importCells([i.split('/')[-1] for i in files], [i for i in files])
        for file in local_dic:
            try:
                local_dic[file].to_sql(file.split('.')[0], conn)
            except ValueError:
                continue
        conn.commit()
        conn.close()
    elif isinstance(files, str):
        print('Import canceled; previously imported data files remain.')

def importCells(listLabels, listFilePath, include_start_rest=True, cycleState=True):
    if len(listFilePath) == len(listLabels):
        mydic = {}
        for i in range(len(listLabels)):
            dbtable = pd.read_csv(listFilePath[i], sep='\t', skiprows=1)
            dbtable.drop(labels=[re.search('Unnamed.*', i)[0] for i in dbtable.columns if re.search('Unnamed.*', i)], axis=1, inplace=True)
            dbtable.loc[dbtable.loc[(dbtable["Z1 []"] == 1) & (dbtable["I [mA]"].isna())].index, "Z1 []"] = 0
            if not include_start_rest:
                dbtable.drop(dbtable.loc[(dbtable["Z1 []"] == 0) & (dbtable["I [mA]"].isna())].index, axis='index', inplace=True)
            if cycleState:
                dbtable['State'] = dbtable.apply(lambda x: astrol_state_classifier(x, "I [mA]"), axis=1)
            mydic[listLabels[i]] = dbtable
        return mydic
    else:
        print("Error")

def classify_file(file_path):
    with open(file_path, 'r') as file:
        first_line = file.readline()
        if first_line.startswith('seqid,'):
            return 'NEWARE'
        else:
            return 'ASTROL'

def import_neware_data(listLabels, listFilePaths):
    cycle_sep = ['cc', 'cccv', 'cv']
    charge_steps = ['cc', 'cccv', 'cv']
    discharge_steps = ['dc', 'cccd', 'dv']
    am_mass = 0.00884 #grams
    new_table = pd.DataFrame()
    def process_group(group):
        # Drop the first 25 and last 180 rows of the group ## NEED TO BE ADJUSTED FOR EVERY APPLICATION
        if len(group) > 500:
            trimmed_group = group.iloc[25:-180]
        else:
            trimmed_group = group.iloc[10:-85]
        return trimmed_group['volt'].mean()

    for n in range(len(listLabels)):
        dbtable = pd.read_csv(listFilePaths[n], sep=',')
        indices = dbtable.index[dbtable['testtime'] == 0].tolist()
        start_index = indices[0]
        cycle_id = 0
        for i in range(len(indices)):
            if dbtable.loc[indices[i], 'steptype'] in cycle_sep:
                end_index = indices[i]
                dbtable.loc[start_index:end_index, 'Cycle'] = cycle_id
                start_index = indices[i]
                cycle_id += 1
        dbtable.loc[start_index:, 'Cycle'] = cycle_id
        dbtable['Cycle'] = dbtable['Cycle'].astype('int64')
    
        grouped = dbtable.groupby(['Cycle', 'steptype'])

        # Get Capacity for each cycle
        features = grouped['cap'].max().unstack()
        features = features.reset_index()
        # Get avg_volts for each cycle
        # Apply the processing function to compute the mean of column 'x' after trimming
        mean_volts = grouped.apply(process_group).unstack()
        mean_volts = mean_volts.reset_index()

        C_present = [col for col in charge_steps if col in features.columns]
        D_present = [col for col in discharge_steps if col in features.columns]
        
        # Takes the average voltage of the first charge/discharge step, if the major step is not the first step, change index to 1, or higher
        features['Charge Mean Voltage [V]'] = mean_volts[C_present[0]]
        features['Discharge Mean Voltage [V]'] = mean_volts[D_present[0]]

        features['Charge Capacity [mAh/g]'] = (features[C_present].sum(axis=1)*1000)/am_mass
        features['Discharge Capacity [mAh/g]'] = (features[D_present].sum(axis=1)*1000)/am_mass
        features['CE'] = features['Discharge Capacity [mAh/g]']/features['Charge Capacity [mAh/g]']
        features['Cell'] = listLabels[n]
        new_table = pd.concat([new_table, features], axis=0)
    return new_table


def astrol_state_classifier(row, current_name):
    try: 
        if re.search('.*New program step', row['Comment']):
            if row[current_name] > 0:
                return 'Discharge'
            else:
                return 'Charge'
        else:
            if row[current_name] > 0:
                return 'Charge'
            else:
                return 'Discharge'
    except TypeError:
        if row[current_name] >= 0:
            return 'Charge'
        else:
            return 'Discharge'

def dic_to_features(mydic):
    new_table = pd.DataFrame()
    for key in mydic:
        cell_data = mydic[key]
        cycles = cell_data.groupby('Z1 []')['C [Ah/kg]'].min().index.values.tolist()
        charge_cap = cell_data.groupby('Z1 []')['C [Ah/kg]'].max().values
        discharge_cap = cell_data.groupby('Z1 []')['C [Ah/kg]'].min().values*-1
        coulombic_eff = discharge_cap/charge_cap
        try:
            energy_density = cell_data.groupby(['Z1 []', 'State']).apply(lambda group: trapezoid(y=group['U [V]'], x=group['C [Ah/kg]']))
            cell_table = pd.DataFrame(data={'Cell': [key]*len(cycles), 'Cycle': cycles, 'Charge Capacity [mAh/g]': charge_cap, 'Discharge Capacity [mAh/g]': discharge_cap, 'CE': coulombic_eff, 'Charge Energy Densiy [mWh/g]': energy_density.values[energy_density.values > 0], 'Discharge Energy Density [mWh/g]': energy_density.values[energy_density.values < 0]*-1})
        except:
            cell_table = pd.DataFrame(data={'Cell': [key]*len(cycles), 'Cycle': cycles, 'Charge Capacity [mAh/g]': charge_cap, 'Discharge Capacity [mAh/g]': discharge_cap, 'CE': coulombic_eff, 'Charge Energy Densiy [mWh/g]': [max(energy_density.values)*-1]*len(cycles), 'Discharge Energy Density [mWh/g]': [min(energy_density.values)*-1]*len(cycles)})
        new_table = pd.concat([new_table, cell_table], axis=0)
        new_table['Cycle'] = new_table['Cycle'].astype('int64')
    return new_table

def search_dir(cell_id, rootdir='C:\\DATA', restricted=False):
    if not isinstance(cell_id, str):
        print("Please enter cell_id as a string.")
    else:
        matches = []
        regex = re.compile('.*_'+str(cell_id)+'_.*\\.(txt|csv)')
        for root, dirs, files in os.walk(rootdir):
            for file in files:
                if regex.match(file):
                    file_path = os.path.join(root, file)   
                    if restricted:
                        # Get the file modification timestamp
                        file_timestamp = os.path.getmtime(file_path)
                        # Calculate the current date minus 2 months
                        two_months_ago = datetime.now() - timedelta(days=60)
                        # Compare the file timestamp with the two months ago timestamp
                        if datetime.fromtimestamp(file_timestamp) >= two_months_ago:
                            matches.append(file_path)
                    else:
                        matches.append(file_path)
        return matches

def get_features(cell_ids):
    astrol_filenames = []
    neware_filenames = []
    if isinstance(cell_ids, str):
        matches = search_dir(cell_ids)
        if len(matches) > 1:
            print('Duplicates found: \n')
            [print(i) for i in matches]
            print('Using first instance: '+ matches[0])
        file_class = classify_file(matches[0])
        if file_class == 'NEWARE':
            neware_filenames.append(matches[0])
        elif file_class == 'ASTROL':
            astrol_filenames.append(matches[0])
    elif isinstance(cell_ids, list):
        for cell_id in cell_ids:
            matches = search_dir(cell_id)
            if len(matches) > 1:
                print('Duplicates found: \n')
                [print(i) for i in matches]
                print('Using first instance: '+ matches[0])
            file_class = classify_file(matches[0])
            if file_class == 'NEWARE':
                neware_filenames.append(matches[0])
            elif file_class == 'ASTROL':
                astrol_filenames.append(matches[0])
    if astrol_filenames:
        local_dic = importCells([i.split('\\')[-1] for i in astrol_filenames], astrol_filenames, include_start_rest=False, cycleState=True)
        astrol_features = dic_to_features(local_dic)
    if neware_filenames:
        neware_features = import_neware_data([i.split('\\')[-1] for i in neware_filenames], neware_filenames)
    try:
        all_features = pd.concat([astrol_features, neware_features], ignore_index=True, join='inner')
        return all_features
    except NameError:
        if astrol_filenames:
            return astrol_features
        elif neware_filenames:
            return neware_features

def get_CE(cell_ids, cycles=[6], avg=True):
    cycles_str = "Cycle == " + str(cycles[0])
    if len(cycles) > 1:
        for i in range(1, len(cycles)):
            cycles_str += '|' + 'Cycle == ' + str(cycles[i])
    all_features = get_features(cell_ids)
    if avg:
        outputCE = all_features.query(cycles_str).groupby('Cell').mean()['CE']
    else:
        outputCE = all_features.query(cycles_str)[['Cell', 'Cycle', 'CE']]
        outputCE.reset_index(drop=True, inplace=True)
        return outputCE
    if len(outputCE):
        ce = outputCE.values[0]
        if ce > 0.999998:
            ce = 0.999998
        return logit(ce)
    else:
        raise ValueError

def get_capacity(cell_ids, cycles=[6], avg=True, max_cap = 170.0, state='Discharge'):
    cycles_str = "Cycle == " + str(cycles[0])
    if len(cycles) > 1:
        for i in range(1, len(cycles)):
            cycles_str += '|' + 'Cycle == ' + str(cycles[i])
    all_features = get_features(cell_ids)
    if avg:
        outputEng = all_features.query(cycles_str).groupby('Cell').mean()[state+' Capacity [mAh/g]']
    else:
        outputEng = all_features.query(cycles_str)[['Cell', 'Cycle', state+' Capacity [mAh/g]']]
        outputEng.reset_index(drop=True, inplace=True)
        return outputEng
    if len(outputEng):
        cap = outputEng.values[0]/max_cap
        if cap < 0.0000001:
            print(cap)
            raise ValueError
        else:
            if cap >= 1.0:
                cap = 0.99999
            return logit(cap)
    else:
        raise ValueError

def get_avgV(cell_ids, cycles=[6], avg=True, state='Discharge'):
    cycles_str = "Cycle == " + str(cycles[0])
    if len(cycles) > 1:
        for i in range(1, len(cycles)):
            cycles_str += '|' + 'Cycle == ' + str(cycles[i])
    all_features = get_features(cell_ids)
    if avg:
        outputV = all_features.query(cycles_str).groupby('Cell').mean()[state+' Mean Voltage [V]']
        return outputV.values
    else:
        outputV = all_features.query(cycles_str)[['Cell', 'Cycle', state+' Mean Voltage [V]']]
        outputV.reset_index(drop=True, inplace=True)
        return outputV

def get_Doverpotential(cycles, voltages):
    """
    apply a fit to overpotential (Y) vs cycles (X) to get average change in overpotential per cycle\n
    Input:\n
    cycles (list) -> List of cycles (int)\n
    voltages (np.array) -> Corresponding average voltages for those cycles\n
    OutPut:\n
    delta_overpotential (float) -> slope of fit
    """
    # Remove any NaN from the dataset
    valid_indices = ~np.isnan(voltages)

    # Filter out the NaN values from y and the corresponding x values
    x_filtered = np.array(cycles)[valid_indices]
    y_filtered = voltages[valid_indices]

    # Least Squares Fit
    #slope, intercept = np.polyfit(x_filtered,y_filtered,1)
    #y_fit = slope*x_filtered+intercept
    #residuals = y_filtered-y_fit
    #variance=np.var(residuals)

    # Huber Fit
    hrfit = linear_model.HuberRegressor()
    hrfit.fit(x_filtered.reshape((len(x_filtered),1)), y_filtered)
    slope = hrfit.coef_[0]
    #intercept = hrfit.intercept_
    
    #print(f"Slope: {slope}")
    #print(f"Intercept: {intercept}")
    #print(f"Variance of residuals: {variance}")
    return slope

#print(get_CE(['08851'], avg=True).values)
#print(get_capacity('08851').values[0])
