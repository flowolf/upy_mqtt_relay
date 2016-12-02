import machine
import time
import network
import socket
import ubinascii
import json
from umqtt.robust import MQTTClient

NETWORK_CONNECT_TIMEOUT = 60 #seconds
DEV_ID = "uPy-{0}".format(ubinascii.hexlify(machine.unique_id()).decode('utf-8'))

# TODO implement settings file for WIFI, MQTT etc.
# enable settings edit after reset button pressed

# you can put multiple networks here,
# device will try to connect to reachable ones
MY_NETS = {
            #"your_net1": "password1",
            #"your_net2": "password2",
          }

print("sleep at the beginning...")
time.sleep(1)

led = machine.Pin(2,machine.Pin.OUT,value=1)
led.low() # blue led on ESP8266 module is reversed
mqtt_server = "10.0.0.17" # your MQTT server
topic = "/socket/uPy/"+ DEV_ID

# button needs to be pulled down with 1kR
button = machine.Pin(5, machine.Pin.IN) # Nodemcu D1

state = 0
stati = [b"off",b"on"]
relay = machine.Pin(12,machine.Pin.OUT) # Nodemcu D6
relay.value(state)

mqtt_user = "mymqttuser"
mqtt_pw = "mymqttpassword"

wlan = network.WLAN(network.STA_IF)
def do_connect():
    print("getting network")
    network_connect_start_time = time.ticks_ms()
    import network

    if not wlan.active():
        led.high() # off
        wlan.active(True)
    nets = wlan.scan()
    for net in nets:
        net = net[0].decode('utf-8')
        if net in MY_NETS and not wlan.isconnected():
            print('connecting to network: {}'.format(net))
            wlan.connect(net, MY_NETS[net])#, timeout=5000)
            while not wlan.isconnected():
                if wlan.status() == network.STAT_IDLE:
                    print("ERROR: nothing going on")
                    break
                # if wlan.status() == network.STAT_CONNECTING:
                #     print("INFO: connecting to network")
                if wlan.status() == network.STAT_GOT_IP:
                    print("INFO: what are you doing here, shouldn't be here...")
                if wlan.status() == network.STAT_WRONG_PASSWORD or\
                    wlan.status() == network.STAT_NO_AP_FOUND or\
                    wlan.status() == network.STAT_CONNECT_FAIL:

                    print("ERROR: wifi has issues ({})".format(wlan.status()))
                    break
                if (network_connect_start_time + NETWORK_CONNECT_TIMEOUT*1000) < time.ticks_ms():
                    print("ERROR: network timeout. trying other network, or sleeping")
                    break
                machine.idle()
    print('network config:', wlan.ifconfig())

c = MQTTClient(DEV_ID, mqtt_server, user=mqtt_user, password=mqtt_pw)

def switch_callback(topic_now, msg):
    global state
    print((topic_now, msg))
    #if topic_now == topic:
    if msg == stati[1]: # on
        led.value(1) # led off
        relay.high()
        state = 1
        c.publish(topic + "/status", stati[state], retain=True)
        print("State is: %s" % state)
    elif msg == stati[0]: # off
        led.value(0) # led on
        relay.low()
        state = 0
        c.publish(topic + "/status", stati[state], retain=True)
        print("State is: %s" % state)
    elif msg == b"toggle":
        toggle()

def toggle():
    global state
    state = 1 - state
    led.value(state)
    relay.value(state)
    c.publish(topic + "/status", stati[state], retain=True)
    print("State is: %s" % state)

def button_pressed():
    but_val = button.value()
    time.sleep_ms(250)
    if not but_val == button.value() and button.value() == 1:
        return True
    return False

# TODO implement reset button

while True:
    do_connect()

    try:
        c.set_callback(switch_callback)
        print("connecting MQTT client...")
        c.connect()
        c.subscribe(topic)
        print("Connected to %s, subscribed to %s topic" % (mqtt_server, topic))
        print("State is: %s" % state)
        while True:
            c.check_msg()
            if button_pressed():
                print("button pressed")
                toggle()

    except:
        print("ERROR: connecting or sending data to MQTT server!")
    finally:
        c.disconnect()

    print("endless loop...")
