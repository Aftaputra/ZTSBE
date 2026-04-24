from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Literal

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
    last_sync: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ActuatorPatch(BaseModel):
    current_status: Optional[bool] = None
    current_value: Optional[float] = None
    mode: Optional[str] = None

class ActuatorModeSwitch(BaseModel):
    mode: Literal["manual", "intermittent", "otomatis_suhu"]

# ========== Blower Config ==========
class BlowerConfigBase(BaseModel):
    mode: Optional[str] = None                        # 'manual', 'intermittent', 'otomatis_suhu'
    interval_on_duration: Optional[int] = None        # Used in 'intermittent' mode
    interval_off_duration: Optional[int] = None       # Used in 'intermittent' mode
    min_temperature: Optional[float] = None           # Used in 'otomatis_suhu' mode
    max_temperature: Optional[float] = None           # Used in 'otomatis_suhu' mode

class BlowerConfigCreate(BlowerConfigBase):
    actuator_id: str

class BlowerConfigResponse(BlowerConfigBase):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

# ========== Pump Config ==========
class PumpConfigBase(BaseModel):
    mode: Optional[str] = None                        # 'manual', 'otomatis_suhu'
    min_temperature: Optional[float] = None           # Used in 'otomatis_suhu' mode
    max_temperature: Optional[float] = None           # Used in 'otomatis_suhu' mode

class PumpConfigCreate(PumpConfigBase):
    actuator_id: str

class PumpConfigResponse(PumpConfigBase):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

# ========== Dimmer Config ==========
class DimmerConfigBase(BaseModel):
    pass  # Dimmer only supports manual mode; brightness set via current_value on Actuator

class DimmerConfigCreate(DimmerConfigBase):
    actuator_id: str

class DimmerConfigResponse(DimmerConfigBase):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

# ========== Heater Config ==========
class HeaterConfigBase(BaseModel):
    mode: Optional[str] = None                        # 'manual', 'otomatis_suhu'
    min_temperature: Optional[float] = None           # Used in 'otomatis_suhu' mode
    max_temperature: Optional[float] = None           # Used in 'otomatis_suhu' mode

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

# ========== Modbus Status ==========
class ModbusStatusResponse(BaseModel):
    connected: bool
    host: str
    port: int
    slave_id: int
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None