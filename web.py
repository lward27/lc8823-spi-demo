from typing import Union
import sys
import led_driver
import light_goggles
import socket
from constants import NUM_LED, UDP_IP, UDP_PORT
import lc8823

from fastapi import FastAPI
import asyncio

async def printstuff():
    while True:
        await asyncio.sleep(1)
        print("beep!")

async def main(lg):
    await asyncio.gather(lg.get_new_variables(), lg.receive_vid_stream())

SPI_BUS = 1
SPI_DEVICE = 0
SPI_SPEED_HZ = 500000 * 3
BRIGHTNESS = 1  # Is already too bright

if len(sys.argv) > 1:
    print("Setting SPI_BUS to %s" % sys.argv[1])
    SPI_BUS = int(sys.argv[1])

if len(sys.argv) > 2:
    print("Setting SPI_DEVICE to %s" % sys.argv[2])
    SPI_DEVICE = int(sys.argv[2])

if len(sys.argv) > 3:
    print("Setting SPI_SPEED_HZ to %s" % sys.argv[3])
    SPI_SPEED_HZ = int(sys.argv[3])

if len(sys.argv) > 4:
    print("Setting BRIGHTNESS to %s" % sys.argv[4])
    BRIGHTNESS = int(sys.argv[4])

if len(sys.argv) > 5:
    print("Setting PROGRAM to %s" % sys.argv[5])
    PROGRAM = str(sys.argv[5])

print("SPI_BUS:", SPI_BUS)
print("SPI_DEVICE:", SPI_DEVICE)
print("SPI_SPEED_HZ:", SPI_SPEED_HZ)
print("BRIGHTNESS:", BRIGHTNESS)
print("PROGRAM:", PROGRAM)

#Initialize Strip
strip = led_driver.APA102(num_led=NUM_LED, 
                            global_brightness=BRIGHTNESS, 
                            SPI_BUS=SPI_BUS, 
                            SPI_DEVICE=SPI_DEVICE,
                            SPI_SPEED_HZ=SPI_SPEED_HZ)  # Initialize the strip

#Initialize UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

#Initialize Goggles
lg = light_goggles.LightGoggles(strip, sock)


app = FastAPI()

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    loop.create_task(lg.get_new_variables())
    loop.create_task(lg.receive_vid_stream())

@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
