import duckdb
from qt_ui import new_material_gui, add_job_gui, stock_solutions_gui
#from background_processes import myround
import sys
import polars as pl
import random
import pickle
from PyQt5.QtWidgets import QApplication

database_name = 'ZnCu_ZnCl-TU-SDS-NHP.duckdb'

def create_DB():
    """
    Run once and never again. Creates the database structure for metadata of ODACell.
    """
    try:
        con = duckdb.connect(database_name)
        con.sql(r"""CREATE TABLE coinCells(
        Status INTEGER NOT NULL DEFAULT 0, 
        ID VARCHAR(5) PRIMARY KEY CHECK(ID ~ '^[0-9]{5}$'), 
        Electrolyte_ID INTEGER, 
        Solvent_Material_ID INTEGER,
        Electrode1_ID INTEGER, 
        Electrode2_ID INTEGER,
        Opt_Client VARCHAR(255),
        Trial INTEGER)""")
        con.sql(r"""CREATE TABLE electrolyteWells(
        Electrolyte_ID INTEGER PRIMARY KEY, 
        DateMixed DATETIME DEFAULT CURRENT_DATE, 
        Active BOOLEAN DEFAULT TRUE, 
        Well INTEGER CHECK(Well<97),  
        currentVolume INTEGER)""")
        con.sql(r"""CREATE TABLE electrolyteComp(
        Electrolyte_ID INTEGER,
        Material_Name VARCHAR(255),
        Material_ID INTEGER,
        Material_molar_conc DOUBLE)""")
        con.sql(r"""CREATE TABLE stockSolutions(
        wellPosition INTEGER,
        Solvent_Material_ID INTEGER,
        Solvent_Name VARCHAR(255),
        Component1_Material_ID INTEGER,
        Component1_Name VARCHAR(255), 
        Component1_molar_conc DOUBLE,
        Density_gmL DOUBLE,
        Volume_uL DOUBLE)""")
    #   con.sql(r"""CREATE TABLE Electrodes(
    #    Electrode_ID INTEGER PRIMARY KEY,
    #    Material_ID INTEGER,
    #    activeMaterial VARCHAR(255), 
    #    activeMaterial_Content DOUBLE, 
    #    specificCapacity_mAh_g DOUBLE, 
    #    nominalVoltage DOUBLE, 
    #    currentCollector VARCHAR(255), 
    #    areaCapacity_mAh_cm2 DOUBLE, 
    #    electrode_AM_mass_mg DOUBLE, 
    #    electrode_size_mm INTEGER)""")
        con.sql(r"""CREATE TABLE Materials(
        Material_ID INTEGER PRIMARY KEY,
        Name VARCHAR(255),
        Supplier VARCHAR(255),
        DateObtained DATETIME DEFAULT CURRENT_DATE,
        molarMass_gmol DOUBLE)""")
    except:
        pass
    finally:
        # explicitly close the connection
        con.close()

def dispense_electrolyte(elec_id, dispense_vol=45):
    """
    Keeps well volume correct after dispensing electrolyte and also deactivates well after certain volume is reached\n
    Inputs:\n
    elec_id (int) -> Electrolye_ID corresponding to the well that OT2 is dispensing from\n
    Outputs:\n
    None
    """
    con = duckdb.connect(database_name)
    well_and_currentVol = con.execute("SELECT Well, currentVolume FROM electrolyteWells WHERE Electrolyte_ID = ?;", [elec_id]).fetchall()[0]
    con.execute("UPDATE electrolyteWells SET currentVolume = currentVolume - ? WHERE Electrolyte_ID = ?;", [dispense_vol, elec_id])
    newVol = con.execute("SELECT currentVolume FROM electrolyteWells WHERE Electrolyte_ID = ?;", [elec_id]).fetchall()[0][0]
    print("Electrlyte ID {} in Well {}: Volume changed from {} uL to {} uL.".format(elec_id, *well_and_currentVol, newVol))
    if newVol < 70:
        con.execute("UPDATE electrolyteWells SET Active = FALSE WHERE Electrolyte_ID = ?;", [elec_id])
        print("Well {} is now empty - removing from Active list.".format(well_and_currentVol[0]))
    con.close()

