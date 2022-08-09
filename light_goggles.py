import asyncio

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
                continue
            colors = lines[3]
            #try:
                #print(f"R:{colors[0]}, G:{colors[1]}, B:{colors[2]}")
            #except:
            print(colors)

            # print("parsed color: {}".format(colors))
            # coerce colors as a list of ints
            # colors2 = [int(c) for c in colors]
            # print("parsed colors2: {}".format(colors2))
            # if we have at least 3 colors values, display them in the strip, otherwise skip
            if len(colors) < 3:
                continue
        # y = b''.join([bytes([x[0]]), bytes([x[1]]), bytes([x[2]])]) 
            # print("parsed lines: {}".format(lines))
            # print(colored(colors[0], colors[1], colors[2], "O")) # show ANSI colors for debugging

            for i in range(self.strip.num_led):  # fill the strip with the same color
                self.strip.set_pixel(i, 
                    colors[0]//self.strip.global_brightness, 
                    colors[1]//self.strip.global_brightness, 
                    colors[2]//self.strip.global_brightness,
                    1)  # 1% brightness, but does not seem to make any difference
            self.strip.show()
            await asyncio.sleep(0)

    async def get_new_variables(self):
        while(True):
            await asyncio.sleep(1)
            print("Getting new variables now!")