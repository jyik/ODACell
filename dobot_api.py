import socket
from threading import Timer
import numpy as np

MyType=np.dtype([('len', np.int64, ), ('digital_input_bits', np.int64, ), 
                ('digital_outputs', np.int64, ), ('robot_mode', np.int64, ), 
                ('controller_timer', np.int64, ),('run_time', np.int64, ), 
                ('test_value', np.int64, ), ('safety_mode', np.float64, ), 
                ('speed_scaling', np.float64, ), ('linear_momentum_norm', np.float64, ),
                ('v_main', np.float64, ), ('v_robot', np.float64, ), 
                ('i_robot', np.float64, ), ('program_state', np.float64, ), 
                ('safety_status', np.float64, ), ('tool_accelerometer_values', np.float64, (3,)), 
                ('elbow_position', np.float64, (3,)), ('elbow_velocity', np.float64, (3,)), 
                ('q_target', np.float64, (6,)), ('qd_target', np.float64,(6,)),
                ('qdd_target', np.float64, (6,)), ('i_target', np.float64,(6,)), 
                ('m_target', np.float64, (6,)), ('q_actual', np.float64, (6,)), 
                ('qd_actual', np.float64, (6,)), ('i_actual', np.float64, (6,)), 
                ('i_control', np.float64, (6,)), ('tool_vector_actual', np.float64, (6,)), 
                ('TCP_speed_actual', np.float64, (6,)), ('TCP_force', np.float64, (6,)),
                ('Tool_vector_target', np.float64, (6,)), ('TCP_speed_target', np.float64, (6,)), 
                ('motor_temperatures', np.float64, (6,)), ('joint_modes', np.float64, (6,)), 
                ('v_actual', np.float64, (6,)), ('dummy', np.float64, (9,6))
                ])

class dobot_api_dashboard:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket_dashboard = 0

        if self.port == 29999:
            try:     
                self.socket_dashboard = socket.socket() 
                self.socket_dashboard.connect((self.ip, self.port))
            except socket.error:
                print("Fail to setup socket connection !", socket.error)
        else:
            print("Connect to dashboard server need use port 29999 !")

    def __delete__(self):
        self.close()

    def EnableRobot(self):
        string = "EnableRobot()"
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()
        
    def DisableRobot(self):
        string = "DisableRobot()"
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def ClearError(self):
        string = "ClearError()"
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def ResetRobot(self):
        string = "ResetRobot()"
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def SpeedFactor(self, speed):
        string = "SpeedFactor({:d})".format(speed)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8')) 
        self.WaitReply()

    def User(self, index):
        string = "User({:d})".format(index)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def Tool(self, index):
        string = "Tool({:d})".format(index)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def RobotMode(self):
        string = "RobotMode()"
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def PayLoad(self, weight, inertia):
        string = "PayLoad({:f},{:f})".format(weight,inertia)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def DO(self, index, val):
        string = "DO({:d},{:d})".format(index,val)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def DOExecute(self, index, val):
        string = "DOExecute({:d},{:d})".format(index,val)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def ToolDO(self, index, val):
        string = "ToolDO({:d},{:d})".format(index,val)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def ToolDOExecute(self, index, val):
        string = "ToolDOExecute({:d},{:d})".format(index,val)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def AO(self, index, val):
        string = "AO({:d},{:f})".format(index,val)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def AOExecute(self, index, val):
        string = "AOExecute({:d},{:f})".format(index,val)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def AccJ(self, speed):
        string = "AccJ({:d})".format(speed)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def AccL(self, speed):
        string = "AccL({:d})".format(speed)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def SpeedJ(self, speed):
        string = "SpeedJ({:d})".format(speed)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def SpeedL(self, speed):
        string = "SpeedL({:d})".format(speed)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def Arch(self, index):
        string = "Arch({:d})".format(index)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def CP(self, ratio):
        string = "CP({:d})".format(ratio)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def LimZ(self, value):
        string = "LimZ({:d})".format(value)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def SetArmOrientation(self, r, d, n, cfg):
        string = "SetArmOrientation({:d},{:d},{:d},{:d})".format(r,d,n,cfg)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def PowerOn(self):
        string = "PowerOn()"
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def RunScript(self, project_name):
        string = "RunScript({:s})".format(project_name)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def ClearError(self):
        string = "ClearError()"
        print(string)
        self.socket_dashboard.send(str.encode(string, 'utf-8'))
        self.WaitReply()

    def StopScript(self):
        string = "StopScript()"
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def PauseScript(self):
        string = "PauseScript()"
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def ContinueScript(self):
        string = "ContinueScript()"
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def GetHoldRegs(self, id, addr, count, type):
        string = "GetHoldRegs({:d},{:d},{:d},{:s})".format(id,addr,count,type)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def SetHoldRegs(self, id, addr, count, table, type):
        string = "SetHoldRegs({:d},{:d},{:d},{:d},{:s})".format(id,addr,count,table,type)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

    def WaitReply(self):
        data = self.socket_dashboard.recv(1024)
        print('receive:', bytes.decode(data,'utf-8'))

    def close(self):
        if(self.socket_dashboard != 0):
            self.socket_dashboard.close()
    
    def SetCollisionLevel(self, level):
        string = "SetCollisionLevel({:d})".format(level)
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()
    
    def Sync(self):
        string = "Sync()"
        print(string)
        self.socket_dashboard.send(str.encode(string,'utf-8'))
        self.WaitReply()