def get_electrolyte(current_well, query_component_list, total_vol):
    """
    Given a component list (see below for acceptable format), returns the Electrolyte_ID and Well. If electrolyte does not exist, it creates it.\n
    Inputs:\n
    current_well (int) -> next empty well in case electrolyte needs to be created\n
    query_component_list (list) -> list of tuples for Material_ID, Material_Name, and molar concentration of component, Material_molar_conc, of the electrolyte. Example: [(1, 'test1', 2.1), (2, 'test2', 0.4), (3, 'test3', 1.2)]\n
    total_vol (int) -> if the electrolyte needs to be mixed, what will the volume inside the well be\n
    Outputs:\n
    elec_id_and_well (list) -> returns a list containing two integers, Electrolyte_ID and Well of the query component
    """
    con = duckdb.connect(database_name)
    results = con.execute("SELECT Electrolyte_ID FROM electrolyteComp WHERE Material_ID = ? AND Material_Name = ? AND Material_molar_conc = ?", query_component_list[0]).fetchall()
    if results:
        for electrolyte in results:
            test_list = con.execute("SELECT Material_ID, Material_Name, Material_molar_conc FROM electrolyteComp WHERE Electrolyte_ID = ?", [electrolyte[0]]).fetchall()
            if set(test_list) == set(query_component_list):
                id_well = con.execute("SELECT Electrolyte_ID, Well FROM electrolyteWells WHERE Electrolyte_ID = ? AND Active = TRUE", [electrolyte[0]]).fetchone()
                if id_well:
                    con.close()
                    return [*id_well]
    if con.sql("SELECT MAX(Electrolyte_ID) FROM electrolyteWells").fetchall()[0][0]:
        elec_id = con.sql("SELECT MAX(Electrolyte_ID) FROM electrolyteWells").fetchall()[0][0] + 1
    else:
        elec_id = 1
    con.execute("INSERT INTO electrolyteWells (Electrolyte_ID, Well, currentVolume) VALUES (?, ?, ?);", [elec_id, current_well, total_vol])
    con.executemany("INSERT INTO electrolyteComp (Electrolyte_ID, Material_ID, Material_name, Material_molar_conc) VALUES (?, ?, ?, ?)", [(elec_id,)+comp for comp in query_component_list])
    con.close()
    return [elec_id, current_well]

def change_coinCell_status(status, name_id):
    con = duckdb.connect(database_name)
    con.execute("UPDATE coinCells SET Status = ? WHERE ID = ?;", [status, name_id])
    con.close()

def add_new_material():
    """
    Add new material into the database\n
    Inputs:\n
    text based gui inputs\n
    Outputs:\n
    None\n
    """
    con = duckdb.connect(database_name)
    if con.execute("SELECT MAX(Material_ID) FROM Materials").fetchall()[0][0]:
        mat_id = con.execute("SELECT MAX(Material_ID) FROM Materials").fetchall()[0][0]+1
    else:
        mat_id = 1
    app = QApplication(sys.argv)
    w = new_material_gui(mat_id)
    w.show()
    app.exec_()
    if w.result():
        con.execute("INSERT INTO Materials (Material_ID, Name, Supplier, molarMass_gmol, DateObtained) VALUES (?, ?, ?, ?, ?);", w.collect_variables())
    con.close()

# To remove/update
#def get_job(con):
#    app = QApplication(sys.argv)
#    w = add_job_gui(con)
#    w.show()
#    app.exec_()
#    if w.result():
#        return w.outputs()

def update_stock():
    """
    Updates initial stock solutions for mixing. GUI based - only selects from existing materials from Materials table in the database. Use the add_new_material() function to add the desired materials before changing the stock solutions.
    """
    con = duckdb.connect(database_name)
    app = QApplication(sys.argv)
    w = stock_solutions_gui(con)
    w.show()
    app.exec_()
    con.close()

