import uuid
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import os

DB_FILE = "./iot_system.db"
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print(f"Database lama {DB_FILE} telah dihapus.")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# MODEL
# ==========================================

class Kandang(Base):
    __tablename__ = "kandang"
    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String, nullable=False)
    lokasi = Column(String)

    lantai = relationship("Lantai", back_populates="kandang", cascade="all, delete-orphan")

class Lantai(Base):
    __tablename__ = "lantai"
    id = Column(Integer, primary_key=True, index=True)
    kandang_id = Column(Integer, ForeignKey("kandang.id", ondelete="CASCADE"), nullable=False)
    nama = Column(String, nullable=False)

    kandang = relationship("Kandang", back_populates="lantai")
    actuators = relationship("Actuator", back_populates="lantai", cascade="all, delete-orphan")

class Actuator(Base):
    __tablename__ = "actuator"
    uuid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lantai_id = Column(Integer, ForeignKey("lantai.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'blower', 'pump', 'dimmer', 'heater'
    mode = Column(String, nullable=True)
    current_status = Column(Boolean, default=False)
    current_value = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lantai = relationship("Lantai", back_populates="actuators")
    blower_config = relationship("BlowerConfig", uselist=False, back_populates="actuator", cascade="all, delete-orphan")
    pump_config = relationship("PumpConfig", uselist=False, back_populates="actuator", cascade="all, delete-orphan")
    dimmer_config = relationship("DimmerConfig", uselist=False, back_populates="actuator", cascade="all, delete-orphan")
    heater_config = relationship("HeaterConfig", uselist=False, back_populates="actuator", cascade="all, delete-orphan")

class BlowerConfig(Base):
    __tablename__ = "blower_config"
    actuator_id = Column(String, ForeignKey("actuator.uuid", ondelete="CASCADE"), primary_key=True)
    interval_on_duration = Column(Integer)
    interval_off_duration = Column(Integer)
    min_temperature = Column(Float)
    max_temperature = Column(Float)

    actuator = relationship("Actuator", back_populates="blower_config")

class PumpConfig(Base):
    __tablename__ = "pump_config"
    actuator_id = Column(String, ForeignKey("actuator.uuid", ondelete="CASCADE"), primary_key=True)
    interval_on_duration = Column(Integer)
    interval_off_duration = Column(Integer)

    actuator = relationship("Actuator", back_populates="pump_config")

class DimmerConfig(Base):
    __tablename__ = "dimmer_config"
    actuator_id = Column(String, ForeignKey("actuator.uuid", ondelete="CASCADE"), primary_key=True)
    min_brightness = Column(Integer)
    max_brightness = Column(Integer)

    actuator = relationship("Actuator", back_populates="dimmer_config")

class HeaterConfig(Base):
    __tablename__ = "heater_config"
    actuator_id = Column(String, ForeignKey("actuator.uuid", ondelete="CASCADE"), primary_key=True)
    min_temperature = Column(Float)
    max_temperature = Column(Float)

    actuator = relationship("Actuator", back_populates="heater_config")

class ConfigAuditLog(Base):
    __tablename__ = "config_audit_log"
    id_log = Column(Integer, primary_key=True, index=True)
    actuator_id = Column(String, ForeignKey("actuator.uuid", ondelete="CASCADE"), nullable=False)
    parameter_yang_diubah = Column(String, nullable=False)
    nilai_lama = Column(String)
    nilai_baru = Column(String)
    waktu_perubahan = Column(DateTime, default=datetime.utcnow)

    actuator = relationship("Actuator")

# ==========================================
# SQLITE TRIGGERS
# ==========================================

def create_sqlite_triggers():
    triggers = [
        "DROP TRIGGER IF EXISTS trigger_audit_blower;",
        "DROP TRIGGER IF EXISTS trigger_audit_pump;",
        "DROP TRIGGER IF EXISTS trigger_audit_dimmer;",
        "DROP TRIGGER IF EXISTS trigger_audit_heater;",

        """
        CREATE TRIGGER trigger_audit_blower
        AFTER UPDATE ON blower_config
        BEGIN
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, waktu_perubahan)
            SELECT NEW.actuator_id, 'interval_on_duration', CAST(OLD.interval_on_duration AS TEXT), CAST(NEW.interval_on_duration AS TEXT), CURRENT_TIMESTAMP
            WHERE NEW.interval_on_duration != OLD.interval_on_duration;

            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, waktu_perubahan)
            SELECT NEW.actuator_id, 'interval_off_duration', CAST(OLD.interval_off_duration AS TEXT), CAST(NEW.interval_off_duration AS TEXT), CURRENT_TIMESTAMP
            WHERE NEW.interval_off_duration != OLD.interval_off_duration;

            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, waktu_perubahan)
            SELECT NEW.actuator_id, 'min_temperature', CAST(OLD.min_temperature AS TEXT), CAST(NEW.min_temperature AS TEXT), CURRENT_TIMESTAMP
            WHERE NEW.min_temperature != OLD.min_temperature;

            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, waktu_perubahan)
            SELECT NEW.actuator_id, 'max_temperature', CAST(OLD.max_temperature AS TEXT), CAST(NEW.max_temperature AS TEXT), CURRENT_TIMESTAMP
            WHERE NEW.max_temperature != OLD.max_temperature;
        END;
        """,

        """
        CREATE TRIGGER trigger_audit_pump
        AFTER UPDATE ON pump_config
        BEGIN
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, waktu_perubahan)
            SELECT NEW.actuator_id, 'interval_on_duration', CAST(OLD.interval_on_duration AS TEXT), CAST(NEW.interval_on_duration AS TEXT), CURRENT_TIMESTAMP
            WHERE NEW.interval_on_duration != OLD.interval_on_duration;

            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, waktu_perubahan)
            SELECT NEW.actuator_id, 'interval_off_duration', CAST(OLD.interval_off_duration AS TEXT), CAST(NEW.interval_off_duration AS TEXT), CURRENT_TIMESTAMP
            WHERE NEW.interval_off_duration != OLD.interval_off_duration;
        END;
        """,

        """
        CREATE TRIGGER trigger_audit_dimmer
        AFTER UPDATE ON dimmer_config
        BEGIN
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, waktu_perubahan)
            SELECT NEW.actuator_id, 'min_brightness', CAST(OLD.min_brightness AS TEXT), CAST(NEW.min_brightness AS TEXT), CURRENT_TIMESTAMP
            WHERE NEW.min_brightness != OLD.min_brightness;

            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, waktu_perubahan)
            SELECT NEW.actuator_id, 'max_brightness', CAST(OLD.max_brightness AS TEXT), CAST(NEW.max_brightness AS TEXT), CURRENT_TIMESTAMP
            WHERE NEW.max_brightness != OLD.max_brightness;
        END;
        """,

        """
        CREATE TRIGGER trigger_audit_heater
        AFTER UPDATE ON heater_config
        BEGIN
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, waktu_perubahan)
            SELECT NEW.actuator_id, 'min_temperature', CAST(OLD.min_temperature AS TEXT), CAST(NEW.min_temperature AS TEXT), CURRENT_TIMESTAMP
            WHERE NEW.min_temperature != OLD.min_temperature;

            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, waktu_perubahan)
            SELECT NEW.actuator_id, 'max_temperature', CAST(OLD.max_temperature AS TEXT), CAST(NEW.max_temperature AS TEXT), CURRENT_TIMESTAMP
            WHERE NEW.max_temperature != OLD.max_temperature;
        END;
        """
    ]
    return triggers

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()