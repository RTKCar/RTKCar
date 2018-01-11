import socket
import threading
import select
import serial
import logging
import time
import multiprocessing
from threading import Timer

"""
    Initiera serial variabeln ser
"""
ser = serial.Serial(
    port='/dev/serial0',
    baudrate=500000,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=None
)


"""
    Initierar logger med namnet RTKCarMain
    Denna variabeln används för att logga
"""
logger = logging.getLogger('RTKCarMain')
logger.setLevel(logging.DEBUG)
filehandler_dbg = logging.FileHandler(logger.name + '-debug.log', mode='w')
filehandler_dbg.setLevel(logging.DEBUG)
streamformatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
filehandler_dbg.setFormatter(streamformatter)
logger.addHandler(filehandler_dbg)


"""
    host = Vilken ip address servern ar pa
    port = Vilken port du vill oppna på din sida
    buffersize = viken storlek buffern skall ha
"""
host = '192.168.43.140'
#host = '172.20.10.5'
port = 9001
buffer_size = 1024
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setblocking(0)

"""
    Globala variabler
"""
styrvinkel_max_hoger = 15
styrvinkel_max_vanster = 75
current_angle = 45
current_speed = 2
car_start = '6:3:0:0:0:0:0:0:0\n'
car_stop = '6:2:0:0:0:0:0:0:0\n'
running = True
stop_auto = False
inet_connection = True


"""
    Queues dit data laggs samt hamtas ifrån olika processer.
    
"""
sock_data_out = multiprocessing.Queue()
sock_data_in = multiprocessing.Queue()
serial_data_in = multiprocessing.Queue()
serial_data_out = multiprocessing.Queue()

"""
    serial_handler
    Kollar ser variablen om det finns data om det gör det skickas datan till serial_data_in Queue
    Om det finns data i serial_data_out skickas den ut via ser variabeln
"""


def serial_handler():
    global ser, serial_data_in, serial_data_out
    while True:
        logger.info('Process 1: Starts')
        readable, writable, _ = select.select([ser], [ser], [])
        for read in readable:
            if read is ser:
                if ser.in_waiting > 0:
                    data = ser.readline().decode()
                    logger.info('Process 1: Serial in: %s' % data)
                    serial_data_in.put(data)
        if serial_data_out.qsize() > 0:
            data = serial_data_out.get()
            logger.info('Process 1: Serial out: %s' % data)
            ser.write(data.encode())
        logger.info('Process 1: Ends')

"""
    process_sensor_data
    Kollar Queue serial_data_in och processar datan
    Om datan har id 15 och någon av deras mätvärden är under 200 stannar bilen och datan skickas vidare
    till sock_data_out
"""

def process_sensor_data():
    """pre: Proccessing all data serial_data_in
    post: puts the handled data in sock_data_out
    :return: nothing
    """
    global stop_auto, inet_connection, current_speed, serial_data_in, sock_data_out
    timer = Timer(1, sensor_timer)
    while True:
        logger.info('Process 2: Starts')
        if serial_data_in.qsize() > 0:
            information = serial_data_in.get()
            information = information.split(':')
            if len(information) > 3:
                can_id = information[0]
                left = information[1]
                middle = information[2]
                right = information[3]
                fast_list = []
                fast_list.append(int(left))
                fast_list.append(int(middle))
                fast_list.append(int(right))
                fast_list = [x for x in fast_list if x != 0]
                fast_list.sort()
                minimum = 0
                if fast_list:
                    minimum = fast_list.pop(0)
                if str(can_id) == '15':
                    print(str(minimum))
                    logger.info('Process 2: Sensor data: %s' % information)
                    if minimum != 0:
                        if minimum == int(left) and minimum < 100:
                            print(minimum)
                            sock_data_out.put('1:' + str(minimum) + ',0')
                            serial_data_out.put(car_stop)
                            logger.info('Process 2: Car will stop')
                            stop_auto = True

                            if timer.is_alive():
                                timer.cancel()
                            timer = Timer(2, sensor_timer)
                            timer.start()

                        elif minimum == int(middle) and minimum < 100:
                            print(minimum)
                            sock_data_out.put('1:' + str(minimum) + ',1')
                            serial_data_out.put(car_stop)
                            logger.info('Process 2: Car will stop')
                            stop_auto = True

                            if timer.is_alive():
                                timer.cancel()
                            timer = Timer(2, sensor_timer)
                            timer.start()

                        elif minimum == int(right) and minimum < 100:
                            print(minimum)
                            sock_data_out.put('1:' + str(minimum) + ',2')
                            serial_data_out.put(car_stop)
                            logger.info('Process 2: Car will stop')
                            stop_auto = True

                            if timer.is_alive():
                                timer.cancel()
                            timer = Timer(2, sensor_timer)
                            timer.start()
        logger.info('Process 2: Ends')