def print_table(tableName):
    """
    Prints database table into terminal.
    """
    con = duckdb.connect(database_name)
    try:
        con.table(tableName).show()
    except duckdb.CatalogException as e:
        print(e)
    finally:
        con.close()

def get_job():
    con = duckdb.connect(database_name)
    try:
        cell_id, elec_id = con.execute("SELECT ID, Electrolyte_ID FROM coinCells WHERE Status == 0").fetchone()
    except TypeError:
        raise TypeError
    well_id = con.execute("SELECT Well FROM electrolyteWells WHERE Electrolyte_ID = ? AND Active = TRUE", [elec_id]).fetchone()[0]
    con.close()
    return cell_id, elec_id, well_id

def get_mixing_volumes(stock_wells, final_molarConcs, well_volume = 1300, solvent_well='11'):
    """
    Calculates the volumes required to create an electrolyte.\n
    Inputs:\n
    stock_wells (list/iterable)-> list of strings that must be same length as init_molarConcs. Indicates which stock concentration corresponds to which well in the stock solutions well, e.g. ['0', '2', '3'] Note the final well, '11' is reserved for pure solvent.\n
    final_molarConcs (list/iterable)-> list of desired electrolyte component molar concentrations in the final mixture. Length should be same as stock concentrations, e.g. [1.5, 0.02, 0.02]\n
    well_volume (float)-> volume (uL) of the new electrlyte composition in the well. Keep below 1600 uL but above 1000 uL (since mixing is done with 1.0 mL by default), e.g. 1300\n
    Outputs:\n
    volumes_to_transfer (list/iterable)-> list of tuples with each well and volume (uL) from stock solutions needed to get desired concentrations, e.g.[('0', 100), ('1', 200), ('2', 300)]
    """
    # Check parameter lengths are the same
    if len(final_molarConcs) != len(stock_wells):
        print('Lengths of parameters do not match.')
        raise ValueError
    # Get initial molar concentrations of each stock solution
    con = duckdb.connect(database_name)
    init_molarConcs = [con.execute("SELECT Component1_molar_conc FROM stockSolutions WHERE wellPosition = ?", [w]).fetchone()[0] for w in stock_wells]
    # Calculate desired volumes of each stock solution
    volumes_to_transfer = [final_molarConc*well_volume/init_molarConc for init_molarConc, final_molarConc in zip(init_molarConcs, final_molarConcs)]
    # Calculate volume of pure solvent required to bring the final volume up to well_volume
    solvent_vol_to_transfer = well_volume - sum(volumes_to_transfer)


    # Check none of the volumes will produce an error
    if (solvent_vol_to_transfer < 0) or (not all(x < 1000 for x in volumes_to_transfer)):
        print(volumes_to_transfer)
        print(solvent_vol_to_transfer)
        print('One or several volumes out of bounds')
        raise ValueError
    else:
        return [(w, myround(v, 0.1)) for w, v in zip(stock_wells, volumes_to_transfer)]+[(solvent_well, myround(solvent_vol_to_transfer, 0.1))]
    
def get_composition(stock_wells, final_molarConcs):
    """
    Gets the Material identification for the electrolyte components (for use with get_electrolyte).\n
    Inputs:\n
    stock_wells (list/iterable)-> list of strings that must be same length as init_molarConcs. Indicates which stock concentration corresponds to which well in the stock solutions well, e.g. ['0', '2', '3'] Note the final well, '11' is reserved for pure solvent.\n
    final_molarConcs (list/iterable)-> list of desired electrolyte component molar concentrations in the final mixture. Length should be same as stock concentrations, e.g. [1.5, 0.02, 0.02]\n
    Outputs:\n
    query_component_list (list/iterable)-> list of tuples with Material_ID, Material_Name, and molar concentration of each component in the electrolyte, e.g. [(1, 'test1', 2.1), (2, 'test2', 0.4), (3, 'test3', 1.2)]
    """
    con = duckdb.connect(database_name)
    material_id = [con.execute("SELECT Component1_Material_ID, Component1_Name FROM stockSolutions WHERE wellPosition = ?", [w]).fetchone() for w in stock_wells]
    query_component_list = [(*material, value) for material, value in zip(material_id, final_molarConcs)]
    con.close()
    return query_component_list

