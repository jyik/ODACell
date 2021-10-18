import paramiko
import datetime
import time
print('{}:     Starting Script...'.format(datetime.datetime.now()))


keyfilename = 'C:\\Users\\renrum\\ot2_ssh_key'
k = paramiko.RSAKey.from_private_key_file(keyfilename, 'otto')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname='169.254.100.142', username='root', pkey=k)
ssh_channel = ssh.invoke_shell()
ssh_channel.send('cd /var/lib/jupyter/notebooks\n'.encode())
time.sleep(0.5)
if ssh_channel.recv_ready():
    output = ssh_channel.recv(1024)
    print(output.decode())

while True:
    command = input()
    if command == 'q':
        break
    if command == 'exit':
        ssh_channel.send("exit\n".encode())
        break
    ssh_channel.send((command + "\n").encode())
    time.sleep(0.3)
    if ssh_channel.recv_ready():
        output = ssh_channel.recv(1024)
        print(output.decode())

ssh.close()