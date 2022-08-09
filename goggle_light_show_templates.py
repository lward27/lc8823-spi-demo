import spidev
import sys
import time
from math import ceil
from constants import NUM_LED, RGB_MAP, r


class ColorCycleTemplate:
    """This class is the basis of all color cycles.
    This file is usually used "as is" and not being changed.

    A specific color cycle must subclass this template, and implement at least the
    'update' method.
    """

    def __init__(self, num_led, strip, pause_value=0, num_steps_per_cycle=100, num_cycles=-1, global_brightness=4):
        self.num_led = num_led  # The number of LEDs in the strip
        self.pause_value = pause_value  # How long to pause between two runs
        self.num_steps_per_cycle = num_steps_per_cycle  # Steps in one cycle.
        self.num_cycles = num_cycles  # How many times will the program run
        self.global_brightness = global_brightness  # Overall brightness of the strip
        self.strip = strip

    def init(self, strip, num_led):
        """This method is called to initialize a color program.

        The default does nothing. A particular subclass could setup
        variables, or even light the strip in an initial color.
        """
        pass

    def shutdown(self, strip, num_led):
        """This method is called before exiting.

        The default does nothing
        """
        pass

    def update(self, strip, num_led, num_steps_per_cycle, current_step,
               current_cycle):
        """This method paints one subcycle. It must be implemented.

        current_step:  This goes from zero to numStepsPerCycle-1, and then
          back to zero. It is up to the subclass to define what is done in
          one cycle. One cycle could be one pass through the rainbow.
          Or it could be one pixel wandering through the entire strip
          (so for this case, the numStepsPerCycle should be equal to numLEDs).
        current_cycle: Starts with zero, and goes up by one whenever a full
          cycle has completed.
        """

        raise NotImplementedError("Please implement the update() method")

    def cleanup(self, strip):
        """Cleanup method."""
        self.shutdown(strip, self.num_led)
        strip.clear_strip()
        strip.cleanup()

    def start(self):
        """This method does the actual work."""
        #strip = None
        try:
            #strip = APA102(num_led=self.num_led, global_brightness=self.global_brightness)  # Initialize the strip
            self.strip.clear_strip()
            self.init(self.strip, self.num_led)  # Call the subclasses init method
            self.strip.show()
            current_cycle = 0
            while True:  # Loop forever
                for current_step in range(self.num_steps_per_cycle):
                    need_repaint = self.update(self.strip, self.num_led,
                                               self.num_steps_per_cycle,
                                               current_step, current_cycle)
                    if need_repaint:
                        self.strip.show()  # repaint if required
                    time.sleep(self.pause_value)  # Pause until the next step
                current_cycle += 1
                if self.num_cycles != -1 and current_cycle >= self.num_cycles:
                    break
            # Finished, cleanup everything
            #self.cleanup(self.strip)

        except KeyboardInterrupt:  # Ctrl-C can halt the light program
            print('Interrupted...')
            if self.strip is not None:
                self.strip.cleanup()


class StrandTest(ColorCycleTemplate):
    """Runs a simple strand test (9 LEDs wander through the strip)."""

    color = None

    def init(self, strip, num_led):
        self.color = 0x000000  # Initialize with black

    def update(self, strip, num_led, num_steps_per_cycle, current_step,
               current_cycle):
        # One cycle = The 9 Test-LEDs wander through numStepsPerCycle LEDs.
        if current_step == 0:
            self.color >>= 8  # Red->green->blue->black
        if self.color == 0:
            self.color = 0xFF0000  # If black, reset to red
        bloblen = 9
        if num_led - 1 < bloblen:
            bloblen = num_led - 3
        if num_led <= 0:
            bloblen = 1
            # The head pixel that will be turned on in this cycle
        head = (current_step + bloblen) % num_steps_per_cycle
        tail = current_step  # The tail pixel that will be turned off
        strip.set_pixel_rgb(head, self.color)  # Paint head
        strip.set_pixel_rgb(tail, 0)  # Clear tail

        return 1  # Repaint is necessary


class TheaterChase(ColorCycleTemplate):
    """Runs a 'marquee' effect around the strip."""

    def update(self, strip, num_led, num_steps_per_cycle, current_step,
               current_cycle):
        # One cycle = One trip through the color wheel, 0..254
        # Few cycles = quick transition, lots of cycles = slow transition
        # Note: For a smooth transition between cycles, numStepsPerCycle must
        # be a multiple of 7
        start_index = current_step % 7  # One segment is 2 blank, and 5 filled
        color_index = strip.wheel(int(round(255 / num_steps_per_cycle *
                                            current_step, 0)))
        for pixel in range(num_led):
            # Two LEDs out of 7 are blank. At each step, the blank
            # ones move one pixel ahead.
            if ((pixel + start_index) % 7 == 0) or ((pixel + start_index) % 7 == 1):
                strip.set_pixel_rgb(pixel, 0)
            else:
                strip.set_pixel_rgb(pixel, color_index)
        return 1


