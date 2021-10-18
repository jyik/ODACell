import socket
import numpy as np
import sys
import DobotSDK as dobotSDK
from PyQt6.QtWidgets import QDialog, QApplication
from DemoClient import *
from ctypes import *

#Error with loading dobotSDK when using Qt5
api = dobotSDK.load()

# Dobot Crimp points
p1 = [-26.4394588470459, 231.85035705566406, -125.17813873291016, 72.37954711914062, 0, 0]
p2 = [-26.4394588470459, 347.1140441894531, -125.5999984741211, 72.37954711914062, 0, 0]
p3 = [-26.4394588470459, 347.1140441894531, -77.6209945678711, 72.37954711914062, 0, 0]
p4 = [-26.4394588470459, 231.85035705566406, -77.61803436279297, 72.37954711914062, 0, 0]
p5 = [116.11180877685547, -202.41477966308594, -77.61803436279297, -84.28645324707031, 0, 0]
p6 = [149.97828674316406, -262.76263427734375, -77.6155014038086, -84.28645324707031, 0, 0]
p7 = [149.97836303710938, -262.7627868652344, -96.27590942382812, -84.28645324707031, 0, 0]
p8 = [116.11180877685547, -202.41477966308594, -96.27590942382812, -84.28645324707031, 0, 0]
p9 = [233.28750610351562, 5.534910678863525, -77.61803436279297, -22.767332077026367, 0, 0]

crimp_coord = [p1, p2, p3, p4, p5, p6, p7, p8, p9]

#pnts 4, 5, 9 needs to be MovJ

#connect to dobbie crimp
dobotSDK.ConnectDobot(api, "192.168.1.6")

#Setup server client connection
host = '130.238.197.183' #client ip
port = 4005
server = ('130.238.197.169', 4000)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((host,port))

