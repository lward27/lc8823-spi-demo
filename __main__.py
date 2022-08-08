# main.py
import asyncio
import sys
import led_driver
import light_goggles
import socket
from constants import NUM_LED, UDP_IP, UDP_PORT
import lc8823

def run_demo(lg):
    # One Cycle with one step and a pause of two seconds. Hence two seconds of white light
    print('Two Seconds of white light')
    my_cycle = lc8823.Solid(num_led=lg.strip.num_led, strip=lg.strip, pause_value=2,
                    num_steps_per_cycle=1, num_cycles=1, global_brightness=lg.strip.global_brightness)
    my_cycle.start()

    # Go twice around the clock
    print('Go twice around the clock')
    my_cycle = lc8823.RoundAndRound(num_led=lg.strip.num_led, strip=lg.strip, pause_value=0, num_steps_per_cycle=NUM_LED, num_cycles=2,
                            global_brightness=lg.strip.global_brightness)
    my_cycle.start()

    # One cycle of red, green and blue each
    print('One strandtest of red, green and blue each')
    my_cycle = lc8823.StrandTest(num_led=lg.strip.num_led, strip=lg.strip, pause_value=0, num_steps_per_cycle=NUM_LED, num_cycles=3,
                        global_brightness=lg.strip.global_brightness)
    my_cycle.start()

    # Five quick trips through the rainbow
    print('Five quick trips through the rainbow')
    my_cycle = lc8823.TheaterChase(num_led=lg.strip.num_led, strip=lg.strip, pause_value=0.04, num_steps_per_cycle=35, num_cycles=5,
                            global_brightness=lg.strip.global_brightness)
    my_cycle.start()

    # Ten slow trips through the rainbow
    print('Ten slow trips through the rainbow')
    my_cycle = lc8823.Rainbow(num_led=lg.strip.num_led, strip=lg.strip, pause_value=0, num_steps_per_cycle=255, num_cycles=10,
                    global_brightness=lg.strip.global_brightness)
    my_cycle.start()
    lg.strip.clear_strip()

async def main(lg):
    await asyncio.gather(lg.get_new_variables(), lg.receive_vid_stream())



if __name__ == "__main__":

    ## TODO: READ COMMAND LINES, named command line args
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

    if(PROGRAM == "flashen.py"):
        asyncio.run(main(lg))
    if(PROGRAM == "lc8823.py"):
        run_demo(lg)
        asyncio.run(main(lg))