class RoundAndRound(ColorCycleTemplate):
    """Runs three LEDs around the strip."""

    def init(self, strip, num_led):
        strip.set_pixel_rgb(0, 0xFF0000)
        strip.set_pixel_rgb(1, 0xFF0000, 5)  # Only 5% brightness
        strip.set_pixel_rgb(2, 0xFF0000)

    def update(self, strip, num_led, num_steps_per_cycle, current_step,
               current_cycle):
        # Simple class to demonstrate the "rotate" method
        strip.rotate()
        return 1


class Solid(ColorCycleTemplate):
    """Paints the strip with one colour."""

    def update(self, strip, num_led, num_steps_per_cycle, current_step, current_cycle):
        stripcolour = 0xFFFFFF
        if current_step == 1:
            stripcolour = 0xFF0000
        if current_step == 2:
            stripcolour = 0x00FF00
        if current_step == 3:
            stripcolour = 0x0000FF
        for led in range(0, num_led):
            strip.set_pixel_rgb(led, stripcolour, 5)  # Paint 5% white
        return 1


class Rainbow(ColorCycleTemplate):
    """Paints a rainbow effect across the entire strip."""

    def update(self, strip, num_led, num_steps_per_cycle, current_step,
               current_cycle):
        # One cycle = One trip through the color wheel, 0..254
        # Few cycles = quick transition, lots of cycles = slow transition
        # -> LED 0 goes from index 0 to 254 in numStepsPerCycle cycles.
        #     So it might have to step up more or less than one index
        #     depending on numStepsPerCycle.
        # -> The other LEDs go up to 254, then wrap around to zero and go up
        #     again until the last one is just below LED 0. This way, the
        #     strip always shows one full rainbow, regardless of the
        #     number of LEDs
        scale_factor = 255 / num_led  # Index change between two neighboring LEDs
        start_index = 255 / num_steps_per_cycle * current_step  # LED 0
        for i in range(num_led):
            # Index of LED i, not rounded and not wrapped at 255
            led_index = start_index + i * scale_factor
            # Now rounded and wrapped
            led_index_rounded_wrapped = int(round(led_index, 0)) % 255
            # Get the actual color out of the wheel
            pixel_color = strip.wheel(led_index_rounded_wrapped)
            strip.set_pixel_rgb(i, pixel_color)
        return 1  # All pixels are set in the buffer, so repaint the strip now


async def show_R(lg):
    while(True):
        for i in range(len(r)):  # fill the strip with the same color
            lg.strip.set_pixel(i, r[i][0], r[i][1], r[i][2],
                                1)  # 1% brightness, but does not seem to make any difference
        lg.strip.show()
        time.sleep(0)

def run_demo(lg):
    # One Cycle with one step and a pause of two seconds. Hence two seconds of white light
    print('Two Seconds of white light')
    my_cycle = Solid(num_led=lg.strip.num_led, strip=lg.strip, pause_value=2,
                    num_steps_per_cycle=1, num_cycles=1, global_brightness=lg.strip.global_brightness)
    my_cycle.start()

    # Go twice around the clock
    print('Go twice around the clock')
    my_cycle = RoundAndRound(num_led=lg.strip.num_led, strip=lg.strip, pause_value=0, num_steps_per_cycle=NUM_LED, num_cycles=2,
                            global_brightness=lg.strip.global_brightness)
    my_cycle.start()

    # One cycle of red, green and blue each
    print('One strandtest of red, green and blue each')
    my_cycle = StrandTest(num_led=lg.strip.num_led, strip=lg.strip, pause_value=0, num_steps_per_cycle=NUM_LED, num_cycles=3,
                        global_brightness=lg.strip.global_brightness)
    my_cycle.start()

    # Five quick trips through the rainbow
    print('Five quick trips through the rainbow')
    my_cycle = TheaterChase(num_led=lg.strip.num_led, strip=lg.strip, pause_value=0.04, num_steps_per_cycle=35, num_cycles=5,
                            global_brightness=lg.strip.global_brightness)
    my_cycle.start()

    # Ten slow trips through the rainbow
    print('Ten slow trips through the rainbow')
    my_cycle = Rainbow(num_led=lg.strip.num_led, strip=lg.strip, pause_value=0, num_steps_per_cycle=255, num_cycles=10,
                    global_brightness=lg.strip.global_brightness)
    my_cycle.start()
    lg.strip.clear_strip()