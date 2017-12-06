
import socket
from threading import Thread
from RTKSerial import RTKSerial

host = '172.20.10.6'
port = 8888
buffer_size = 2000


class PiClient(Thread, RTKSerial):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        tcpClientA = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connected = False
        while not connected:
            try:
                tcpClientA.connect((host, port))
                connected = True
            except Exception as e:
                pass
        while RTKSerial.running == 1:
            data = tcpClientA.recv(buffer_size)
            if data:
                RTKSerial.srvMsg.append(data) #pop
                # MESSAGE = raw_input("tcpClientA: Enter message to continue/ Enter exit:")
                # tcpClientA.close()