class dobot_api_feedback:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket_feedback = 0 

        if self.port == 30003:
            try:      
                self.socket_feedback = socket.socket() 
                self.socket_feedback.connect((self.ip, self.port))
            except socket.error:
                print("Fail to connect feedback server !", socket.error)
        else:
            print("Connect to feedback server need use port 30003 !")


    def __del__(self):
        self.close()

    def MovJ(self, x, y, z, a, b, c):
        string = "MovJ({:f},{:f},{:f},{:f},{:f},{:f})".format(x,y,z,a,b,c)
        print(string)
        self.socket_feedback.send(str.encode(string,'utf-8'))
    
    def MovL(self, x, y, z, a, b, c):
        string = "MovL({:f},{:f},{:f},{:f},{:f},{:f})".format(x,y,z,a,b,c)
        print(string)
        self.socket_feedback.send(str.encode(string,'utf-8'))

    def JointMovJ(self, j1, j2, j3, j4, j5, j6):
        string = "JointMovJ({:f},{:f},{:f},{:f},{:f},{:f})".format(j1,j2,j3,j4,j5,j6)
        print(string)
        self.socket_feedback.send(str.encode(string,'utf-8')) 
    
    def Jump(self):
        print("待定") 

    def RelMovJ(self, offset1, offset2, offset3, offset4, offset5, offset6):
        string = "RelMovJ({:f},{:f},{:f},{:f},{:f},{:f})".format(offset1,offset2,offset3,offset4,offset5,offset6)
        print(string)
        self.socket_feedback.send(str.encode(string,'utf-8'))
    
    def RelMovL(self, offsetX, offsetY, offsetZ):
        string = "RelMovL({:f},{:f},{:f})".format(offsetX,offsetY,offsetZ)
        print(string)
        self.socket_feedback.send(str.encode(string,'utf-8'))

    def MovLIO(self, x, y, z, a, b, c, *dynParams):
        # example： MovLIO(0,50,0,0,0,0,(0,50,1,0),(1,1,2,1))
        string = "MovLIO({:f},{:f},{:f},{:f},{:f},{:f}".format(x,y,z,a,b,c)
        print(type(dynParams), dynParams)
        for params in dynParams:
            print(type(params), params)
            string = string + ",{{{:d},{:d},{:d},{:d}}}".format(params[0],params[1],params[2],params[3])
        string = string + ")"
        print(string)
        self.socket_feedback.send(str.encode(string,'utf-8')) 

    def MovJIO(self, x, y, z, a, b, c, *dynParams):
        # example： MovJIO(0,50,0,0,0,0,(0,50,1,0),(1,1,2,1))
        string = "MovJIO({:f},{:f},{:f},{:f},{:f},{:f}".format(x,y,z,a,b,c)
        print(string)
        print(type(dynParams), dynParams)
        for params in dynParams:
            print(type(params), params)
            string = string + ",{{{:d},{:d},{:d},{:d}}}".format(params[0],params[1],params[2],params[3])
        string = string + ")"
        print(string)
        self.socket_feedback.send(str.encode(string,'utf-8'))  
 
    def Arc(self, x1, y1, z1, a1, b1, c1, x2, y2, z2, a2, b2, c2):
        string = "Arc({:f},{:f},{:f},{:f},{:f},{:f},{:f},{:f},{:f},{:f},{:f},{:f})".format(x1,y1,z1,a1,b1,c1,x2,y2,z2,a2,b2,c2)
        print(string)
        self.socket_feedback.send(str.encode(string,'utf-8'))

    def Circle(self, count, x1, y1, z1, a1, b1, c1, x2, y2, z2, a2, b2, c2):
        string = "Circle({:d},{:f},{:f},{:f},{:f},{:f},{:f},{:f},{:f},{:f},{:f},{:f},{:f})".format(count,x1,y1,z1,a1,b1,c1,x2,y2,z2,a2,b2,c2)
        print(string)
        self.socket_feedback.send(str.encode(string,'utf-8'))
    
    def ServoJ(self, j1, j2, j3, j4, j5, j6):
        string = "ServoJ({:f},{:f},{:f},{:f},{:f},{:f})".format(j1,j2,j3,j4,j5,j6)
        print(string)
        self.socket_feedback.send(str.encode(string,'utf-8'))

    def ServoP(self, x, y, z, a, b, c):
        string = "ServoP({:f},{:f},{:f},{:f},{:f},{:f})".format(x,y,z,a,b,c)
        print(string)
        self.socket_feedback.send(str.encode(string,'utf-8'))

    def WaitReply(self):
        all = self.socket_feedback.recv(10240)
        data = all[0:1440]
        a = np.frombuffer(data, dtype=MyType)
        if hex((a['test_value'][0])) == '0x123456789abcdef':
            print('robot_mode', a['robot_mode'])
            print('tool_vector_actual', np.around(a['tool_vector_actual'], decimals=4))
            print('q_actual', np.around(a['q_actual'], decimals=4))
            print('test_value', a['test_value'])
       
    def close(self):
        if(self.socket_feedback != 0):
            self.socket_feedback.close()