import duckdb
from qt_ui import new_material_gui, add_job_gui, stock_solutions_gui
import sys
from PyQt5.QtWidgets import QApplication

def create_DB(con = duckdb.connect('odaCell_DB.duckdb')):
    """
    Run once and never again. Creates the database for ODACell.
    """
    con.sql(r"""CREATE TABLE coinCells(
        Status INTEGER NOT NULL DEFAULT 0, 
        ID VARCHAR(5) PRIMARY KEY CHECK(ID ~ '^[0-9]{5}$'), 
        Electrolyte_ID INTEGER, 
        Electrode1_ID INTEGER, 
        Electrode2_ID INTEGER)""")
    con.sql(r"""CREATE TABLE Electrolytes(
        Electrolyte_ID INTEGER PRIMARY KEY, 
        DateMixed DATETIME DEFAULT CURRENT_DATE, 
        Active BOOLEAN DEFAULT TRUE, 
        Well INTEGER CHECK(Well<97), 
        initialVolume INTEGER, 
        currentVolume INTEGER, 
        Solvent_Material_ID INTEGER, 
        Solvent_Name VARCHAR(255),
        Salt_Material_ID INTEGER, 
        Salt_Name VARCHAR(255),
        Salt_Conc DOUBLE)""")
    con.sql(r"""CREATE TABLE stockSolutions(
        wellPosition INTEGER,
        Active BOOLEAN DEFAULT TRUE,
        Solvent_Material_ID INTEGER,
        Solvent_Name VARCHAR(255),
        Component1_Material_ID INTEGER,
        Component1_Name VARCHAR(255), 
        Component1_Conc DOUBLE,
        Density_gmL DOUBLE,
        Volume_uL DOUBLE)""")
    con.sql(r"""CREATE TABLE Electrodes(
        Electrode_ID INTEGER PRIMARY KEY,
        Material_ID INTEGER,
        activeMaterial VARCHAR(255), 
        activeMaterial_Content DOUBLE, 
        specificCapacity_mAh_g DOUBLE, 
        nominalVoltage DOUBLE, 
        currentCollector VARCHAR(255), 
        areaCapacity_mAh_cm2 DOUBLE, 
        electrode_AM_mass_mg DOUBLE, 
        electrode_size_mm INTEGER)""")
    con.sql(r"""CREATE TABLE Additives(
        Electrolyte_ID INTEGER,
        Material_ID INTEGER, 
        Additive VARCHAR(255), 
        Additive_Conc DOUBLE)""")
    con.sql(r"""CREATE TABLE Materials(
        Material_ID INTEGER PRIMARY KEY,
        Name VARCHAR(255),
        Supplier VARCHAR(255),
        DateObtained DATETIME DEFAULT CURRENT_DATE,
        molarMass DOUBLE)""")
    # explicitly close the connection
    con.close()

def dispense_electrolyte(con, elec_id, dispense_vol=45):
    well_and_currentVol = con.execute("SELECT Well, currentVolume FROM Electrolytes WHERE Electrolyte_ID = ?;", [elec_id]).fetchall()[0]
    con.execute("UPDATE Electrolytes SET currentVolume = currentVolume - ? WHERE Electrolyte_ID = ?;", [dispense_vol, elec_id])
    newVol = con.execute("SELECT currentVolume FROM Electrolytes WHERE Electrolyte_ID = ?;", [elec_id]).fetchall()[0][0]
    print("Electrlyte ID {} in Well {}: Volume changed from {} uL to {} uL.".format(elec_id, *well_and_currentVol, newVol))
    if newVol < 70:
        con.execute("UPDATE Electrolytes SET Active = FALSE WHERE Electrolyte_ID = ?;", [elec_id])
        print("Well {} is now empty - removing from Active list.".format(well_and_currentVol[0]))

def get_electrolyte(con, additive_list, current_well, initial_vol, query_solvent_material_id, query_solvent_name, query_salt_material_id, query_salt_name, query_salt_conc):
    results = con.execute("SELECT Electrolyte_ID, Well FROM Electrolytes WHERE Salt_Name = ? AND Salt_Conc = ? AND Active = TRUE", [query_salt_name, query_salt_conc]).fetchall()
    if results:
        for electrolyte in results:
            add_results = con.execute("SELECT Material_ID, Additive, Additive_Conc FROM Additives WHERE Electrolyte_ID = ?", [electrolyte[0]]).fetchall()
            if set(add_results) == set(additive_list):
                return [*electrolyte]
    if con.sql("SELECT MAX(Electrolyte_ID) FROM Electrolytes").fetchall()[0][0]:
        elec_id = con.sql("SELECT MAX(Electrolyte_ID) FROM Electrolytes").fetchall()[0][0] + 1
    else:
        elec_id = 1
    con.execute("INSERT INTO Electrolytes (Electrolyte_ID, Well, initialVolume, currentVolume, Solvent_Material_ID, Solvent_Name, Salt_Material_ID, Salt_Name, Salt_Conc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", [elec_id, current_well, initial_vol, initial_vol, query_solvent_material_id, query_solvent_name, query_salt_material_id, query_salt_name, query_salt_conc])
    if additive_list:
        con.executemany("INSERT INTO Additives (Electrolyte_ID, Material_ID, Additive, Additive_Conc) VALUES (?, ?, ?, ?)", [(elec_id,)+additive for additive in additive_list])
    return [elec_id, current_well]

def add_new_material(con):
    if con.execute("SELECT MAX(Material_ID) FROM Materials").fetchall()[0][0]:
        mat_id = con.execute("SELECT MAX(Material_ID) FROM Materials").fetchall()[0][0]+1
    else:
        mat_id = 1
    app = QApplication(sys.argv)
    w = new_material_gui(mat_id)
    w.show()
    app.exec_()
    if w.result():
        con.execute("INSERT INTO Materials (Material_ID, Name, Supplier, molarMass, DateObtained) VALUES (?, ?, ?, ?, ?);", w.collect_variables())

def get_job(con):
    app = QApplication(sys.argv)
    w = add_job_gui(con)
    w.show()
    app.exec_()
    if w.result():
        return w.outputs()

def update_stock(con):
    app = QApplication(sys.argv)
    w = stock_solutions_gui(con)
    w.show()
    app.exec_()