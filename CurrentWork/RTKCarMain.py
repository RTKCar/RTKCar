import queue
import socket
import threading
import select
import serial
import logging
import time
import datetime
import sys
import multiprocessing


#sys.setswitchinterval(0.05)
"""
START:81
START:81
STOP:2
START:4:81
MANUAL:w:1/0:3,4,5 beroende på om knappen är nertryckt eller ej 1 = tryck, 0 = släpp
om w = 1 skall bilen rulla om 0 skall bilena stanna, samma med s.
om a eller d = 1 skall en tråd med en viss timer börja svänger på hjulen tills dom blir = 0
SPEED:3,4,5
 meddelanden från oliver
 
Oliver vill ha
1:cm:0,1,2 vänster mitten höger
"""

ser = serial.Serial(
    port='/dev/serial0',
    baudrate=500000,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=None
)

logger = logging.getLogger('test') #Create a log with the same name as the script that created it
logger.setLevel(logging.DEBUG)
#Create handlers and set their logging level
filehandler_dbg = logging.FileHandler(logger.name + '-debug.log', mode='w')
filehandler_dbg.setLevel(logging.DEBUG)
#Create custom formats of the logrecord fit for both the logfile and the console
streamformatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s') #We only want to see certain parts of the message
#Apply formatters to handlers
filehandler_dbg.setFormatter(streamformatter)
#Add handlers to logger
logger.addHandler(filehandler_dbg)

host = '192.168.43.140'
#host = '172.20.10.5'
port = 9001
buffer_size = 1024

styrvinkel_max_hoger = 30
styrvinkel_max_vanster = 90
current_angle = 90
current_speed = 2

car_start = '6:3:0:0:0:0:0:0:0\n'
car_stop = '6:2:0:0:0:0:0:0:0\n'

running = True
stop_auto = False
inet_connection = True
send_queue = multiprocessing.Queue()
receive_queue = multiprocessing.Queue()
handle_sensor = multiprocessing.Queue()
serial_out = multiprocessing.Queue()
handle_data = multiprocessing.Queue()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setblocking(0)


def serial_handler():
    global ser, handle_sensor, serial_out
    while True:
        readable, writable, _ = select.select([ser], [ser], [])
        for read in readable:
            if read is ser:
                if ser.in_waiting > 0:
                    data = ser.readline().decode()
                    #print(data + " " + str(handle_sensor.qsize()))
                    logger.info('Thread 1: Serial in: %s' % data)
                    handle_sensor.put(data)
        if serial_out.qsize() > 0:
            data = serial_out.get()
            print(data)
            logger.info('Thread 1: Serial out: %s' % data)
            #print("Data start send serial by PI to serial: " + str(data) + " " + str(datetime.datetime.now()))
            ser.write(data.encode())
            #print("Data done send serial by PI to serial: " + str(data) + " " + str(datetime.datetime.now()))


def process_sensor_data():
    global stop_auto, inet_connection, current_speed, handle_sensor, send_queue
    while True:
        if handle_sensor.qsize() > 0:
            information = handle_sensor.get()
            information = information.split(':')
            if len(information) > 3:
                can_id = information[0]
                left = information[1]
                middle = information[2]
                right = information[3]
                if str(can_id) == '15':
                    logger.info('Thread 2: Sensor data: %s' % information)
                    #print('inside Checking sensor data')
                    #print("Sensor data med id 15: " + str(can_id) + " left: " + str(left) + " middle: " + str(middle) + " right: " + str(right) + " size " + str(handle_sensor.qsize()))
                    if (1 <= int(left) < 200 or 1 <= int(middle) < 200 or 1 <= int(right) < 200):
                        if int(left) < int(middle) and int(left) < int(right):
                     #       print('VANSTER')
                            send_queue.put('1:' + str(left) + ',0')
                        elif int(middle) < int(left) and int(middle) < int(right):
                     #       print('MITTEN')
                            send_queue.put('1:' + str(middle) + ',1')
                        elif int(right) < int(middle) and int(right) < int(left):
                     #       print('HOGER')
                            send_queue.put('1:' + str(right) + ',2')
                        # Skicka via socket "ObjectDetected,Avstand"
                        serial_out.put(car_stop)
                        logger.info('Thread 2: Car will stop')
                        stop_auto = True
                    elif not stop_auto:
                        serial_out.put(str(current_speed))
                        logger.info('Thread 2: Car will start')
                        stop_auto = False
        else:
            time.sleep(0.05)


def pi_client():
    global stop_auto, handle_data, send_queue
    connected = False
    while not connected:
        try:
            sock.connect((host, port))

            connected = True
        except Exception as e:
            pass
    while True:
        readable, writable, error = select.select([sock], [sock], [sock])
        for read in readable:
            if read is sock:
                #print("Data start received by PI: " + " " + str(datetime.datetime.now()))
                data = sock.recv(1024).decode('utf-8')
                #print(data)
                #print("Data done start received by PI: " + str(data) + " " + str(datetime.datetime.now()))
                if data:
                    logger.info('Thread 3: Server data in: %s' % data)
                #    print("Data from oliver " + data)
                    handle_data.put(data)
        for write in writable:
            if write is sock:
                if send_queue.qsize() > 0:
                    data = send_queue.get()
                    logger.info('Thread 3: Server data out: %s' % data)
                #    print("Data to oliver " + data)
                    sock.send(data.encode('utf-8'))


