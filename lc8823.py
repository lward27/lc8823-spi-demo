import spidev
import sys
import time
from math import ceil

NUM_LED = 122
RGB_MAP = {'rgb': [3, 2, 1], 'rbg': [3, 1, 2], 'grb': [2, 3, 1],
           'gbr': [2, 1, 3], 'brg': [1, 3, 2], 'bgr': [1, 2, 3]}


class APA102:
    """
    Driver for APA102 LEDS (aka "DotStar").

    (c) Martin Erzberger 2016-2020

    Public methods are:
     - set_pixel
     - set_pixel_rgb
     - get_pixel
     - get_pixel_rgb
     - show
     - clear_strip
     - cleanup

    Helper methods for color manipulation are:
     - combine_color
     - wheel

    The rest of the methods are used internally and should not be used by the
    user of the library. This file is the main driver, and is usually used "as is".

    Very brief overview of APA102: An APA102 LED is addressed with SPI. The bits
    are clocked in one by one, starting with the least significant bit.

    An LED usually just copies everything that is sent to its data-in to
    data-out. While doing this, it remembers its own color and keeps glowing
    with that color as long as there is power.

    An LED can be switched to not forward the data, but instead use the data
    to change it's own color. This is done by sending (at least) 32 bits of
    zeroes to data-in. The LED then accepts the next correct 32 bit LED
    frame (with color information) as its new color setting.

    After having received the 32 bit color frame, the LED changes color,
    and then resumes to just copying data-in to data-out.

    The really clever bit is this: While receiving the 32 bit LED frame,
    the LED sends zeroes on its data-out line. Because a color frame is
    32 bits, the LED sends 32 bits of zeroes to the next LED.
    As we have seen above, this means that the next LED is now ready
    to accept a color frame and update its color.

    So that's really the entire protocol:
    - Start by sending 32 bits of zeroes. This prepares LED 1 to update
      its color.
    - Send color information one by one, starting with the color for LED 1,
      then LED 2 etc.
    - Finish off by cycling the clock line a few times to get all data
      to the very last LED on the strip

    The last step is necessary, because each LED delays forwarding the data
    a bit. Imagine ten people in a row. When you tell the last color
    information, i.e. the one for person ten, to the first person in
    the line, then you are not finished yet. Person one has to turn around
    and tell it to person 2, and so on. So it takes ten additional "dummy"
    cycles until person ten knows the color. When you look closer,
    you will see that not even person 9 knows its own color yet. This
    information is still with person 2. Essentially the driver sends additional
    zeroes to LED 1 as long as it takes for the last color frame to make it
    down the line to the last LED.
    """
    # Constants
    LED_START = 0b11100000  # Three "1" bits, followed by 5 brightness bits

    def __init__(self, num_led=8, order='rgb', global_brightness=4):
        """Initializes the library

        :param num_led: Number of LEDs in the strip
        :param order: Order in which the colours are addressed (this differs from strip to strip)
        :param global_brightness: This is a 5 bit value, i.e. from 0 to 31.
        """

        # Just in case someone use CAPS here.
        order = order.lower()

        self.num_led = num_led
        self.rgb = RGB_MAP.get(order, RGB_MAP['rgb'])
        self.global_brightness = global_brightness
        self.order = 'rbg'  # Strip colour ordering

        self.leds = [self.LED_START, 0, 0, 0] * self.num_led  # Pixel buffer

        self.spi = spidev.SpiDev(SPI_BUS, SPI_DEVICE)
        self.spi.max_speed_hz = SPI_SPEED_HZ
        # print("SPI speed: ", self.spi.max_speed_hz)

    def clock_start_frame(self):
        """Sends a start frame to the LED strip.

        This method clocks out a start frame, telling the receiving LED
        that it must update its own color now.
        """
        self.send_to_spi(bytes([0] * 4))

    def clock_end_frame(self):
        """Sends an end frame to the LED strip.

        As explained above, dummy data must be sent after the last real colour
        information so that all of the data can reach its destination down the line.
        The delay is not as bad as with the human example above.
        It is only 1/2 bit per LED. This is because the SPI clock line
        is being inverted by the LED chip.

        Say a bit is ready on the SPI data line. The sender communicates
        this by toggling the clock line. The bit is read by the LED
        and immediately forwarded to the output data line. When the clock goes
        down again on the input side, the LED will toggle the clock up
        on the output to tell the next LED that the bit is ready.

        After one LED the clock is inverted, and after two LEDs it is in sync
        again, but one cycle behind. Therefore, for every two LEDs, one bit
        of delay gets accumulated. For 300 LEDs, 150 additional bits must be fed to
        the input of LED one so that the data can reach the last LED.

        Ultimately, we need to send additional numLEDs/2 arbitrary data bits,
        in order to trigger numLEDs/2 additional clock changes. This driver
        sends zeroes, which has the benefit of getting LED one partially or
        fully ready for the next update to the strip. An optimized version
        of the driver could omit the "clockStartFrame" method if enough zeroes have
        been sent as part of "clockEndFrame".
        """
        # Send reset frame necessary for SK9822 type LEDs
        self.send_to_spi(bytes([0] * 4))
        for _ in range((self.num_led + 15) // 16):
            self.send_to_spi([0x00])

    def set_global_brightness(self, brigtness):
        """ Set the overall brightness of the strip."""
        self.global_brightness = brigtness

    def clear_strip(self):
        """ Turns off the strip and shows the result right away."""

        for led in range(self.num_led):
            self.set_pixel(led, 0, 0, 0)
        self.show()

    def set_pixel(self, led_num, red, green, blue, bright_percent=100):
        """Sets the color of one pixel in the LED stripe.

        The changed pixel is not shown yet on the Stripe, it is only
        written to the pixel buffer. Colors are passed individually.
        If brightness is not set the global brightness setting is used.
        """
        if led_num < 0:
            return  # Pixel is invisible, so ignore
        if led_num >= self.num_led:
            return  # again, invisible

        # Calculate pixel brightness as a percentage of the
        # defined global_brightness. Round up to nearest integer
        # as we expect some brightness unless set to 0
        brightness = ceil(bright_percent * self.global_brightness / 100.0)
        brightness = int(brightness)

        # LED start frame is three "1" bits, followed by 5 brightness bits
        ledstart = (brightness & 0b00011111) | self.LED_START

        start_index = 4 * led_num
        self.leds[start_index] = ledstart
        self.leds[start_index + self.rgb[0]] = red
        self.leds[start_index + self.rgb[1]] = green
        self.leds[start_index + self.rgb[2]] = blue

    def set_pixel_rgb(self, led_num, rgb_color, bright_percent=100):
        """Sets the color of one pixel in the LED stripe.

        The changed pixel is not shown yet on the Stripe, it is only
        written to the pixel buffer.
        Colors are passed combined (3 bytes concatenated)
        If brightness is not set the global brightness setting is used.
        """
        self.set_pixel(led_num, (rgb_color & 0xFF0000) >> 16,
                       (rgb_color & 0x00FF00) >> 8, rgb_color & 0x0000FF,
                       bright_percent)

    def get_pixel(self, led_num):
        """Gets the color and brightness of one pixel in the LED stripe.

        This won't be the color that is actually shown on the stripe,
        but rather the value stored in memory.
        """
        if led_num < 0:
            return  # Pixel is invisible, so ignore
        if led_num >= self.num_led:
            return  # again, invisible

        output = {"red": 0, "green": 0, "blue": 0, "brightness": 0}
        start_index = 4 * led_num

        # Filter out the three start bits
        output["bright_percent"] = self.leds[start_index] & 0b00011111
        output["red"] = self.leds[start_index + self.rgb[0]]
        output["green"] = self.leds[start_index + self.rgb[1]]
        output["blue"] = self.leds[start_index + self.rgb[2]]

        # Recalculate the percentage brightness
        # This won't be the precise value that was passed to set_pixel
        # But it will be the value used by the LED
        output["bright_percent"] = output["bright_percent"] * 100 / self.global_brightness

        return output

    def get_pixel_rgb(self, led_num):
        """Gets the color of one pixel in the LED stripe.

        This won't be the color that is actually show on the stripe,
        but rather the value stored in memory.
        Colors are combined (3 bytes concatenated)
        """
        output = {"rgb_color": 0, "brightness": 0}
        pixel = self.get_pixel(led_num)

        output["rgb_color"] = pixel["red"] << 8 | pixel["green"] << 8 | pixel["blue"]
        output["bright_percent"] = pixel["bright_percent"]

        return output

    def rotate(self, positions=1):
        """Rotate the LEDs by the specified number of positions.

        Treating the internal LED array as a circular buffer, rotate it by
        the specified number of positions. The number could be negative,
        which means rotating in the opposite direction.
        """
        cutoff = 4 * (positions % self.num_led)
        self.leds = self.leds[cutoff:] + self.leds[:cutoff]

    def show(self):
        """Sends the content of the pixel buffer to the strip.

        Todo: More than 1024 LEDs requires more than one xfer operation.
        """
        self.clock_start_frame()
        # xfer2 kills the list, unfortunately. So it must be copied first
        # SPI takes up to 4096 Integers. So we are fine for up to 1024 LEDs.
        self.send_to_spi(self.leds)
        self.clock_end_frame()

    def cleanup(self):
        """Release the SPI device; Call this method at the end"""
        self.clear_strip()
        # print("deinit!")
        self.spi.close()  # Close SPI port

    @staticmethod
    def combine_color(red, green, blue):
        """Make one 3*8 byte color value."""

        return (red << 16) + (green << 8) + blue

    def wheel(self, wheel_pos):
        """Get a color from a color wheel; Green -> Red -> Blue -> Green"""

        if wheel_pos > 255:
            wheel_pos = 255  # Safeguard
        if wheel_pos < 85:  # Green -> Red
            return self.combine_color(wheel_pos * 3, 255 - wheel_pos * 3, 0)
        if wheel_pos < 170:  # Red -> Blue
            wheel_pos -= 85
            return self.combine_color(255 - wheel_pos * 3, 0, wheel_pos * 3)
        # Blue -> Green
        wheel_pos -= 170
        return self.combine_color(0, wheel_pos * 3, 255 - wheel_pos * 3)

    def send_to_spi(self, data):
        """Internal method to output data to the chosen SPI device"""
        # @TODO: actual writing
        # self.spi.write(data)
        # print(data)
        self.spi.writebytes2(data)

    def dump_array(self):
        """For debug purposes: Dump the LED array onto the console."""

        print(self.leds)


class ColorCycleTemplate:
    """This class is the basis of all color cycles.
    This file is usually used "as is" and not being changed.

    A specific color cycle must subclass this template, and implement at least the
    'update' method.
    """

    def __init__(self, num_led, pause_value=0, num_steps_per_cycle=100, num_cycles=-1, global_brightness=4):
        self.num_led = num_led  # The number of LEDs in the strip
        self.pause_value = pause_value  # How long to pause between two runs
        self.num_steps_per_cycle = num_steps_per_cycle  # Steps in one cycle.
        self.num_cycles = num_cycles  # How many times will the program run
        self.global_brightness = global_brightness  # Overall brightness of the strip

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
        strip = None
        try:
            strip = APA102(num_led=self.num_led, global_brightness=self.global_brightness)  # Initialize the strip
            strip.clear_strip()
            self.init(strip, self.num_led)  # Call the subclasses init method
            strip.show()
            current_cycle = 0
            while True:  # Loop forever
                for current_step in range(self.num_steps_per_cycle):
                    need_repaint = self.update(strip, self.num_led,
                                               self.num_steps_per_cycle,
                                               current_step, current_cycle)
                    if need_repaint:
                        strip.show()  # repaint if required
                    time.sleep(self.pause_value)  # Pause until the next step
                current_cycle += 1
                if self.num_cycles != -1 and current_cycle >= self.num_cycles:
                    break
            # Finished, cleanup everything
            self.cleanup(strip)

        except KeyboardInterrupt:  # Ctrl-C can halt the light program
            print('Interrupted...')
            if strip is not None:
                strip.cleanup()


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


SPI_BUS = 1
SPI_DEVICE = 0
SPI_SPEED_HZ = 500000
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

print("SPI_BUS:", SPI_BUS)
print("SPI_DEVICE:", SPI_DEVICE)
print("SPI_SPEED_HZ:", SPI_SPEED_HZ)
print("BRIGHTNESS:", BRIGHTNESS)

# One Cycle with one step and a pause of two seconds. Hence two seconds of white light
print('Two Seconds of white light')
my_cycle = Solid(num_led=NUM_LED, pause_value=2,
                 num_steps_per_cycle=1, num_cycles=1, global_brightness=BRIGHTNESS)
my_cycle.start()

# Go twice around the clock
print('Go twice around the clock')
my_cycle = RoundAndRound(num_led=NUM_LED, pause_value=0, num_steps_per_cycle=NUM_LED, num_cycles=2,
                         global_brightness=BRIGHTNESS)
my_cycle.start()

# One cycle of red, green and blue each
print('One strandtest of red, green and blue each')
my_cycle = StrandTest(num_led=NUM_LED, pause_value=0, num_steps_per_cycle=NUM_LED, num_cycles=3,
                      global_brightness=BRIGHTNESS)
my_cycle.start()

# Five quick trips through the rainbow
print('Five quick trips through the rainbow')
my_cycle = TheaterChase(num_led=NUM_LED, pause_value=0.04, num_steps_per_cycle=35, num_cycles=5,
                        global_brightness=BRIGHTNESS)
my_cycle.start()

# Ten slow trips through the rainbow
print('Ten slow trips through the rainbow')
my_cycle = Rainbow(num_led=NUM_LED, pause_value=0, num_steps_per_cycle=255, num_cycles=10,
                   global_brightness=BRIGHTNESS)
my_cycle.start()