def volConc_to_mol(wellVol_list):
    """
    DEPRECATED\n
    Converts molal concentration to moles for each component in the electrolyte.\n
    """
    con = duckdb.connect(database_name)
    mol_comp = {}
    for i in wellVol_list:
        solution = con.execute("SELECT Solvent_Material_ID, Component1_Material_ID, Component1_Conc_molal, Density_gmL FROM stockSolutions WHERE wellPosition = ?", [i[0]]).fetchone()
        if None in solution:
            num_mols = solution[3]*i[1]/1000/con.execute("SELECT molarMass_gmol FROM Materials WHERE Material_ID = ?", [solution[0]]).fetchone()[0]
            try:
                mol_comp[solution[0]] += num_mols
            except KeyError:
                mol_comp[solution[0]] = num_mols
        else:
            total_mass = solution[3]*i[1]/1000
            solute_molarMass = con.execute("SELECT molarMass_gmol FROM Materials WHERE Material_ID = ?", [solution[1]]).fetchone()[0]
            solvent_molarMass = con.execute("SELECT molarMass_gmol FROM Materials WHERE Material_ID = ?", [solution[0]]).fetchone()[0]
            solute_mass = total_mass*(solution[2]*solute_molarMass/(solution[2]*solute_molarMass + 1000))
            solvent_mass = total_mass - solute_mass
            solute_mol = solute_mass/solute_molarMass
            solvent_mol = solvent_mass/solvent_molarMass
            for mat, val in [(solution[0], solvent_mol), (solution[1], solute_mol)]:
                try:
                    mol_comp[mat] += val
                except KeyError:
                    mol_comp[mat] = val
    #reformat
    mol_comp_list = [(n, con.execute("SELECT Name FROM Materials WHERE Material_ID = ?", [n]).fetchone()[0], mol_comp[n]) for n in mol_comp]
    con.close()
    return mol_comp_list

def add_coinCell(id, electrolyte_id, solvent_id, electrode_ids, trial, optimizer='batterydemo\\NEVHI_42'):
    """
    Adds a sample to the coinCells table in the database.\n
    Inputs:\n
    id (str) -> unique identifier for the cell\n
    electrolyte_id (int) -> Electrolyte_ID corresponding to the ID from electrolyteWells/electrolyteComp table for the cell\n
    solvent_id (int) -> Material_ID corresponding to the solvent used in the electrolyte\n
    electrode_ids (list) -> list of Material_IDs for the electrodes used in the cell\n
    trial (int) -> trial number for the cell\n
    optimizer (str) -> name of the primary optimization client this sample will be part of\n
    Outputs:\n
    None
    """
    con = duckdb.connect(database_name)
    con.execute("INSERT INTO coinCells (ID, Electrolyte_ID, Solvent_Material_ID, Electrode1_ID, Electrode2_ID, Opt_Client, Trial) VALUES (?, ?, ?, ?, ?, ?, ?)", [id, electrolyte_id, solvent_id, electrode_ids[0], electrode_ids[1], optimizer, trial])
    con.close()

def get_trial_id(name_id):
    """
    Returns the trial number and optimization client for a given cell ID.\n
    Inputs:\n
    name_id (str) -> unique identifier for the cell\n
    Outputs:\n
    client_trial (tuple) -> tuple containing the optimization client and trial number for the cell
    """
    con = duckdb.connect(database_name)
    client_trial = con.execute("SELECT Opt_Client, Trial FROM coinCells WHERE ID = ?", [name_id]).fetchone()
    con.close()
    return client_trial

