
import machine
import pyb



print("sdsdsd")

def LED_loop_test():
    for i in range(1, 5):
        pyb.LED(i).on()
        pyb.delay(200)
        pyb.LED(i).off()
        pyb.delay(200)


LED_loop_test()
pyb.delay(500)
LED_loop_test()


