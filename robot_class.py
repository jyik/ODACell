from dobot_api import dobot_api_dashboard, dobot_api_feedback, MyType
import time

class Dobot:
    def __init__(self, ip_address):
        self.dashboard = dobot_api_dashboard(ip_address, 29999)
        self.feedback = dobot_api_feedback(ip_address, 30003)
        self.dashboard.SetCollisionLevel(4)
        self.dashboard.ClearError()
        self.dashboard.EnableRobot()
    def blocking(self):
        self.dashboard.Sync()
    #speeds don't work
    def globalspeed(self, spd):
        self.dashboard.SpeedL(spd)
    def __del__(self):
        self.dashboard.DisableRobot()

class Dobbie_Crimp(Dobot):
    def __init__(self, ip_address):
        super().__init__(ip_address)
        # Define all points
        # P0 = home
        self.p0 = [0, 0, 0, 0, 0, 0]
        # P1 = outside Otto unloaded
        self._p1 = [-26.4394588470459, 231.85035705566406, -125.17813873291016, 72.37954711914062, 0, 0]
        # P2 = inside Otto unloaded
        self._p2 = [-26.4394588470459, 347.1140441894531, -125.5999984741211, 72.37954711914062, 0, 0]
        # P3 = inside Otto loaded
        self._p3 = [-26.4394588470459, 347.1140441894531, -77.6209945678711, 72.37954711914062, 0, 0]
        # P4 = outside Otto loaded
        self._p4 = [-26.4394588470459, 231.85035705566406, -77.61803436279297, 72.37954711914062, 0, 0]
        # P5 = in front of Crimper loaded
        self._p5 = [116.11180877685547, -202.41477966308594, -77.61803436279297, -84.28645324707031, 0, 0]
        # P6 = over Crimper hole loaded
        self._p6 = [149.97828674316406, -262.76263427734375, -77.6155014038086, -84.28645324707031, 0, 0]
        # P7 = over Crimper hole unloaded
        self._p7 = [149.97836303710938, -262.7627868652344, -96.27590942382812, -84.28645324707031, 0, 0]
        # P8 = in front of Crimper unloaded
        self._p8 = [116.11180877685547, -202.41477966308594, -96.27590942382812, -84.28645324707031, 0, 0]
        # P9 = midpoint (collect cell components)
        self._p9 = [233.28750610351562, 5.534910678863525, -77.61803436279297, -22.767332077026367, 0, 0]

    def crimp(self):
        self.dashboard.DOExecute(1, 1)
        time.sleep(2.5)
        self.dashboard.DOExecute(1, 0)
        #asyncio.sleep()
    
    def mov(self, mode, pnt):
        if (isinstance(mode, str) and isinstance(pnt, list)):
            if mode.lower() == 'j':
                self.feedback.MovJ(*pnt)
            elif mode.lower() == 'l':
                self.feedback.MovL(*pnt)
        else:
            print("Wrong arugment types")

class Dobbie_Cell(Dobot):
    def __init__(self, ip_address):
        super().__init__(ip_address)
        #points
        # P0 = home
        self.p0 = [0, 0, 0, 0, 0, 0]
        # P1 = negative casing
        self.p1 = [119.15614318847656, -184.87525939941406, -135.72756958007812, 73.01055145263672, 0, 0]
        # P2 = anode
        self.p2 = [139.85618591308594, -188.875244140625, -135.5277587890625, 73.01055908203125, 0, 0]
        # P3 = separator
        self.p3 = [159.3562469482422, -190.67532348632812, -134.6278839111328, 73.01055908203125, 0, 0]
        # P4 = cathode
        self.p4 = [178.25633239746094, -193.3754119873047, -135.0279571533203, 73.01055908203125, 0, 0]
        # P5 = spring+spacer
        self.p5 = [197.05615234375, -196.3752899169922, -134.8279266357422, 73.01055908203125, 0, 0]
        # P6 = positive casing
        self.p6 = [218.05613708496094, -198.375244140625, -133.92804260253906, 73.01055908203125, 0, 0]
        # Cell holder dropoff points
        self.p1_unload = [-23.305221557617188, -253.40907287597656, -8.986085414886475, 34.781944274902344, 0, 0]
        self.p2_unload = [-23.105199813842773, -254.10911560058594, -9.286142349243164, 34.78192138671875, 0, 0]
        self.p3_unload = [-22.605121612548828, -252.80911254882812, -8.28610610961914, 34.78193664550781, 0, 0]
        self.p4_unload = [-22.605121612548828, -252.80911254882812, -8.28610610961914, 34.78193664550781, 0, 0]
        self.p5_unload = [-23.005115509033203, -254.00930786132812, -6.976101150512695, 34.781944274902344, 0, 0]
        self.p6_unload = [-22.955509185791016, -252.9289093017578, -6.072357444763184, 33.739532470703125, 0, 0]

    def vacuum(self, isOn):
        if isOn == True:
            self.dashboard.DOExecute(10, 1)
        elif isOn == False:
            self.dashboard.DOExecute(10, 0)
    
    def blow(self):
        self.dashboard.DOExecute(9, 1)
        self.dashboard.DOExecute(9, 0)
    
    # pick_n_place needs to be added
    # cell cycling needs to be added

dcrimp = Dobbie_Crimp('192.168.2.6')
#dcell = Dobbie_Cell('192.168.1.6')

P1 = [-63.4905, 348.0490, -125.0851, 112.2722, 0, 0] # inside otto unloaded 2
P2 = [-60.6266, 319.7347, -125.0851, 77.6736, 0, 0] # inside otto unloaded 1
P3 = [-63.4905, 348.0490, -77.6210, 112.2722, 0, 0] # inside otto loaded

dcrimp.mov('l', P2)
dcrimp.mov('l', P1)
dcrimp.mov('l', P3)
dcrimp.mov('l', P1)
dcrimp.mov('l', P2)
dcrimp.mov('l', dcrimp._p1)
#dcrimp.mov('l', P3)
dcrimp.blocking()
time.sleep(25)