def aq_solv_percent(name_id):
    """
    DEPRECATED\n
    Returns the percentage of aqueous solvent in the electrolyte.\n
    """
    try:
        con = duckdb.connect(database_name)
        elec_id = con.execute("SELECT Electrolyte_ID FROM coinCells WHERE ID = ?", [name_id]).fetchone()[0]
        h20_comp = con.execute("SELECT Material_mol FROM electrolyteComp WHERE Electrolyte_ID = ? AND LOWER(Material_Name) = 'h2o'", [elec_id]).fetchall()
        mol_h2o = sum([i[0] for i in h20_comp])
        #non_aq_solvent_list = ['dmso', 'acetonitrile', 'trimethyl phosphate']
        solvents_list = ['dmso', 'acetonitrile', 'trimethyl phosphate', 'h2o']
        #non_aq_str = '('+' OR '.join(["LOWER(Material_Name) = '"+i+"'" for i in non_aq_solvent_list])+')'
        solvents_str = '('+' OR '.join(["LOWER(Material_Name) = '"+i+"'" for i in solvents_list])+')'
        #non_aq_comp = con.execute("SELECT Material_mol FROM electrolyteComp WHERE Electrolyte_ID = ? AND "+non_aq_str, [elec_id]).fetchall()
        solvents_comp = con.execute("SELECT Material_mol FROM electrolyteComp WHERE Electrolyte_ID = ? AND "+solvents_str, [elec_id]).fetchall()
        #mol_nonaq = sum([i[0] for i in non_aq_comp])
        mol_solvents = sum([i[0] for i in solvents_comp])
        con.close()
        return mol_h2o/mol_solvents
    except TypeError:
        print("Cannot find Cell ID.")
    finally:
        con.close()

def get_status(name_id):
    """
    Gets the status of the cell (0,1,2,3).\n
    """
    try:
        con = duckdb.connect(database_name)
        status = con.execute("SELECT Status FROM coinCells WHERE ID = ?", [name_id]).fetchone()[0]
        con.close()
        return status
    except TypeError:
        print("Cannot find Cell ID.")
    finally:
        con.close()

def get_well(name_id):
    """
    Gets the well_ID of the electrolyte used in the cell.\n
    Inputs:\n
    name_id (str) -> unique identifier for the cell\n
    Outputs:\n
    well (int) -> well_id of the electrolyte
    """
    try:
        con = duckdb.connect(database_name)
        well = con.execute("SELECT t2.Well FROM coinCells AS t1 JOIN electrolyteWells AS t2 ON t1.Electrolyte_ID = t2.Electrolyte_ID WHERE t1.ID = ?", [name_id]).fetchone()[0]
        con.close()
        return well
    except TypeError:
        print("Cannot find Cell ID.")
    finally:
        con.close()

# def add_repeat(name_id, new_electrolyte=True):
#     """
#     DOES NOT WORK YET\n
#     Adds a repeat of a cell with a new electrolyte.\n
#     Inputs:\n
#     name_id (str) -> unique identifier for the cell\n
#     new_electrolyte (bool) -> if True, a new electrolyte is created, if False, the same electrolyte is used\n
#     NOTE: track_objs.parquet and elec_mixing_volumes.pkl must be present in the working directory\n
#     Outputs:\n
#     None
#     """
#     try:
#         con = duckdb.connect(database_name)
#         # Get Electrolyte_ID from coinCells table
#         electrolyte_id = con.execute("SELECT Electrolyte_ID FROM coinCells WHERE ID = ?", [name_id]).fetchone()[0]
        
#         # Get composition of the current electrolyte
#         electrolyte_comps = con.execute("SELECT * FROM electrolyteComp WHERE Electrolyte_ID = ?", [electrolyte_id]).fetchall()
        
#         client, id = get_trial_id(name_id)
#         electrolyte_vols = pl.scan_csv(client+'.csv').filter(pl.col('trial') == id).collect()
#         electrolyte_vols = list(electrolyte_vols.row(0))[1:]
#         sum_electrolytes = sum(electrolyte_vols)
#         electrolyte_vols = [(str(i), n) for i,n in enumerate(electrolyte_vols)]

#         track_objs = pl.read_parquet('track_objs.parquet')
#         well_id = track_objs['wellIndex_int'][0]
#         with open('elec_mixing_volumes.pkl', 'rb') as f:
#             elec_mixing_queue = pickle.load(f)
#         new_id = "{:05d}".format(random.randint(0,99999))
    
