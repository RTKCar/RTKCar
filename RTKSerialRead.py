#!/usr/bin/env python
# -*- coding: utf-8 -*-
import serial
import time
import re
from RTKSerial import RTKSerial
from threading import Thread

    #RTKSerialRead(Thread, RTKSerial)
    #Runns on its own thread to check if there is any incoming information from CAN Buss
    #Only reacts of there is a decimal value lesser then 200(cm)
    #
class RTKSerialRead(Thread, RTKSerial):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        r = re.compile('.*:.*:.*:.*:.*:.*:.*:.*')
        while RTKSerial.stop == 0:
            while RTKSerial.running == 1:
                if RTKSerial.running == 1:
                    theLine = self.ser.readline()
                    if r.match(theLine) is not None:
                        theLine = theLine.split(':', 9)
                        self.check_information(theLine)
                        #print("I got: %s and Running is: %s" % (theLine, RTKSerial.running))



    #check_information(self, information)
    #Checks if the incoming values from the sensors are < 200 cm and if they are
    #sets running to 0 so the car stops
    #information is the entire message that has be received
    #Writes to CANBuss pririty 6(Drivsystem) and information 0 so the car stops
    #TODO perhaps fix the ser.write so its done properly
    def check_information(self, information):
        if information[0] == '15':
            index = [1, 2, 3]
            left, middle, right = [information[i] for i in index]
            print("left: %s middle: %s right: %s" % (left, middle, right))
            #if int(left) < 20 or int(middle) < 20 or int(right) < 20:
             #   print("left: %s middle: %s right: %s" % (left, middle, right))
                #RTKSerial.ser.write('6:0\n')
                #RTKSerial.running = 0
            #else:
                #RTKSerial.running = 1
             #   print("left: %s middle: %s right: %s" % (left, middle, right))
