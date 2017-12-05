
import socket
from threading import Thread
from RTKSerial import RTKSerial

host = '127.0.0.1'
port = 8888
buffer_size = 2000


class PiClient(Thread, RTKSerial):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        tcpClientA = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpClientA.connect((host, port))
        while True:
            data = tcpClientA.recv(buffer_size)
            if data:
                RTKSerial.srvMsg = data
                print(data)
                # MESSAGE = raw_input("tcpClientA: Enter message to continue/ Enter exit:")
                # tcpClientA.close()

