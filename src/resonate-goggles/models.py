from pydantic import BaseModel, Field

class HardwareConfig(BaseModel):
    spi_speed: int = Field(default = 150000)
    led_brightness: int = Field(default = 1, gt=0, le=20)
    dimmer_level: int = Field(default = 1, gt=0, le=100)

class BrightnessControl(BaseModel):
    dimmer_level: int = Field(default=1, gt=0, le=100)