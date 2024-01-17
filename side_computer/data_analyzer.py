import sqlite3
import pandas as pd
import numpy as np
import os
import re
from scipy.special import logit
from tkinter.filedialog import askopenfilenames
from scipy.integrate import trapezoid



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
    return new_table

def search_dir(cell_id, rootdir='C:\DATA'):
    if not isinstance(cell_id, str):
        print("Please enter cell_id as a string.")
    else:
        matches = []
        regex = re.compile('.*_'+str(cell_id)+'_.*.txt')
        for root, dirs, files in os.walk(rootdir):
            for file in files:
                if regex.match(file):
                    matches.append(root+'\\'+file)
        return matches

def get_features(cell_ids):
    filenames = []
    if isinstance(cell_ids, str):
        matches = search_dir(cell_ids)
        if len(matches) > 1:
            print('Duplicates found: \n')
            [print(i) for i in matches]
            print('Using first instance: '+ matches[0])
        filenames.append(matches[0])
    elif isinstance(cell_ids, list):
        for cell_id in cell_ids:
            matches = search_dir(cell_id)
            if len(matches) > 1:
                print('Duplicates found: \n')
                [print(i) for i in matches]
                print('Using first instance: '+ matches[0])
            filenames.append(matches[0])
    local_dic = importCells([i.split('\\')[-1] for i in filenames], filenames, include_start_rest=False, cycleState=True)
    all_features = dic_to_features(local_dic)
    return all_features

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
        if ce > 0.99998:
            ce = 0.99998
        return logit(ce)
    else:
        raise ValueError

def get_capacity(cell_ids, cycles=[6], avg=True, max_cap = 150.0, state='Discharge'):
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
        if cap < 0.1:
            raise ValueError
        else:
            if cap >= 1.0:
                cap = 0.99999
            return logit(cap)
    else:
        raise ValueError

#print(get_CE(['08851'], avg=True).values)
#print(get_capacity('08851').values[0])
