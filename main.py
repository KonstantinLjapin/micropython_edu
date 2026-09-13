from boot import pyb
from drivers.sensor.AHT import get_temperature
from drivers.sensor.mpu_6050 import get_accelerometer_test
from drivers.sensor.gy271 import get_compass
from drivers.sensor.uln2003 import driver_test
from motor_control import motor_set_compass
def led_loop_test():
    for i in range(1, 5):
        pyb.LED(i).on()
        pyb.delay(200)
        pyb.LED(i).off()
        pyb.delay(200)


def get_temperature_test():
    for i in range(1, 5):
        get_temperature(scl='X9', sda='X10')
        pyb.delay(500)
        print("LED", i, "ON")
        pyb.LED(i).on()
        pyb.delay(1000)
        print("LED", i, "OFF")
        pyb.LED(i).off()
        pyb.delay(1000)


def get_accelerometer():
    while True:
        get_accelerometer_test(scl='Y9', sda='Y10')
        pyb.delay(1000)


def start_compass():
    get_compass(sda='X10', slc='X9')


def driver_run_test(step_type):
    """

    :param step_type: only 'f' \ 'h'
    :return:
    """
    print("go motor one round")
    driver_test(step=step_type, in1='X1', in2='X2', in3='X3', in4='X4')


def m_s_c():
    motor_set_compass()


led_loop_test()
pyb.delay(500)
led_loop_test()