def sensor_timer():
    global stop_auto
    if stop_auto:
        serial_data_out.put(str(current_speed))
        logger.info('Process 2: Car will start speed %s' % current_speed)
        print("Car will start")
        stop_auto = False


"""
    pi_client
    Clienten läser inkommande data som vidare läggs i Queue sock_data_in
    Om det finns data som skall skickas i sock_data_out skickas den via socketen
"""


def pi_client():
    global sock_data_in, sock_data_out
    connected = False
    while not connected:
        try:
            sock.connect((host, port))
            connected = True
        except Exception as e:
            pass
    while True:
        logger.info('Process 3: Starts')
        readable, writable, error = select.select([sock], [sock], [sock])
        for read in readable:
            if read is sock:
                data = sock.recv(1024).decode('utf-8')
                if data:
                    logger.info('Process 3: Server data in: %s' % data)
                    sock_data_in.put(data)
        for write in writable:
            if write is sock:
                if sock_data_out.qsize() > 0:
                    data = sock_data_out.get()
                    logger.info('Process 3: Server data out: %s' % data)
                    sock.send(data.encode('utf-8'))
        logger.info('Process 3: Ends')


def internet(h="8.8.8.8", p=53, timeout=3):
    global inet_connection
    time.sleep(1)
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((h, p))
        inet_connection = True
    except Exception as ex:
        inet_connection = False


"""
    steering
    Denna tråden svänger bilen 'vinkel' grader var 0.2 sekunder
"""


def steering(vinkel):
    global running, current_angle
    while running:
        current_angle += vinkel
        if styrvinkel_max_hoger < current_angle < styrvinkel_max_vanster:
            logger.info('Thread steering: Steering Change: %s' % current_angle)
            serial_data_out.put('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')
        elif current_angle > styrvinkel_max_vanster:
            current_angle = styrvinkel_max_vanster
            logger.info('Thread steering: Steering Change: %s' % current_angle)
            serial_data_out.put('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')
        elif current_angle < styrvinkel_max_hoger:
            current_angle = styrvinkel_max_hoger
            logger.info('Thread steering: Steering Change: %s' % current_angle)
            serial_data_out.put('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')
        time.sleep(0.2)


"""
    handle_sock_data
    Kollar 'sock_data_in' om det finns data processas den och gör lämpliga val
"""


