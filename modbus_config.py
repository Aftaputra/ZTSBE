"""
Modbus Configuration & Register Mapping
Untuk integrasi dengan Modbus Slave (PLC/Simulator)
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ========== MODBUS CONNECTION CONFIG ==========
MODBUS_HOST = os.getenv("MODBUS_HOST", "127.0.0.1")
MODBUS_PORT = int(os.getenv("MODBUS_PORT", "502"))
MODBUS_SLAVE_ID = int(os.getenv("MODBUS_SLAVE_ID", "1"))
MODBUS_TIMEOUT = int(os.getenv("MODBUS_TIMEOUT", "5"))

# ========== REGISTER MAPPING ==========
# Format: 
#   - Coil (digital output/input): 0-9999
#   - Holding Register (analog output): 40000-49999
#   - Input Register (analog input): 30000-39999

MODBUS_REGISTER_MAP = {
    "blower": {
        "manual": {
            "coil_status": 100,                    # ON/OFF
            "register_value": 1000,                # PWM 0-100%
        },
        "intermittent": {
            "coil_status": 101,                    # ON/OFF (auto toggle)
            "register_interval_on": 1001,          # Durasi nyala (detik)
            "register_interval_off": 1002,         # Durasi mati (detik)
        },
        "otomatis_suhu": {
            "coil_status": 102,                    # ON/OFF (auto by temp)
            "register_min_temp": 1003,             # Min threshold
            "register_max_temp": 1004,             # Max threshold
            "register_current_temp": 1005,         # Current temp (read from sensor)
        }
    },
    "pump": {
        "manual": {
            "coil_status": 200,
            "register_value": 2000,
        },
        "otomatis_suhu": {
            "coil_status": 201,
            "register_min_temp": 2001,
            "register_max_temp": 2002,
            "register_current_temp": 2003,
        }
    },
    "dimmer": {
        "manual": {
            "coil_status": 300,
            "register_value": 3000,                # Brightness 0-100%
        }
    },
    "heater": {
        "manual": {
            "coil_status": 400,
            "register_value": 4000,
        },
        "otomatis_suhu": {
            "coil_status": 401,
            "register_min_temp": 4001,
            "register_max_temp": 4002,
            "register_current_temp": 4003,
        }
    }
}

# ========== HELPER FUNCTION ==========
def get_modbus_addresses(device_type: str, mode: str):
    """
    Get Modbus addresses untuk device & mode tertentu
    
    Args:
        device_type: 'blower', 'pump', 'dimmer', 'heater'
        mode: 'manual', 'intermittent', 'otomatis_suhu'
    
    Returns:
        dict dengan coil_status, register_value, etc
    """
    if device_type not in MODBUS_REGISTER_MAP:
        raise ValueError(f"Unknown device type: {device_type}")
    
    if mode not in MODBUS_REGISTER_MAP[device_type]:
        raise ValueError(f"Unknown mode '{mode}' for device '{device_type}'")
    
    return MODBUS_REGISTER_MAP[device_type][mode]
