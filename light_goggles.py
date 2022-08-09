import asyncio
import time
#from goggle_light_show_templates import show_R
from constants import r


class LightGoggles:
    """
    A class used to represent a pair of Resonate Light Goggles

    ...

    Attributes
    ----------
    strip : APA102
        An object representing an LED Strip
    sock : socket
        An object representing a unix socket
    rest_mode : boolean
        Represents if the goggles are currently in restmode, if false, something is playing!
    last_received_socket_communication : int
        the linux time that last communication was received over the socket
    last_last_received_socket_communication : int
        the linux time that the time before last communication was received over the socket
        combined with previous attributes, the goggles object has knowledge if information is
        flowing over the socket

    Methods
    -------
    show_R()
        Displays the Resonate "R" on the light goggles, used for Rest Mode
    show_solid_color(colors)
        accepts a byte string of colors.  Colors are represented by 3 2 digit hexidecimal
        values, i.e. 24 bit color.
    async receive_vid_stream()
        Streams video to light goggles over socket
    async manage_rest_mode()
        Handles turning restmode on when nothing is coming over the socket

    """
    def __init__(self, strip, sock, rest_mode=True, color_divider=1):
        self.strip = strip # Initialized in main.py
        self.sock = sock # Initialized in main.py
        self.rest_mode = rest_mode # Goggles start in rest mode
        self.last_received_socket_communication = time.time() 
        self.last_last_received_socket_communication = self.last_received_socket_communication-1
        self.color_divider = color_divider

    def show_R(self):
        for i in range(len(r)):  # fill the strip with the same color
                    # R image is stored in constants.py file
                    self.strip.set_pixel(i, r[i][0], r[i][1], r[i][2], 
                                        1)  # 1% brightness, but does not seem to make any difference
        self.strip.show() 
    
    def show_solid_color(self, colors):
        for i in range(self.strip.num_led):  # fill the strip with the same color
            self.strip.set_pixel(i, 
                colors[0]//self.color_divider, 
                colors[1]//self.color_divider, 
                colors[2]//self.color_divider,
                1)  # 1% brightness, but does not seem to make any difference
        self.strip.show()

    def fade(self):
        current_pixel = self.strip.get_pixel(0)
        print(current_pixel)
        
        for j in range(100):
            for i in range(self.strip.num_led):
                self.strip.set_pixel(i, 
                    current_pixel["red"]//(j+1), 
                    current_pixel["blue"]//(j+1), 
                    current_pixel["green"]//(j+1),
                    1)  # 1% brightness, but does not seem to make any difference
            self.strip.show()
            time.sleep(.01)

    async def receive_vid_stream(self):
        while True:
            # Try, because this is non-blocking socket, if no communcation
            # comes over the socket, a BlockingIOError is thrown
            try:
                data, addr = self.sock.recvfrom(512)
                self.rest_mode = False # If we make it this far, socket comms are happening
                # Capture last received data - used for rest mode.
                self.last_received_socket_communication = time.time()
                # parse the bytes, splitting by newline-bytes
                lines = data.split(b'\n')
                # get the 4th line, or skip.
                if len(lines) < 4:
                    continue

                colors = lines[3]
                if len(colors) < 3: # Skip color values that don't make sense!
                    continue
                self.show_solid_color(colors)

            except BlockingIOError:
                #print("nothing to stream")
                continue

            finally:
                await asyncio.sleep(0) #give control back to the loop regardless of socket comms.

    async def manage_rest_mode(self):
        while True:
            print(self.last_received_socket_communication) # Debug
            if(self.last_received_socket_communication == self.last_last_received_socket_communication):
                #print("nothing playing for 5 seconds, starting rest mode...")
                if(self.rest_mode == False):
                    self.fade()
                self.rest_mode = True
                self.show_R()
            self.last_last_received_socket_communication = self.last_received_socket_communication
            await asyncio.sleep(5) # Toggle how long rest_mode takes to start up.

