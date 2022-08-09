import asyncio
import time

# start = time.time()

# print(23*2.3)

# end = time.time()
# print(end - start)

class LightGoggles:
    def __init__(self, strip, sock):
        self.strip = strip
        self.sock = sock
    
    async def receive_vid_stream(self):
        while True:
            data, addr = self.sock.recvfrom(512)
            # parse the bytes, splitting by newline-bytes
            lines = data.split(b'\n')
            # get the 4th line, or skip.
            if len(lines) < 4:
                print("here lines < 4")
                continue

            colors = lines[3]
            print(colors)

            if len(colors) < 3:
                print("here colors < 3")
                continue

            for i in range(self.strip.num_led):  # fill the strip with the same color
                self.strip.set_pixel(i, 
                    colors[0]//self.strip.global_brightness, 
                    colors[1]//self.strip.global_brightness, 
                    colors[2]//self.strip.global_brightness,
                    1)  # 1% brightness, but does not seem to make any difference
            self.strip.show()

            await asyncio.sleep(0)