def handle_sock_data():
    control_angle = ["", ""]
    drive = ["", ""]
    first_time = True
    steering_thread = threading.Thread()
    global current_angle, current_speed, running
    while True:
        logger.info('Process 4: Starts')
        if sock_data_in.qsize() > 0:
            all_messages = sock_data_in.get().split(';')
            for x in all_messages:
                current_message = x.split(':')
                if current_message[0] == 'START':
                    if first_time:
                        first_time = False
                        current_speed = 5
                        if not stop_auto:
                            logger.info('Process 4: Speed Change: %s' % current_speed)
                            serial_data_out.put('6:' + str(current_speed) + ':0:0:0:0:0:0:0\n')
                    result = ''.join([i for i in current_message[1] if i.isdigit()])
                    print("styrvinkel från aidin: " + str(result))
                    current_angle = int(result)
                    logger.info("Real angle: " + str(current_angle))
                    current_angle = (current_angle * -1) + 45
                    print("current Angle: " + str(current_angle))
                    if styrvinkel_max_hoger < current_angle < styrvinkel_max_vanster:
                        data = ('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')
                        logger.info('Process 4: serial out: %s' % data)
                        serial_data_out.put(data)
                    elif current_angle > styrvinkel_max_vanster:
                        current_angle = styrvinkel_max_vanster
                        data = ('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')
                        logger.info('Process 4: serial out: %s' % data)
                        serial_data_out.put(data)
                    elif current_angle < styrvinkel_max_hoger:
                        current_angle = styrvinkel_max_hoger
                        data = ('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')
                        logger.info('Process 4: serial out: %s' % data)
                        serial_data_out.put(data)

                elif current_message[0] == 'STOP':
                    first_time = True
                    current_speed = 2
                    logger.info('Process 4: Car STOP')
                    serial_data_out.put('6:' + str(current_speed) + ':0:0:0:0:0:0:0\n')

                elif current_message[0] == 'MANUAL':
                    first_time = True
                    logger.info('Process 4: MANUAL')
                    if current_message[1].lower() == 'w':
                        if current_message[2] == '1' and not drive[0].lower() == 's':
                            if current_speed == 2:
                                current_speed = 3
                            drive[0] = current_message[1]
                            drive[1] = current_message[2]
                            serial_data_out.put('6:' + str(current_speed) + ':0:0:0:0:0:0:0\n')
                            logger.info('Process 4: MANUAL Speed change %s' % current_speed)

                        elif current_message[2] == '0' and drive[0].lower() == 'w':
                            drive[0] = ""
                            drive[1] = ""
                            current_speed = 2
                            logger.info('Process 4: MANUAL STOP')
                            serial_data_out.put('6:' + str(current_speed) + ':0:0:0:0:0:0:0\n')

                    elif current_message[1].lower() == 's':
                        if current_message[2] == '1' and not drive[0].lower() == 'w':
                            drive[0] = current_message[1]
                            drive[1] = current_message[2]
                            current_speed = 1
                            logger.info('Process 4: MANUAL BACKING')
                            serial_data_out.put('6:' + str(current_speed) + ':0:0:0:0:0:0:0\n')

                        elif current_message[2] == '0' and drive[0].lower() == 's':
                            drive[0] = ""
                            drive[1] = ""
                            logger.info('Process 4: MANUAL STOP')
                            current_speed = 2
                            serial_data_out.put('6:' + str(current_speed) + ':0:0:0:0:0:0:0\n')

                    elif current_message[1].lower() == 'a':
                        if current_message[2] == '1' and not control_angle[0].lower() == 'd':
                            running = True
                            control_angle[0] = current_message[1]
                            control_angle[1] = current_message[2]
                            steering_thread = threading.Thread(target=steering, args=(2,))
                            steering_thread.start()
                            logger.info('Process 4: MANUAL Start steering and starting thread')
                        elif current_message[2] == '0' and control_angle[0].lower() == 'a':
                            control_angle[0] = ""
                            control_angle[1] = ""
                            running = False
                            steering_thread.join()
                            logger.info('Process 4: MANUAL Stop steering and starting thread')

                    elif current_message[1].lower() == 'd':
                        if current_message[2] == '1' and not  control_angle[0].lower() == 'a':
                            running = True
                            control_angle[0] = current_message[1]
                            control_angle[1] = current_message[2]
                            steering_thread = threading.Thread(target=steering, args=(-2,))
                            steering_thread.start()
                            logger.info('Process 4: MANUAL Start steering and starting thread')
                        elif current_message[2] == '0' and control_angle[0].lower() == 'd':
                            control_angle[0] = ""
                            control_angle[1] = ""
                            running = False
                            steering_thread.join()
                            logger.info('Process 4: MANUAL Stop steering and starting thread')

                elif current_message[0] == 'SPEED':
                    current_speed = int(current_message[1])
                    serial_data_out.put('6:' + str(current_speed) + ':0:0:0:0:0:0:0\n')
                    logger.info('Process 4: MANUAL Change speed %s' % current_speed)
        logger.info('Process 4: Ends')


if __name__ == '__main__':
    mp_serial_handler = multiprocessing.Process(target=serial_handler)
    mp_pi = multiprocessing.Process(target=pi_client)
    mp_sensor_data = multiprocessing.Process(target=process_sensor_data)
    mp_sock_data = multiprocessing.Process(target=handle_sock_data)
    mp_serial_handler.daemon = True
    mp_sensor_data.daemon = True
    mp_pi.daemon = True
    mp_sock_data.daemon = True
    mp_sock_data.start()
    mp_serial_handler.start()
    mp_sensor_data.start()
    mp_pi.start()

    while True:
        pass