#         query_comp_list = volConc_to_mol(electrolyte_vols)
#         elec_id, well = get_electrolyte(well_id, query_comp_list, sum_electrolytes)
#         if new_electrolyte:
#             elec_mixing_queue[new_id] = [electrolyte_vols, well_id]
#             with open('elec_mixing_volumes.pkl', 'wb') as f:
#                 pickle.dump(elec_mixing_queue, f)
#         else:
#             elec_mixing_queue[new_id] = [electrolyte_vols, well_id]
#         track_objs = track_objs.with_columns((pl.col('wellIndex_int') + 1).alias('wellIndex_int'))
#         add_coinCell(new_id, elec_id, [1, 2], id, client+'-repeat')
#         track_objs.write_parquet('track_objs.parquet')
        
#     except Exception as e:
#         print(e)

def add_repeat(cell_ID, new_electrolyte=True):
    """
    For molar concentrations\n
    Adds a repeat of a cell with a new electrolyte.\n
    Inputs:\n
    cell_ID (str) -> unique identifier for the cell\n
    new_electrolyte (bool) -> creates new electrolyte for the repeat if True, or use the same well for the repeat if False\n
    NOTE: track_objs.parquet and elec_mixing_volumes.pkl must be present in the working directory\n
    Outputs:\n
    None
    """
    con = duckdb.connect(database_name)
    new_id = "{:05d}".format(random.randint(0,99999))
    # Get electrolyte's old data from coinCells
    electrolyte_id, trial_num, client = con.execute("SELECT Electrolyte_ID, Trial, Opt_Client FROM coinCells WHERE ID = ?", [cell_ID]).fetchone()
    electrode_ids = con.execute("SELECT Electrode1_ID, Electrode2_ID FROM coinCells WHERE ID = ?", [cell_ID]).fetchone()
    if client.endswith('repeat'):
        client_name = client
    else:
        client_name = client+'-repeat'

    if new_electrolyte:
        con.execute("UPDATE electrolyteWells SET Active = false WHERE Electrolyte_ID = ?", [electrolyte_id])
        # Get composition of the electrolyte
        electrolyte_comps = con.execute("SELECT Material_ID, Material_molar_conc FROM electrolyteComp WHERE Electrolyte_ID = ?", [electrolyte_id]).fetchall()
        materials, final_concs = zip(*electrolyte_comps)
        stock_wells = [con.execute("SELECT wellPosition FROM stockSolutions WHERE Component1_Material_ID = ?", [i]).fetchone()[0] for i in materials]
        con.close()
        # Calculate transfer volumes to get that electrolyte from Stock
        vols = get_mixing_volumes([str(i) for i in stock_wells], list(final_concs))
        query_comp_list = get_composition([str(i) for i in stock_wells], list(final_concs))
        # Prepare well location
        track_objs = pl.read_parquet('track_objs.parquet')
        well_id = track_objs['wellIndex_int'][0]
        with open('elec_mixing_volumes.pkl', 'rb') as f:
            elec_mixing_queue = pickle.load(f)
        # Generate new electrolyte ID
        new_elec_id, electrolyte_well = get_electrolyte(well_id, query_comp_list, sum(value for _, value in vols))
        # Insert new electrolyte ID mixing volumes into the dictionary and update track_objs wellIndex
        elec_mixing_queue[new_id] = [vols, electrolyte_well]
        with open('elec_mixing_volumes.pkl', 'wb') as f:
            pickle.dump(elec_mixing_queue, f)
        track_objs = track_objs.with_columns((pl.col('wellIndex_int') + 1).alias('wellIndex_int'))
        track_objs.write_parquet('track_objs.parquet')
        # Add job
        add_coinCell(new_id, new_elec_id, 1, list(electrode_ids), trial_num, client_name)
    else:
        add_coinCell(new_id, electrolyte_id, 1, list(electrode_ids), trial_num, client_name)

def myround(x, base=20.0):
    return round(base * round(x/base), 1)