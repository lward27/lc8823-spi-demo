# main.py
import asyncio
from typing import Union

import sys
import led_driver
import light_goggles
import socket
from constants import NUM_LED, UDP_IP, UDP_PORT, r, SPI_BUS, SPI_DEVICE, SPI_SPEED_HZ, BRIGHTNESS
from fastapi import FastAPI

defaults = None
with open('/etc/default/lc8823-demo', 'r') as f:
    defaults = {k[0] : k[1] for k in [x.strip('\n').split('=') for x in f.readlines()]}
print(defaults)

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

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    #loop.create_task(lg.get_new_variables())
    loop.create_task(lg.receive_vid_stream())
    loop.create_task(lg.manage_rest_mode())
    

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/goggles/brightness")
async def read_brightness():
    return {"brightness": lg.color_divider}

@app.post("/goggles/brightness/{brightness}")
async def set_brightness(brightness: int, q: Union[str, None] = None):
    lg.color_divider = brightness
    return {"brightness": brightness, "q": q}




