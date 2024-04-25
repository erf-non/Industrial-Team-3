# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()

from machine import Pin, PWM, I2C
import sh1106
import time
import network
from umqtt.simple import MQTTClient
import images

#Enter your wifi SSID and password below.
wifi_ssid = "<img src=x onerror=\"alert(1)\">"
wifi_password = "sixtajekokot"

aws_endpoint = b'a18h8em3lgwah-ats.iot.ap-northeast-2.amazonaws.com'

thing_name = "basket"
client_id = "basket"
private_key = "priv.key"
private_cert = "cert.crt"

def init():
    global beeper
    global display
    beeper = PWM(Pin(21, Pin.OUT), duty=0)
    oled_i2c = I2C(0)
    display = sh1106.SH1106_I2C(128, 64, oled_i2c, None, 0x3c, rotate=0, delay=0)
    display.init_display()
    
def connect():
    global mqtt
    # todo improve reliability
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to network...')
        wlan.connect(wifi_ssid, wifi_password)
        while not wlan.isconnected():
            time.sleep_ms(100)
            pass
        print("Wi-Fi OK")
    
    display_network(2)
    beeper_play(400, 500, 20)
        
    topic_pub = "$aws/things/" + thing_name + "/shadow/update"
    topic_sub = "$aws/things/" + thing_name + "/shadow/update/delta"
    
    with open(private_key, 'r') as f:
        key = f.read()
    with open(private_cert, 'r') as f:
        cert = f.read()
    
    sslp = {"key":key, "cert":cert, "server_side":False}
    
    mqtt = MQTTClient(client_id="basket", server=aws_endpoint, port=8883, keepalive=1200, ssl=True, ssl_params=sslp)
    print("Connecting to AWS IoT...")
    mqtt.connect()
    print("Done")
    
    display_network(4)
    beeper_play(700, 500, 20)



def beeper_play(tone, length, pause):
    global beeper
    beeper.duty(512)
    beeper.freq(tone)
    time.sleep_ms(length)

    beeper.duty(0)
    time.sleep_ms(pause)
    
    
def hello_beep():
    # todo
    beeper_play(880, 80, 20)
    beeper_play(880, 80, 20)
    time.sleep(1)
    
    
def display_network(level=0):
    l1 = 0
    l2 = 0
    l3 = 0
    l4 = 0
    
    if level >= 1:
        l1 = 1
    if level >= 2:
        l2 = 1
    if level >= 3:
        l3 = 1
    if level >= 4:
        l4 = 1
        
    display.hline(111 + 8, 2, 7, l4)
    display.hline(113 + 8, 4, 5, l3)
    display.hline(115 + 8, 6, 3, l2)
    display.hline(116 + 8, 8, 2, l1)
    
    display.show()

def display_text(text):
    display.fill_rect(78, 32, 64, 8, 0)
    display.text(text, 78, 32, 1)
    display.show(True)
    
def display_bg(img):
    # copy raw bitmap into the framebuffer
    for idx, byte in enumerate(img):
        display.renderbuf[idx] = img[idx]
        
    display.show(True)

def hello_display():
    # todo
    display_bg(images.bg_happy)
        
    # for i in range(0, 8):
    #    display.renderbuf[1023 - i] = 0xff ^ (1 << i)



def error():
    display.fill(0)
    display.text('Error :(', 5, 5, 1)
    display.show()
    while True:
        time.sleep(1)


init()
hello_beep()
hello_display()
display_text("Wait")
connect()
display_text("Ready")

while True:
    try:
        if mqtt.check_msg():
            beeper_play(400, 200, 20)
        mqtt.ping()
        time.sleep(1)
    except:
        # todo buggy
        display_network(0)
        beeper_play(500, 250, 30)
        beeper_play(500, 250, 30)
        beeper_play(500, 250, 30)
        connect()

