from boot import pyb
from drivers.sensor.AHT import get_temperature


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


led_loop_test()
pyb.delay(500)
led_loop_test()
