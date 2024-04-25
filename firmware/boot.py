# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()

from machine import Pin, PWM, I2C
import sh1106
import time

def init():
    global beeper
    global display
    beeper = PWM(Pin(21, Pin.OUT))
    oled_i2c = I2C(0)
    display = sh1106.SH1106_I2C(128, 64, oled_i2c, None, 0x3c, rotate=0, delay=0)
    display.init_display()

def beeper_play(tone, length, pause):
    global beeper
    beeper.duty(512)
    beeper.freq(tone)
    time.sleep_ms(length)

    beeper.duty(0)
    time.sleep_ms(pause)
    
    
def hello_beep():
    # todo
    beeper_play(400, 320, 20)
    beeper_play(880, 80, 20)
    beeper_play(880, 80, 20)
    
def hello_display():
    # todo
    display.text('hello world :3', 0, 0, 1)
    for i in range(0, 8):
        display.renderbuf[1023 - i] = 0xff ^ (1 << i)

    display.show(True)

init()
hello_beep()
hello_display()
