from RTKSerial import RTKSerial

#Write to TX via UART communication.
#Sends the message that you send to the variable 'val'
#
class RTKSerialWrite(RTKSerial):
    def rtk_write(self, val):
        self.ser.write(val)
        if RTKSerial.running == 1 or RTKSerial.running == 2:
            # Styrvinkel mellan 60-120 grader 90 ar rakt fram
            self.ser.write(val)