def internet(h="8.8.8.8", p=53, timeout=3):
    global inet_connection
    time.sleep(1)
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((h, p))
        inet_connection = True
    except Exception as ex:
        inet_connection = False


def steering(vinkel):
    global running, current_angle
    while running:
        current_angle += vinkel
        print("VINKEL PA STYR: " + str(current_angle))
        serial_out.put('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')
        time.sleep(0.2)

def handledata():

    control_angle = ["", ""]
    drive = ["", ""]
    first_time = True
    steering_thread = threading.Thread()
    global current_angle, current_speed, running
    while True:
        if handle_data.qsize() > 0:
            #print("Data start processed by PI: " + str(datetime.datetime.now()))
            all_messages = handle_data.get().split(';')
            for x in all_messages:
                current_message = x.split(':')
                if current_message[0] == 'START':
                    if first_time:
                        #current_speed = 3
                        #serial_out.put('6:' + str(current_speed) + ':0:0:0:0:0:0:0\n')
                        first_time = False
                    print("From Aidin styrvinkel: " + str(current_message[1]))
                    logger.info('Thread 4: Serial out: %s' % current_message[1])
                    result = ''.join([i for i in current_message[1] if i.isdigit()])
                    current_angle = int(result)
                    if styrvinkel_max_hoger < current_angle < styrvinkel_max_vanster:
                        serial_out.put('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')
                    elif current_angle > styrvinkel_max_vanster:
                        current_angle = styrvinkel_max_vanster
                        serial_out.put('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')
                    elif current_angle < styrvinkel_max_hoger:
                        current_angle = styrvinkel_max_hoger
                        serial_out.put('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')

                elif current_message[0] == 'STOP':
                    first_time = True
                    current_speed = 2
                    serial_out.put('6:' + str(current_speed) + ':0:0:0:0:0:0:0\n')

                elif current_message[0] == 'MANUAL':
                    first_time = True
                    if current_message[1].lower() == 'w':
                        if current_message[2] == '1' and not drive[0].lower() == 's':
                            if current_speed == 2:
                                current_speed = 3
                            drive[0] = current_message[1]
                            drive[1] = current_message[2]
                            serial_out.put('6:' + str(current_speed) + ':0:0:0:0:0:0:0\n')

                        elif current_message[2] == '0' and drive[0].lower() == 'w':
                            drive[0] = ""
                            drive[1] = ""
                            serial_out.put('6:2:0:0:0:0:0:0:0\n')

                    elif current_message[1].lower() == 's':
                        if current_message[2] == '1' and not drive[0].lower() == 'w':
                            drive[0] = current_message[1]
                            drive[1] = current_message[2]
                            serial_out.put('6:1:0:0:0:0:0:0:0\n')

                        elif current_message[2] == '0' and drive[0].lower() == 's':
                            drive[0] = ""
                            drive[1] = ""
                            serial_out.put('6:2:0:0:0:0:0:0:0\n')

                    elif current_message[1].lower() == 'a':
                        if current_message[2] == '1' and not control_angle[0].lower() == 'd':
                            running = True
                            control_angle[0] = current_message[1]
                            control_angle[1] = current_message[2]
                            steering_thread = threading.Thread(target=steering, args=(2,))
                            steering_thread.start()
                        elif current_message[2] == '0' and control_angle[0].lower() == 'a':
                            control_angle[0] = ""
                            control_angle[1] = ""
                            running = False
                            steering_thread.join()

                    elif current_message[1].lower() == 'd':
                        if current_message[2] == '1' and not  control_angle[0].lower() == 'a':
                            running = True
                            control_angle[0] = current_message[1]
                            control_angle[1] = current_message[2]
                            steering_thread = threading.Thread(target=steering, args=(-2,))
                            steering_thread.start()
                        elif current_message[2] == '0' and control_angle[0].lower() == 'd':
                            control_angle[0] = ""
                            control_angle[1] = ""
                            running = False
                            steering_thread.join()

                elif current_message[0] == 'SPEED':
                    current_speed = int(current_message[1])
                    serial_out.put('6:' + str(current_speed) + ':0:0:0:0:0:0:0\n')
            #print("Data done processed by PI: " + str(datetime.datetime.now()))
        else:
            time.sleep(0.01)


if __name__ == '__main__':
    serial_han = multiprocessing.Process(target=serial_handler)
    pi = multiprocessing.Process(target=pi_client)
    sendata = multiprocessing.Process(target=process_sensor_data)
    handata = multiprocessing.Process(target=handledata)
    serial_han.daemon = True
    sendata.daemon = True
    pi.daemon = True
    handata.daemon = True
    handata.start()
    serial_han.start()
    sendata.start()
    pi.start()

    while True:
        pass
