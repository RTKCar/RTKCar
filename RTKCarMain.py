from RTKSerialRead import RTKSerialRead
from RTKSerialWrite import RTKSerialWrite
from RTKSerial import RTKSerial
from PiClient import PiClient
import time






a = RTKSerialRead()
b = RTKSerialWrite()
c = RTKSerial()
d = PiClient()

a.start()
d.start()
loopvar = True

while loopvar:
    if c.srvMsg:
        data = c.srvMsg.pop()
        if data == 'stop':
            #b.rtk_write(data)
            print("%s is equal to stop" %data)
            loopvar = False
        else:
            print(data)

RTKSerial.running = 0
a.join()
d.join()
#time.sleep(4)
#b.rtk_write('10:80:2:100:3:70:120:150:56\n')
#b.rtk_write('\n')
#time.sleep(1)
#print('10:100:0:0:0:0:0:0:0\n')
#b.rtk_write('10:100:0:0:0:0:0:0:0\n')
#time.sleep(2)
#print('10:120:0:0:0:0:0:0:0\n')
#b.rtk_write('10:120:0:0:0:0:0:0:0\n')

#time.sleep(1)
#RTKSerial.stop = 1
#time.sleep(1)
#RTKSerial.running = 0
#time.sleep(1)
#a.join()
