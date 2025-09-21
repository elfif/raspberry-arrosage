#!/usr/bin/python
# -*- coding:UTF-8 -*-

import RPi.GPIO as GPIO

Relay = [5, 6, 13, 16, 19, 20, 21, 26]

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

def close_all_relays():
    for i in range(0,8):
        GPIO.setup(Relay[i], GPIO.OUT)
        GPIO.output(Relay[i], GPIO.HIGH)

def open_all_relays():
    for i in range(0,8):
        GPIO.setup(Relay[i], GPIO.OUT)
        GPIO.output(Relay[i], GPIO.LOW)

def open_relay(relay_number):
    GPIO.setup(Relay[relay_number], GPIO.OUT)
    GPIO.output(Relay[relay_number], GPIO.LOW)

def close_relay(relay_number):
    GPIO.setup(Relay[relay_number], GPIO.OUT)
    GPIO.output(Relay[relay_number], GPIO.HIGH)

# def main():
#     close_all_relays()
#     open_relay(7)
#     time.sleep(10)
#     close_relay(7)

# if __name__ == "__main__":
#     main()