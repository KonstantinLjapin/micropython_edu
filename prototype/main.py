#this �ڲ�����
from pyb import Timer
from pyb import Switch
from pyb import Accel


# LED loop test
def LED_loop_test():
    for i in range(1, 5):
        pyb.LED(i).on()
        pyb.delay(100)
        pyb.LED(i).off()
        pyb.delay(100)


while True:
	accel = pyb.Accel()
	if (accel.y()>=15):
  	  pyb.LED(4).on()
	else:
  	  pyb.LED(4).off()

	if (accel.z()>=15):
  	  pyb.LED(3).on()
	else:
  	  pyb.LED(3).off()

	sw = Switch()
	sw.value() # returns True or False
	sw.callback(lambda: pyb.LED(2).toggle())









