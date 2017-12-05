from RTKSerialRead import RTKSerialRead
from RTKSerialWrite import RTKSerialWrite
from RTKSerial import RTKSerial
import time






a = RTKSerialRead()
b = RTKSerialWrite()
c = RTKSerial()




a.start()
time.sleep(4)
b.rtk_write('Hej\n')
#b.rtk_write('\n')
time.sleep(1)
b.rtk_write('R\n')
time.sleep(2)
b.rtk_write('Test\n')

time.sleep(1)
RTKSerial.stop = 1
time.sleep(1)
RTKSerial.running = 0
time.sleep(1)
a.join()
