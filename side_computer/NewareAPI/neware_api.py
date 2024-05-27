import socket
import re
from datetime import datetime
import pandas as pd
import shutil
import shortuuid
import os
#from data_analyzer import search_dir

PORT = 502 # Port for TCP connection
chl_mapping = {"1":[27, 1, 1],
               "2":[27, 1, 2],
               "3":[27, 1, 3],
               "4":[27, 1, 4],
               "5":[27, 1, 5],
               "6":[27, 1, 6],
               "7":[27, 1, 7],
               "8":[27, 1, 8],
               "9":[27, 2, 1],
               "10":[27, 2, 2],
               "11":[27, 2, 3],
               "12":[27, 2, 4],
               "13":[27, 2, 5],
               "14":[27, 2, 6],
               "15":[27, 2, 7],
               "16":[27, 2, 8],
               "17":[27, 3, 1],
               "18":[27, 3, 2],
               "19":[27, 3, 3],
               "20":[27, 3, 4],
               "21":[27, 3, 5],
               "22":[27, 3, 6],
               "23":[27, 3, 7],
               "24":[27, 3, 8],
               "25":[27, 4, 1],
               "26":[27, 4, 2],
               "27":[27, 4, 3],
               "28":[27, 4, 4],
               "29":[27, 4, 5],
               "30":[27, 4, 6],
               "31":[27, 4, 7],
               "32":[27, 4, 8],
               "33":[27, 5, 1],
               "34":[27, 5, 2],
               "35":[27, 5, 3],
               "36":[27, 5, 4],
               "37":[27, 5, 5],
               "38":[27, 5, 6],
               "39":[27, 5, 7],
               "40":[27, 5, 8]}

