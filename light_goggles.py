import asyncio
import time
from goggle_light_show_templates import show_R
from constants import r

# start = time.time()

# print(23*2.3)

# end = time.time()
# print(end - start)

class LightGoggles:
    def __init__(self, strip, sock, rest_mode=True):
        self.strip = strip
        self.sock = sock
        self.rest_mode = rest_mode
        self.last_received_socket_communication = time.time()
        self.last_last_received_socket_communication = self.last_received_socket_communication-1

    def show_R(self):
        for i in range(len(r)):  # fill the strip with the same color
                    self.strip.set_pixel(i, r[i][0], r[i][1], r[i][2],
                                        1)  # 1% brightness, but does not seem to make any difference
        self.strip.show()

    
    async def receive_vid_stream(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(512)
                # Capture last received data - used for rest mode.
                self.last_received_socket_communication = time.time()
                
                # parse the bytes, splitting by newline-bytes
                lines = data.split(b'\n')
                # get the 4th line, or skip.
                if len(lines) < 4:
                    continue
                colors = lines[3]
                if len(colors) < 3:
                    continue
                for i in range(self.strip.num_led):  # fill the strip with the same color
                    self.strip.set_pixel(i, 
                        colors[0]//self.strip.global_brightness, 
                        colors[1]//self.strip.global_brightness, 
                        colors[2]//self.strip.global_brightness,
                        1)  # 1% brightness, but does not seem to make any difference
                self.strip.show()
            except BlockingIOError:
                #print("nothing to stream")
                continue
            finally:
                await asyncio.sleep(0)

    async def manage_rest_mode(self):
        while True:
            print(self.last_received_socket_communication)
            if(self.last_received_socket_communication == self.last_last_received_socket_communication):
                print("nothing playing for 5 seconds, starting rest mode...")
                self.show_R()
            self.last_last_received_socket_communication = self.last_received_socket_communication
            await asyncio.sleep(5)

