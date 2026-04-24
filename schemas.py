from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

# ========== Kandang ==========
class KandangBase(BaseModel):
    nama: str
    lokasi: Optional[str] = None

class KandangCreate(KandangBase):
    pass

class KandangResponse(KandangBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ========== Lantai ==========
class LantaiBase(BaseModel):
    kandang_id: int
    nama: str

class LantaiCreate(LantaiBase):
    pass

class LantaiResponse(LantaiBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ========== Actuator ==========
class ActuatorBase(BaseModel):
    lantai_id: int
    name: str
    type: str
    mode: Optional[str] = None
    current_status: Optional[bool] = False
    current_value: Optional[float] = None

class ActuatorCreate(ActuatorBase):
    pass

class ActuatorResponse(ActuatorBase):
    uuid: str
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ActuatorPatch(BaseModel):
    current_status: Optional[bool] = None
    current_value: Optional[float] = None

# ========== Blower Config ==========
class BlowerConfigBase(BaseModel):
    interval_on_duration: int
    interval_off_duration: int
    min_temperature: float
    max_temperature: float

class BlowerConfigCreate(BlowerConfigBase):
    actuator_id: str

class BlowerConfigResponse(BlowerConfigBase):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

# ========== Pump Config ==========
class PumpConfigBase(BaseModel):
    interval_on_duration: int
    interval_off_duration: int

class PumpConfigCreate(PumpConfigBase):
    actuator_id: str

class PumpConfigResponse(PumpConfigBase):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

# ========== Dimmer Config ==========
class DimmerConfigBase(BaseModel):
    min_brightness: int
    max_brightness: int

class DimmerConfigCreate(DimmerConfigBase):
    actuator_id: str

class DimmerConfigResponse(DimmerConfigBase):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

# ========== Heater Config ==========
class HeaterConfigBase(BaseModel):
    min_temperature: float
    max_temperature: float

class HeaterConfigCreate(HeaterConfigBase):
    actuator_id: str

class HeaterConfigResponse(HeaterConfigBase):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

# ========== Audit Log ==========
class AuditLogResponse(BaseModel):
    id_log: int
    actuator_id: str
    parameter_yang_diubah: str
    nilai_lama: Optional[str]
    nilai_baru: Optional[str]
    waktu_perubahan: datetime
    model_config = ConfigDict(from_attributes=True)