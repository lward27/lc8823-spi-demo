# main.py
import asyncio
from typing import Union
from datetime import datetime

import led_driver
import light_goggles
import socket
from constants import NUM_LED, UDP_IP, UDP_PORT, r
from fastapi import FastAPI
from tags import tags_metadata
from models import BrightnessControl

hardware_config_options = {}

def read_hardware_config_file():
    with open('/etc/default/lc8823-demo', 'r') as f:
        hardware_config_options = {k[0] : k[1] for k in [x.strip('\n').split('=') for x in f.readlines()]}
    return hardware_config_options

def setup_goggles():
    defaults = read_hardware_config_file()
    print(defaults)

    #Initialize Strip
    strip = led_driver.APA102(num_led=NUM_LED, 
                                global_brightness=int(defaults['LED_BRIGHTNESS']), 
                                SPI_BUS=defaults['SPI_BUS'], 
                                SPI_DEVICE=['SPI_DEVICE'],
                                SPI_SPEED_HZ=int(defaults['SPI_SPEED_HZ']))  # Initialize the strip

    #Initialize UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(0)


    #Initialize Goggles
    lg = light_goggles.LightGoggles(strip, sock, dimmer_level=int(defaults["DIMMER_LEVEL"])) #DIMMER_LEVEL becomes dimmer_level inside the Light Goggles class
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

@app.on_event("shutdown")
def shutdown_event():
    lg.strip.clear_strip()

@app.get("/")
async def read_root():
    return {"Welcoe to Resoante Light Goggles, check the DOCS at /docs"}

@app.get("/goggles", tags=["State"]) #effectively returns goggles current state
async def read_goggle_state():
    return {"brightness": lg.strip.global_brightness, 
            "dimmer_level": lg.dimmer_level,
            "rest_mode": lg.rest_mode,
            "last_socket_communication": datetime.fromtimestamp(lg.last_received_socket_communication),
            }

@app.get("/goggles/hardware", tags=["Hardware Config"])
async def read_hardware_config():
    return read_hardware_config_file()

@app.get("/goggles/dimmer", response_model=BrightnessControl, tags=["Dimmer Control"])
async def read_dimmer():
    dimmer_level = lg.dimmer_level
    return {"dimmer_level":dimmer_level}

@app.post("/goggles/dimmer", tags=["Dimmer Control"])
async def set_dimmer(dimmer_control: BrightnessControl):
    lg.dimmer_level = dimmer_control.dimmer_level
    return {"dimmer": dimmer_control}