#setup GUI: work in progress
class MyForm(QDialog):
    def __init__(self):
        global api
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.textEditLogDisplay.setReadOnly(True)

        # Dobie Cell
        #self.ui.checkBoxConnectServer.toggled.connect(self.connection)
        self.ui.checkBoxDobieCellControl.clicked.connect(self.cell_control)
        self.ui.pushButtonPC.clicked.connect(lambda:self.pick_n_place("P1"))
        self.ui.pushButtonC.clicked.connect(lambda:self.pick_n_place("P2"))
        self.ui.pushButtonS.clicked.connect(lambda:self.pick_n_place("P3"))
        self.ui.pushButtonA.clicked.connect(lambda:self.pick_n_place("P4"))
        self.ui.pushButtonSpacerSpring.clicked.connect(lambda:self.pick_n_place("P5"))
        self.ui.pushButtonNC.clicked.connect(lambda:self.pick_n_place("P6"))
        self.ui.checkBoxVacuum.clicked.connect(self.vacuum)
        self.ui.pushButtonPump.clicked.connect(self.blow)


        # Dobie Crimp
        self.ui.checkBoxDobieCrimpControl.clicked.connect(self.crimp_control)
        self.ui.pushButtonCrimp.clicked.connect(self.crimp)
        self.ui.radioButtonP1.toggled.connect(self.mov_crimp)
        self.ui.radioButtonP2.toggled.connect(self.mov_crimp)
        self.ui.radioButtonP3.toggled.connect(self.mov_crimp)
        self.ui.radioButtonP4.toggled.connect(self.mov_crimp)
        self.ui.radioButtonP5.toggled.connect(self.mov_crimp)
        self.ui.radioButtonP6.toggled.connect(self.mov_crimp)
        self.ui.radioButtonP7.toggled.connect(self.mov_crimp)
        self.ui.radioButtonP8.toggled.connect(self.mov_crimp)
        self.ui.radioButtonP9.toggled.connect(self.mov_crimp)

        self.show()
    
    #Setup helper functions
    def cell_control(self):
        global s, server
        if self.ui.checkBoxDobieCellControl.isChecked()==True:
            s.sendto("activate".encode('utf-8'), server)
        else:
            s.sendto("deactivate".encode('utf-8'), server)
        data, addr = s.recvfrom(1024)
        data = data.decode('utf-8')
        self.ui.textEditLogDisplay.append(data)

    def crimp_control(self):
        global api
        if self.ui.checkBoxDobieCrimpControl.isChecked()==True:
            dobotSDK.SetControlMode(api, 1)
            self.ui.textEditLogDisplay.append("Dobie Crimp enabled")
        else:
            dobotSDK.SetControlMode(api, 0)
            self.ui.textEditLogDisplay.append("Dobie Crimp disabled")
    
    def crimp(self):
        global api
        _, DOmap = dobotSDK.GetDO(api)
        self.ui.textEditLogDisplay.append("Crimping in progress...")
        DOmap[1] = True
        dobotSDK.SetDO(api, DOmap)
        _ = dobotSDK.SetControlMode(api, 1)
        DOmap[1] = False
        dobotSDK.SetDO(api, DOmap)
        dobotSDK.dSleep(10000)
        _ = dobotSDK.SetControlMode(api, 1)
        self.ui.textEditLogDisplay.append("Crimping finished")

    def mov_crimp(self):
        global api, crimp_coord
        coordList = dobotSDK.GetExchange(api)[9]
        dist_list = [np.linalg.norm(np.array(i[:3])-np.array(coordList[:3])) for i in crimp_coord]
        closest_pnt_indx = np.argmin(dist_list)

        if self.ui.radioButtonP1.isChecked() == True:
            pnt = 0
        if self.ui.radioButtonP2.isChecked() == True:
            pnt = 1
        if self.ui.radioButtonP3.isChecked() == True:
            pnt = 2
        if self.ui.radioButtonP4.isChecked() == True:
            pnt = 3
        if self.ui.radioButtonP5.isChecked() == True:
            pnt = 4
        if self.ui.radioButtonP6.isChecked() == True:
            pnt = 5
        if self.ui.radioButtonP7.isChecked() == True:
            pnt = 6
        if self.ui.radioButtonP8.isChecked() == True:
            pnt = 7
        if self.ui.radioButtonP9.isChecked() == True:
            pnt = 8
        
        if (min(dist_list) < 1 and pnt == closest_pnt_indx):
            return
        if closest_pnt_indx == 1:
            dobotSDK.MovL(api, crimp_coord[0], isBlock=True)
            current_pos = 0
        elif closest_pnt_indx == 2:
            dobotSDK.MovL(api, crimp_coord[3], isBlock=True)
            current_pos = 3
        elif closest_pnt_indx == 5:
            dobotSDK.MovL(api, crimp_coord[4], isBlock=True)
            current_pos = 4
        elif closest_pnt_indx == 6:
            dobotSDK.MovL(api, crimp_coord[7], isBlock=True)
            current_pos = 7
        else:
            dobotSDK.MovJ(api, crimp_coord[closest_pnt_indx], isBlock=True)
            current_pos = closest_pnt_indx

        if pnt == 8:
            if current_pos == 7:
                dobotSDK.MovJ(api, crimp_coord[4], isBlock=True)
                dobotSDK.MovJ(api, crimp_coord[8], isBlock=True)
            elif current_pos == 0:
                dobotSDK.MovJ(api, crimp_coord[3], isBlock=True)
                dobotSDK.MovJ(api, crimp_coord[8], isBlock=True)
            else:
                dobotSDK.MovJ(api, crimp_coord[8], isBlock=True)
        elif pnt in [0,3,4,7]:
            dobotSDK.MovJ(api, crimp_coord[pnt], isBlock=True)
        elif pnt in [1,2,5,6]:
            if current_pos == 8:
                if pnt >= 4:
                    dobotSDK.MovJ(api, crimp_coord[4], isBlock=True)
                    for i in range(5, pnt+1):
                        dobotSDK.MovL(api, crimp_coord[i], isBlock=True)
                elif pnt <= 3:
                    dobotSDK.MovJ(api, crimp_coord[3], isBlock=True)
                    for i in reversed(range(pnt, 3)):
                        dobotSDK.MovL(api, crimp_coord[i], isBlock=True)
            elif pnt - current_pos < 0:
                for i in reversed(range(pnt, current_pos)):
                    if i == 3:
                        dobotSDK.MovJ(api, crimp_coord[i], isBlock=True)
                    else:
                        dobotSDK.MovL(api, crimp_coord[i], isBlock=True)
            elif pnt - current_pos > 0:
                for i in range(current_pos+1, pnt+1):
                    if i == 4:
                        dobotSDK.MovJ(api, crimp_coord[i], isBlock=True)
                    else:
                        dobotSDK.MovL(api, crimp_coord[i], isBlock=True)
            

    def pick_n_place(self, pnt):
        global s, server
        dobie_cell_pnt_dic = {'P1':'positive casing', 'P2':'cathode', 'P3':'separator', 'P4':'anode', 'P5':'spring and spacer', 'P6':'negative casing'}
        s.sendto(("pick_n_place:"+pnt).encode('utf-8'), server)
        self.ui.textEditLogDisplay.append("Dobie Cell placed "+dobie_cell_pnt_dic[pnt])
    
    def vacuum(self):
        global s, server
        if self.ui.checkBoxVacuum.isChecked()==True:
            s.sendto("vaccum:on".encode('utf-8'), server)
        else:
            s.sendto("vaccum:off".encode('utf-8'), server)
        data, addr = s.recvfrom(1024)
        data = data.decode('utf-8')
        self.ui.textEditLogDisplay.append(data)
    
    def blow(self):
        global s, server
        s.sendto("blow".encode('utf-8'), server)
        data, addr = s.recvfrom(1024)
        data = data.decode('utf-8')
        self.ui.textEditLogDisplay.append(data)

# run gui app
if __name__=="__main__":
    app = QApplication(sys.argv)
    w = MyForm()
    w.show()
    sys.exit(app.exec())

