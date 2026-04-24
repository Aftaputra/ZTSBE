"""
Modbus Service - PyModbus async TCP client wrapper
Handles connection management, read/write operations, and database sync
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from modbus_config import (
    MODBUS_HOST,
    MODBUS_PORT,
    MODBUS_SLAVE_ID,
    MODBUS_TIMEOUT,
    get_modbus_addresses,
)

logger = logging.getLogger(__name__)


class ModbusService:
    """Async PyModbus TCP client wrapper with auto-reconnect and DB sync."""

    def __init__(self):
        self.host: str = MODBUS_HOST
        self.port: int = MODBUS_PORT
        self.slave_id: int = MODBUS_SLAVE_ID
        self.timeout: int = MODBUS_TIMEOUT
        self._client: Optional[AsyncModbusTcpClient] = None
        self.connected: bool = False
        self.last_sync: Optional[datetime] = None
        self.error_message: Optional[str] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish connection to Modbus TCP slave. Returns True on success."""
        try:
            self._client = AsyncModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=self.timeout,
            )
            connected = await self._client.connect()
            if connected:
                self.connected = True
                self.error_message = None
                logger.info(f"Modbus connected: {self.host}:{self.port}")
            else:
                self.connected = False
                self.error_message = "Connection refused"
                logger.warning(f"Modbus connection refused: {self.host}:{self.port}")
            return self.connected
        except Exception as exc:
            self.connected = False
            self.error_message = str(exc)
            logger.error(f"Modbus connect error: {exc}")
            return False

    async def disconnect(self):
        """Close connection gracefully."""
        if self._client:
            self._client.close()
        self.connected = False
        logger.info("Modbus disconnected")

    def _is_ready(self) -> bool:
        return self._client is not None and self.connected

    # ------------------------------------------------------------------
    # Low-level read helpers
    # ------------------------------------------------------------------

    async def read_coil(self, address: int) -> Optional[bool]:
        """Read a single coil (digital I/O). Returns None on error."""
        if not self._is_ready():
            return None
        try:
            result = await self._client.read_coils(address, count=1, slave=self.slave_id)
            if result.isError():
                logger.error(f"read_coil({address}) error: {result}")
                return None
            return bool(result.bits[0])
        except (ModbusException, Exception) as exc:
            logger.error(f"read_coil({address}) exception: {exc}")
            self.connected = False
            return None

    async def read_register(self, address: int) -> Optional[int]:
        """Read a single holding register. Returns None on error."""
        if not self._is_ready():
            return None
        try:
            result = await self._client.read_holding_registers(address, count=1, slave=self.slave_id)
            if result.isError():
                logger.error(f"read_register({address}) error: {result}")
                return None
            return result.registers[0]
        except (ModbusException, Exception) as exc:
            logger.error(f"read_register({address}) exception: {exc}")
            self.connected = False
            return None

    # ------------------------------------------------------------------
    # Low-level write helpers
    # ------------------------------------------------------------------

    async def write_coil(self, address: int, value: bool) -> bool:
        """Write a single coil. Returns True on success."""
        if not self._is_ready():
            logger.warning(f"write_coil({address}, {value}) skipped: not connected")
            return False
        try:
            result = await self._client.write_coil(address, value, slave=self.slave_id)
            if result.isError():
                logger.error(f"write_coil({address}, {value}) error: {result}")
                return False
            return True
        except (ModbusException, Exception) as exc:
            logger.error(f"write_coil({address}, {value}) exception: {exc}")
            self.connected = False
            return False

    async def write_register(self, address: int, value: int) -> bool:
        """Write a single holding register. Returns True on success."""
        if not self._is_ready():
            logger.warning(f"write_register({address}, {value}) skipped: not connected")
            return False
        try:
            result = await self._client.write_register(address, value, slave=self.slave_id)
            if result.isError():
                logger.error(f"write_register({address}, {value}) error: {result}")
                return False
            return True
        except (ModbusException, Exception) as exc:
            logger.error(f"write_register({address}, {value}) exception: {exc}")
            self.connected = False
            return False

    # ------------------------------------------------------------------
    # High-level device write
    # ------------------------------------------------------------------

    async def sync_actuator_to_modbus(self, device_type: str, mode: str, status: bool, value: Optional[float], config: dict) -> bool:
        """
        Write actuator state and config to Modbus registers.

        Args:
            device_type: 'blower', 'pump', 'dimmer', 'heater'
            mode: active mode string
            status: ON/OFF
            value: current_value (PWM, brightness, etc.)
            config: dict with mode-specific parameters (min_temperature, etc.)

        Returns:
            True if all writes succeeded (or were skipped due to disconnect).
        """
        if not self._is_ready():
            return False

        try:
            addrs = get_modbus_addresses(device_type, mode)
        except ValueError as exc:
            logger.warning(f"sync_actuator_to_modbus: {exc}")
            return False

        ok = True

        # Always write ON/OFF coil
        ok &= await self.write_coil(addrs["coil_status"], status)

        if mode == "manual":
            if value is not None and "register_value" in addrs:
                ok &= await self.write_register(addrs["register_value"], int(value))

        elif mode == "intermittent":
            if config.get("interval_on_duration") is not None and "register_interval_on" in addrs:
                ok &= await self.write_register(addrs["register_interval_on"], int(config["interval_on_duration"]))
            if config.get("interval_off_duration") is not None and "register_interval_off" in addrs:
                ok &= await self.write_register(addrs["register_interval_off"], int(config["interval_off_duration"]))

        elif mode == "otomatis_suhu":
            if config.get("min_temperature") is not None and "register_min_temp" in addrs:
                ok &= await self.write_register(addrs["register_min_temp"], int(config["min_temperature"] * 10))
            if config.get("max_temperature") is not None and "register_max_temp" in addrs:
                ok &= await self.write_register(addrs["register_max_temp"], int(config["max_temperature"] * 10))

        return ok

    # ------------------------------------------------------------------
    # High-level device read (poll from PLC)
    # ------------------------------------------------------------------

    async def read_actuator_from_modbus(self, device_type: str, mode: str) -> dict:
        """
        Read actuator state from Modbus registers.

        Returns dict with keys: status (bool), value (int|None), current_temp (int|None)
        """
        result = {"status": None, "value": None, "current_temp": None}
        if not self._is_ready():
            return result

        try:
            addrs = get_modbus_addresses(device_type, mode)
        except ValueError:
            return result

        coil = await self.read_coil(addrs["coil_status"])
        result["status"] = coil

        if mode == "manual" and "register_value" in addrs:
            result["value"] = await self.read_register(addrs["register_value"])

        if mode == "otomatis_suhu" and "register_current_temp" in addrs:
            raw = await self.read_register(addrs["register_current_temp"])
            if raw is not None:
                result["current_temp"] = raw / 10.0  # stored as tenths of a degree

        return result

    # ------------------------------------------------------------------
    # Database sync (called by background polling task)
    # ------------------------------------------------------------------

    async def poll_and_sync(self, db_session_factory):
        """
        Poll all actuators from Modbus and update database.
        Uses the provided session factory to open a DB session.
        """
        if not self._is_ready():
            # Attempt reconnect
            await self.connect()
            if not self._is_ready():
                return

        from database import Actuator  # local import to avoid circular deps

        db = db_session_factory()
        try:
            actuators = db.query(Actuator).all()
            for act in actuators:
                if not act.mode:
                    continue
                plc_data = await self.read_actuator_from_modbus(act.type, act.mode)
                if plc_data["status"] is None:
                    continue  # read failed

                changed = False
                if plc_data["status"] != act.current_status:
                    act.current_status = plc_data["status"]
                    changed = True
                if plc_data["value"] is not None and plc_data["value"] != act.current_value:
                    act.current_value = float(plc_data["value"])
                    changed = True

                if changed:
                    act.updated_at = datetime.utcnow()

                act.last_sync = datetime.utcnow()

            db.commit()
            self.last_sync = datetime.utcnow()
        except Exception as exc:
            logger.error(f"poll_and_sync error: {exc}")
            db.rollback()
        finally:
            db.close()


# Module-level singleton
modbus_service = ModbusService()
