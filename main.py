# main.py
import asyncio
from typing import Union
from datetime import datetime

import sys
import led_driver
import light_goggles
import socket
from constants import NUM_LED, UDP_IP, UDP_PORT, r, SPI_BUS, SPI_DEVICE, SPI_SPEED_HZ, BRIGHTNESS
from fastapi import FastAPI
from tags import tags_metadata

def read_hardware_config_file():
    with open('/etc/default/lc8823-demo', 'r') as f:
        defaults = {k[0] : k[1] for k in [x.strip('\n').split('=') for x in f.readlines()]}
    return defaults

def write_hardware_config_file():
    with open('/etc/default/lc8823-demo', 'w') as f:
        f.write("SPI_SPEED=1500000\nLED_BRIGHTNESS=5\nSPI_PROGRAM=flashen.py\n")

def setup_goggles():
    defaults = read_hardware_config_file()

    #Initialize Strip
    strip = led_driver.APA102(num_led=NUM_LED, 
                                global_brightness=int(defaults['LED_BRIGHTNESS']), 
                                SPI_BUS=SPI_BUS, 
                                SPI_DEVICE=SPI_DEVICE,
                                SPI_SPEED_HZ=int(defaults['SPI_SPEED']))  # Initialize the strip

    #Initialize UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(0)


    #Initialize Goggles
    lg = light_goggles.LightGoggles(strip, sock)
    return lg

lg = setup_goggles()
app = FastAPI(openapi_tags=tags_metadata,
              title="Resonate Labs Chair Control Service",
              description="An API to control a Resonate Chair.",
              version="0.0.1",
              terms_of_service="http://example.com/terms/",
              contact={
                  "name": "SweetLou",
                  "email": "lward@ipponusa.com",
              },
              license_info={
                  "name": "Apache 2.0",
                  "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
              },)

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    #loop.create_task(lg.get_new_variables())
    loop.create_task(lg.receive_vid_stream())
    loop.create_task(lg.manage_rest_mode())

@app.get("/")
async def read_root():
    return {"Welcoe to Resoante Light Goggles, check the DOCS at /docs"}

@app.get("/goggles", tags=["State"]) #effectively returns goggles current state
async def read_goggle_state():
    return {"brightness": lg.strip.global_brightness, 
            "color_divider": lg.color_divider,
            "rest_mode": lg.rest_mode,
            "last_socket_communication": datetime.fromtimestamp(lg.last_received_socket_communication),
            }

@app.get("/goggles/hardware", tags=["Hardware Config"])
async def read_hardware_config():
    return read_hardware_config_file()

@app.post("/goggles/hardware/{config}", tags=["Hardware Config"])
async def update_hardware_config():
    write_hardware_config_file()
    return("beep boop")

@app.get("/goggles/dimmer", tags=["Dimmer Control"])
async def read_dimmer():
    return {"dimmer": lg.color_divider}

@app.post("/goggles/dimmer/{dimmer}", tags=["Dimmer Control"])
async def set_dimmer(dimmer: int):
    lg.color_divider = dimmer
    return {"dimmer": dimmer}




