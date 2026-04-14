from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class LogResponse(BaseModel):
    id: int
    actuator_id: str
    parameter_yang_diubah: str
    nilai_lama: str
    nilai_baru: str
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

# Blower Schemas
class BlowerUpdate(BaseModel):
    interval_on_duration: int
    interval_off_duration: int
    min_temperature: float
    max_temperature: float

class BlowerResponse(BlowerUpdate):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

class BlowerCreate(BaseModel):
    actuator_id: str
    interval_on_duration: int = 10
    interval_off_duration: int = 5
    min_temperature: float = 25.0
    max_temperature: float = 30.0

# Pump Schemas
class PumpUpdate(BaseModel):
    interval_on_duration: int
    interval_off_duration: int

class PumpResponse(PumpUpdate):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

class PumpCreate(BaseModel):
    actuator_id: str
    interval_on_duration: int = 8
    interval_off_duration: int = 4

# Dimmer Schemas
class DimmerUpdate(BaseModel):
    min_brightness: int
    max_brightness: int

class DimmerResponse(DimmerUpdate):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

class DimmerCreate(BaseModel):
    actuator_id: str
    min_brightness: int = 0
    max_brightness: int = 100

# Heater Schemas
class HeaterUpdate(BaseModel):
    min_temperature: float
    max_temperature: float

class HeaterResponse(HeaterUpdate):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

class HeaterCreate(BaseModel):
    actuator_id: str
    min_temperature: float = 20.0
    max_temperature: float = 35.0

# Device Type Enum
class DeviceType(BaseModel):
    type: str  # blower, pump, dimmer, heater