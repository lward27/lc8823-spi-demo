from pydantic import BaseModel

class HardwareConfig(BaseModel):
    spi_speed: int = 150000
    led_brightness: int = 1