class NewareAPI:
    def __init__(self, IP: str) -> None:
        """
        Create TCP connection to the neware at IP address
        """
        self.ip = IP
        self.port = PORT
        self.chl_map = chl_mapping
        try:
            self.neware_socket = socket.socket()
            self.neware_socket.connect((self.ip, self.port))
            connect = u"""<?xml version="1.0" encoding="UTF-8" ?><bts version="1.0"><cmd>connect</cmd>
                          <username>test</username><password>123</password><type>bfgs</type></bts>\n\n#\r\n"""
            self.sendRecvMsg(connect)
        except socket.error:
            print(socket.error)
            raise Exception(f"Unable to set socket connection for {self.ip} using port {self.port}!", socket.error)
        

    def log(self, text):
        """
        TODO: Add a log
        """
        #if self.text_log:
        #    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S ")
        #    self.text_log.insert(END, date+text+"\n")
        #else:
        #    print(text)
        print("currently not working")

    def send_data(self, string):
        """
        Send data to socket connection
        """
        print(f"Sending:\n{string}")
        try:
            self.neware_socket.send(str.encode(string, 'utf-8'))
        except Exception as e:
            print(e)

    def wait_reply(self):
        """
        Read the return value
        """
        data_str = ""
        try:
            data = self.neware_socket.recv(2048)
            data_str += str(data, encoding="utf-8")
            while "#" not in data_str[-4:]:
                data = self.neware_socket.recv(2048)
                data_str += str(data, encoding="utf-8")
        except Exception as e:
            print(e)
        finally:
            print(f'Received:\n{data_str}')
            return data_str

    def sendRecvMsg(self, string):
        """
        Send commad and then wait for response
        """
        self.send_data(string)
        recvData = self.wait_reply()
        return recvData
    
    def startCell(self, chlid, cell_id, procedure_dir=r"C:\Program Files (x86)\NEWARE\BTSClient80\StepManager\Jackie_templates\lfp_lto_aq_bo.xml"):
        """
        Start designated protocol file on chlid (str - specified by the mapping).
        cell_id will be the barcode.
        """
        cmd = u"""<?xml version="1.0" encoding="UTF-8" ?>
                <bts version="1.0">
                <cmd>start</cmd>
                <list count="1" DBC_CAN="1">
                <start ip="127.0.0.1" devtype="24" devid="{}" subdevid="{}" chlid="{}" barcode="{}" >{}</start>
                <backup backupdir="C:\\BACKUP" remotedir="" filenametype="1" customfilename="" addtimewhenrepeat="0" createdirbydate="0" filetype="1" backupontime="0" backupontimeinterval="720" backupfree="0" /> 
                </list>
                </bts>
                \n\n#\r\n""".format(*self.chl_map[chlid], cell_id, procedure_dir)
        return self.sendRecvMsg(cmd)

    def stopCell(self, chlid):
        """
        Stop channels. Can be one (str - specified by the mapping) or many (list or tuple of strings specified by the mapping)
        """
        if isinstance(chlid, str):
            l = 1
            chlid = [chlid]
        elif isinstance(chlid, tuple) or isinstance(chlid, list):
            l = len(chlid)
        else:
            print("Cannot read Channel ID, make sure the type is correct.")
        
        header = u"""<?xml version="1.0" encoding="UTF-8" ?>\n<bts version="1.0">\n\t<cmd>stop</cmd>\n\t<list count = "{}">\n""".format(l)
        footer = u"""\t</list>\n</bts>\n\n#\r\n"""
        cmd_string = ""
        for chl in chlid:
            cmd_string += u"""\t\t<stop ip="127.0.0.1" devtype="24" devid="{}" subdevid="{}" chlid="{}">true</stop>\n""".format(*self.chl_map[chl])
        return self.sendRecvMsg(header+cmd_string+footer)

    def chlStatus(self, chlid=''):
        """
        Get Status of all the channels (no arguements) or specific channel(s) (chlid argument str or list of strings corresponding to the mapping)
        """
        header = u"""<?xml version="1.0" encoding="UTF-8" ?>\n<bts version="1.0">\n\t<cmd>getchlstatus</cmd>\n\t<list count = "{}">\n""".format(len(self.chl_map))
        footer = u"""\t</list>\n</bts>\n\n#\r\n"""
        cmd_string = ""
        for chl in self.chl_map:
            cmd_string += u"""\t\t<status ip="127.0.0.1" devtype="24" devid="{}" subdevid="{}" chlid="{}">true</status>\n""".format(*self.chl_map[chl])
        rspns = self.sendRecvMsg(header+cmd_string+footer)
        if chlid:
            match = re.search('devid="{}" subdevid="{}" chlid="{}"'.format(*self.chl_map[chlid]) + '\>(.*?)\<', rspns)
            if match:
                return match.group(1)
            else:
                return rspns
        else:
            return rspns

    def inquireChl(self,chlid:str):
        cmd_string = u"""<?xml version="1.0" encoding="UTF-8" ?><bts version="1.0"><cmd>inquire</cmd>
                        <list count = "1">
                        <inquire ip="127.0.0.1" devtype="24" devid="{}" subdevid="{}" chlid="{}" aux="0" barcode="1">true</inquire>
                        </list></bts>\n\n#\r\n""".format(*self.chl_map[chlid])
        recv_str = self.sendRecvMsg(cmd_string)
        pattern = r'<inquire(.*?)\/>'
        match = re.search(pattern, recv_str)
        key_vals_pattern = r'(\w+)="([^"]*)"'
        key_val_matches = re.findall(key_vals_pattern, match[0])
        chlStat = {key: value for key, value in key_val_matches}
        return chlStat

    def downloadData(self, chlid:str, savePath=''):
        """
        Downloads the data points for chlid corresponding to the mapping. savePath must contain the new filename as well. If no savePath given, it will default to save into C:/DATA
        """
        startPos = 1
        count = '100'
        name = self.inquireChl(chlid)['barcode']
        if not savePath:
            data_folder = 'C:'+os.sep+"DATA"+os.sep
            date = datetime.today().strftime('%Y-%m-%d')
            if not os.path.exists(data_folder+date):
                os.makedirs(data_folder+date)
            uniqeid = str(shortuuid.uuid())
            new_file = data_folder+date+os.sep+date+"_"+name+"_"+uniqeid+".txt"
        else:
            new_file = savePath

        while count == '100':
            cmd_string = u"""<?xml version="1.0" encoding="UTF-8" ?><bts version="1.0">
                <cmd>download</cmd>
                    <download devtype="24" devid="{}" subdevid="{}" chlid="{}" auxid="0" testid="0" startpos="{}" count="100"/>
                </bts>\n\n#\r\n""".format(*chl_mapping[chlid], startPos)
            return_data = self.sendRecvMsg(cmd_string)
            match = re.search('<list count="(\d+)">(.*?)</list>', return_data, re.DOTALL)
            if match:
                # Extract the count and the matched text
                count = match.group(1)
                startPos += int(count)
                extracted_data = match.group(2)
                if savePath:
                    pass
                with open(new_file, 'a') as f:
                    # Write the extracted text to the file
                    f.write(extracted_data)
                    f.close() #explicitly close otherwise I get an permission error becase the loop is too fast
            else:
                print('error')
                break
        self.xml_to_csv(new_file)
        # deletes the txt file
        if os.path.isfile(new_file):
            os.remove(new_file)

    def xml_to_csv(self, filepath: str):
        pattern = r'<(.*?)\/>'
        key_vals_pattern = r'(\w+)="([^"]*)"'
        buffer = ''
        data = []
        save_file = filepath.rsplit('.', 1)[0]
        with open(filepath, 'r') as file:
            while True:
                chunk = buffer + file.read(2048)
                if not chunk:
                    break

                # Process the chunk up to the last complete piece of data
                last_newline = chunk.rfind('\n')
                if last_newline != -1:
                    data_to_process = chunk[:last_newline]
                    buffer = chunk[last_newline+1:]
                else:
                    data_to_process = chunk
                    buffer = ''
                # Regular expression pattern to match each row
                matches = re.findall(pattern, data_to_process)
                for match in matches:
                    # Fine Key-Value pairs
                    key_val_matches = re.findall(key_vals_pattern, match)
                    # Convert the matches into a dictionary
                    row = {key: value for key, value in key_val_matches}
                    data.append(row)
        df = pd.DataFrame(data)
        df.to_csv(save_file+'.csv', index=False)

    def device_info(self):
        device_info = u"""<?xml version="1.0" encoding="UTF-8" ?><bts version="1.0"><cmd>getdevinfo</cmd></bts>\n\n#\r\n"""
        return self.sendRecvMsg(device_info)

    def close(self):
        """
        Close the port
        """
        self.neware_socket.close()

    def __del__(self):
        self.close()