from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os

# Hapus database lama jika perlu rebuild
DB_FILE = "./iot_system.db"
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print(f"Database lama {DB_FILE} telah dihapus.")

# Setup database
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# MODEL DATABASE
# ==========================================

class ConfigAuditLog(Base):
    __tablename__ = "config_audit_log"
    id = Column(Integer, primary_key=True, index=True)
    actuator_id = Column(String, index=True)
    parameter_yang_diubah = Column(String)
    nilai_lama = Column(String)
    nilai_baru = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

class BlowerConfig(Base):
    __tablename__ = "blower_config"
    id = Column(Integer, primary_key=True, index=True)
    actuator_id = Column(String, unique=True, index=True)
    interval_on_duration = Column(Integer)
    interval_off_duration = Column(Integer)
    min_temperature = Column(Float)
    max_temperature = Column(Float)

class PumpConfig(Base):
    __tablename__ = "pump_config"
    id = Column(Integer, primary_key=True, index=True)
    actuator_id = Column(String, unique=True, index=True)
    interval_on_duration = Column(Integer)
    interval_off_duration = Column(Integer)

class DimmerConfig(Base):
    __tablename__ = "dimmer_config"
    id = Column(Integer, primary_key=True, index=True)
    actuator_id = Column(String, unique=True, index=True)
    min_brightness = Column(Integer)
    max_brightness = Column(Integer)

class HeaterConfig(Base):
    __tablename__ = "heater_config"
    id = Column(Integer, primary_key=True, index=True)
    actuator_id = Column(String, unique=True, index=True)
    min_temperature = Column(Float)
    max_temperature = Column(Float)

# ==========================================
# SQLITE TRIGGERS
# ==========================================

def create_sqlite_triggers():
    """Membuat trigger untuk SQLite"""
    triggers = [
        "DROP TRIGGER IF EXISTS trigger_audit_blower;",
        "DROP TRIGGER IF EXISTS trigger_audit_pump;",
        "DROP TRIGGER IF EXISTS trigger_audit_dimmer;",
        "DROP TRIGGER IF EXISTS trigger_audit_heater;",
        
        # Trigger untuk Blower
        """
        CREATE TRIGGER trigger_audit_blower
        AFTER UPDATE ON blower_config
        BEGIN
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, timestamp)
            SELECT NEW.actuator_id, 'interval_on_duration', CAST(OLD.interval_on_duration AS TEXT), CAST(NEW.interval_on_duration AS TEXT), datetime('now')
            WHERE NEW.interval_on_duration != OLD.interval_on_duration;
            
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, timestamp)
            SELECT NEW.actuator_id, 'interval_off_duration', CAST(OLD.interval_off_duration AS TEXT), CAST(NEW.interval_off_duration AS TEXT), datetime('now')
            WHERE NEW.interval_off_duration != OLD.interval_off_duration;
            
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, timestamp)
            SELECT NEW.actuator_id, 'min_temperature', CAST(OLD.min_temperature AS TEXT), CAST(NEW.min_temperature AS TEXT), datetime('now')
            WHERE NEW.min_temperature != OLD.min_temperature;
            
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, timestamp)
            SELECT NEW.actuator_id, 'max_temperature', CAST(OLD.max_temperature AS TEXT), CAST(NEW.max_temperature AS TEXT), datetime('now')
            WHERE NEW.max_temperature != OLD.max_temperature;
        END;
        """,
        
        # Trigger untuk Pump
        """
        CREATE TRIGGER trigger_audit_pump
        AFTER UPDATE ON pump_config
        BEGIN
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, timestamp)
            SELECT NEW.actuator_id, 'interval_on_duration', CAST(OLD.interval_on_duration AS TEXT), CAST(NEW.interval_on_duration AS TEXT), datetime('now')
            WHERE NEW.interval_on_duration != OLD.interval_on_duration;
            
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, timestamp)
            SELECT NEW.actuator_id, 'interval_off_duration', CAST(OLD.interval_off_duration AS TEXT), CAST(NEW.interval_off_duration AS TEXT), datetime('now')
            WHERE NEW.interval_off_duration != OLD.interval_off_duration;
        END;
        """,
        
        # Trigger untuk Dimmer
        """
        CREATE TRIGGER trigger_audit_dimmer
        AFTER UPDATE ON dimmer_config
        BEGIN
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, timestamp)
            SELECT NEW.actuator_id, 'min_brightness', CAST(OLD.min_brightness AS TEXT), CAST(NEW.min_brightness AS TEXT), datetime('now')
            WHERE NEW.min_brightness != OLD.min_brightness;
            
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, timestamp)
            SELECT NEW.actuator_id, 'max_brightness', CAST(OLD.max_brightness AS TEXT), CAST(NEW.max_brightness AS TEXT), datetime('now')
            WHERE NEW.max_brightness != OLD.max_brightness;
        END;
        """,
        
        # Trigger untuk Heater
        """
        CREATE TRIGGER trigger_audit_heater
        AFTER UPDATE ON heater_config
        BEGIN
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, timestamp)
            SELECT NEW.actuator_id, 'min_temperature', CAST(OLD.min_temperature AS TEXT), CAST(NEW.min_temperature AS TEXT), datetime('now')
            WHERE NEW.min_temperature != OLD.min_temperature;
            
            INSERT INTO config_audit_log (actuator_id, parameter_yang_diubah, nilai_lama, nilai_baru, timestamp)
            SELECT NEW.actuator_id, 'max_temperature', CAST(OLD.max_temperature AS TEXT), CAST(NEW.max_temperature AS TEXT), datetime('now')
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