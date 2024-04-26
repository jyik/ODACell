import polars as pl
import numpy as np
import duckdb


def get_coords(for_robot, file_loc = r'C:\Users\renrum\Desktop\Coordinates\v4\coordinates.parquet'):
    """
    Loads relevant point locations for specific robots into a DuckDB relation.\n
    Inputs: \n
    for_robot (str)-> Robot name, either:\n
    'Crimp' \n
    'Grip' \n
    \n
    file_loc (str)-> file location. Must be a parquet file.\n
    Output: \n
    coord (duckdb Relation)->  duckdb Relation of [Name, Category, Sub Category, Robot, X, Y, Z, R] coordinates.
    """
    return duckdb.sql("SELECT * FROM read_parquet('{}') WHERE Robot='{}';".format(file_loc,for_robot))

def get_pnt(p, df):
    """
    Get the point [x,y,z,Rx] from the coordinate dataframe. \n
    Input: \n
    p (str)-> str for mapping using the corresponding Name column of df\n
    df (duckdb query-able type)-> coordinate dataframe\n
    Output: \n
    pnt (list)-> list of [x,y,z,R] \n
    """
    if isinstance(p, str):
        return [value for value in duckdb.sql("SELECT X, Y, Z, R FROM df WHERE Name='{}'".format(p)).fetchall()[0]]
    else:
        print('wrong type')

def get_r(x,y):
    """
    Convert 2D x,y Cartesian coordinates to radius r. \n
    Input: \n
    x (float)-> x coordinate in mm \n
    y (float)-> y coordinate in mm \n
    Output: \n
    r (float)-> radius/hypotenuse in mm \n
    """
    return np.sqrt(x**2 + y**2)

def get_xy(r,theta):
    """
    Convert 2D radial coordinates to Cartesian coordinates \n
    Input: \n
    r (float)-> radius in mm \n
    theta (float)-> angle in degrees \n
    Output: \n
    xy (list)-> [x,y] coordinates in mm \n
    """
    return [r*np.cos(theta*np.pi/180), r*np.sin(theta*np.pi/180)]

def movetoheight(pnt, z):
    """
    Takes a list and absolute height and returns the list with that height (in index 2) \n
    Input: \n
    pnt (list)-> list of a coordinate point [X,Y,Z,R] \n
    z (float)-> desired height \n
    Output: \n
    temp_pnt (list)-> list with new z replacing old Z [X,Y,z,R] \n
    """
    if isinstance(pnt, (list, np.ndarray)):
        temp_pnt = list(pnt).copy()
        temp_pnt[2] = z
        return temp_pnt
    else:
        print("Coordinate point is not a list [x,y,z,rx]")

def excel_to_parquet(excel_filepath=r'C:\Users\renrum\Desktop\Coordinates\v4\coordinatesDB.xlsx'):
    parquet_filepath = excel_filepath.split('.')[0]+'.parquet'
    pl.read_excel(excel_filepath).write_parquet(parquet_filepath)

def pnt_offset(pnt, offset_list:list):
    if len(pnt) == len(offset_list):
        new_pnt = [pnt[i]+offset_list[i] for i in range(len(pnt))]
        return new_pnt
    else:
        print("Point and Offset must have same dimensions. Set 0 for dimensions you don't want to change.")
