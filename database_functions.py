import duckdb
from qt_ui import new_material_gui, add_job_gui, stock_solutions_gui
import sys
from PyQt5.QtWidgets import QApplication

database_name = 'test.duckdb'

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
        Material_mol DOUBLE)""")
        con.sql(r"""CREATE TABLE stockSolutions(
        wellPosition INTEGER,
        Solvent_Material_ID INTEGER,
        Solvent_Name VARCHAR(255),
        Component1_Material_ID INTEGER,
        Component1_Name VARCHAR(255), 
        Component1_Conc_molal DOUBLE,
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
    #   con.sql(r"""CREATE TABLE Additives(
    #    Electrolyte_ID INTEGER,
    #    Material_ID INTEGER, 
    #    Additive VARCHAR(255), 
    #    Additive_Conc DOUBLE)""")
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
    current_well (int) -> next empty well incase electrolyte needs to be created\n
    query_component_list (list) -> list of tuples for Material_ID, Material_Name, and number of moles of component, Material_mol, of the electrolyte. Example: [(1, 'test1', 2.1), (2, 'test2', 0.4), (3, 'test3', 1.2)]\n
    total_vol (int) -> if the electrolyte needs to be mixed, what will the volume inside the well be\n
    Outputs:\n
    elec_id_and_well (list) -> returns a list containing two integers, Electrolyte_ID and Well of the query component
    """
    con = duckdb.connect(database_name)
    results = con.execute("SELECT Electrolyte_ID FROM electrolyteComp WHERE Material_ID = ? AND Material_Name = ? AND Material_mol = ?", query_component_list[0]).fetchall()
    if results:
        for electrolyte in results:
            test_list = con.execute("SELECT Material_ID, Material_Name, Material_mol FROM electrolyteComp WHERE Electrolyte_ID = ?", [electrolyte[0]]).fetchall()
            if set(test_list) == set(query_component_list):
                id_well = con.execute("SELECT Electrolyte_ID, Well FROM electrolyteWells WHERE Electrolyte_ID = ?", [electrolyte[0]]).fetchone()
                con.close()
                return [*id_well]
    if con.sql("SELECT MAX(Electrolyte_ID) FROM electrolyteWells").fetchall()[0][0]:
        elec_id = con.sql("SELECT MAX(Electrolyte_ID) FROM electrolyteWells").fetchall()[0][0] + 1
    else:
        elec_id = 1
    con.execute("INSERT INTO electrolyteWells (Electrolyte_ID, Well, currentVolume) VALUES (?, ?, ?);", [elec_id, current_well, total_vol])
    con.executemany("INSERT INTO electrolyteComp (Electrolyte_ID, Material_ID, Material_name, Material_mol) VALUES (?, ?, ?, ?)", [(elec_id,)+comp for comp in query_component_list])
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
    Updates initial stock solutions for mixing. GUI based - only selects from existing materials from Materials table in the database.
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
        print(con.execute("SELECT * FROM "+tableName).fetch_df().to_string())
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

def get_mixing_volumes(init_molals, final_molals, molar_masses, densities, solvent_mass = 1.3):
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
    
def volConc_to_mol(wellVol_list):
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

def add_coinCell(id, electrolyte_id, electrode_ids, trial, optimizer='batterydemo\\NEVHI_42'):
    con = duckdb.connect(database_name)
    con.execute("INSERT INTO coinCells (ID, Electrolyte_ID, Electrode1_ID, Electrode2_ID, Opt_Client, Trial) VALUES (?, ?, ?, ?, ?, ?)", [id, electrolyte_id, electrode_ids[0], electrode_ids[1], optimizer, trial])
    con.close()

def get_trial_id(name_id):
    con = duckdb.connect(database_name)
    client_trial = con.execute("SELECT Opt_Client, Trial FROM coinCells WHERE ID = ?", [name_id]).fetchone()
    con.close()
    return client_trial

def aq_solv_percent(name_id):
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
