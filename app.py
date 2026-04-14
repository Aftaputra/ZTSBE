from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, text, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import datetime
import uvicorn
import os

# ==========================================
# 1. HAPUS DATABASE LAMA (jika perlu rebuild)
# ==========================================
DB_FILE = "./iot_system.db"
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print(f"Database lama {DB_FILE} telah dihapus.")

# ==========================================
# 2. SETUP DATABASE (SQLite)
# ==========================================
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# 3. MODEL DATABASE (SQLAlchemy)
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
# 4. SCHEMA PYDANTIC
# ==========================================
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

# Pump Schemas
class PumpUpdate(BaseModel):
    interval_on_duration: int
    interval_off_duration: int

class PumpResponse(PumpUpdate):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

# Dimmer Schemas
class DimmerUpdate(BaseModel):
    min_brightness: int
    max_brightness: int

class DimmerResponse(DimmerUpdate):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

# Heater Schemas
class HeaterUpdate(BaseModel):
    min_temperature: float
    max_temperature: float

class HeaterResponse(HeaterUpdate):
    actuator_id: str
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 5. SQLITE TRIGGERS
# ==========================================

def create_sqlite_triggers():
    """Membuat trigger untuk SQLite"""
    triggers = [
        # Hapus trigger lama jika ada
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

# ==========================================
# 6. LIFESPAN: BUAT TABEL & TRIGGER SAAT STARTUP
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Buat semua tabel
    Base.metadata.create_all(bind=engine)
    
    # Eksekusi pembuatan Trigger
    with engine.begin() as conn:
        for query in create_sqlite_triggers():
            try:
                conn.execute(text(query))
            except Exception as e:
                print(f"Error executing trigger: {e}")
        
        # Buat data dummy untuk semua aktuator jika belum ada
        db = SessionLocal()
        
        # Cek dan buat data Blower
        if not db.query(BlowerConfig).first():
            dummy_blower = BlowerConfig(
                actuator_id="BLOWER-01", 
                interval_on_duration=10, 
                interval_off_duration=5, 
                min_temperature=25.0, 
                max_temperature=30.0
            )
            db.add(dummy_blower)
        
        # Cek dan buat data Pump
        if not db.query(PumpConfig).first():
            dummy_pump = PumpConfig(
                actuator_id="PUMP-01",
                interval_on_duration=8,
                interval_off_duration=4
            )
            db.add(dummy_pump)
        
        # Cek dan buat data Dimmer
        if not db.query(DimmerConfig).first():
            dummy_dimmer = DimmerConfig(
                actuator_id="DIMMER-01",
                min_brightness=0,
                max_brightness=100
            )
            db.add(dummy_dimmer)
        
        # Cek dan buat data Heater
        if not db.query(HeaterConfig).first():
            dummy_heater = HeaterConfig(
                actuator_id="HEATER-01",
                min_temperature=20.0,
                max_temperature=35.0
            )
            db.add(dummy_heater)
        
        db.commit()
        db.close()
    
    yield

# ==========================================
# 7. INISIALISASI FASTAPI
# ==========================================
app = FastAPI(
    title="IoT Actuator API",
    description="API untuk mengatur konfigurasi aktuator (Blower, Pump, Dimmer, Heater) dengan audit log menggunakan Trigger SQLite",
    version="1.0.0",
    lifespan=lifespan
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 8. ENDPOINTS BLOWER
# ==========================================
@app.get("/blower/{actuator_id}", response_model=BlowerResponse, tags=["Blower"])
def get_blower_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(BlowerConfig).filter(BlowerConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Blower tidak ditemukan")
    return config

@app.put("/blower/{actuator_id}", response_model=BlowerResponse, tags=["Blower"])
def update_blower_config(actuator_id: str, config_update: BlowerUpdate, db: Session = Depends(get_db)):
    config = db.query(BlowerConfig).filter(BlowerConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Blower tidak ditemukan")
    
    config.interval_on_duration = config_update.interval_on_duration
    config.interval_off_duration = config_update.interval_off_duration
    config.min_temperature = config_update.min_temperature
    config.max_temperature = config_update.max_temperature
    
    db.commit()
    db.refresh(config)
    return config

# ==========================================
# 9. ENDPOINTS PUMP
# ==========================================
@app.get("/pump/{actuator_id}", response_model=PumpResponse, tags=["Pump"])
def get_pump_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(PumpConfig).filter(PumpConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Pump tidak ditemukan")
    return config

@app.put("/pump/{actuator_id}", response_model=PumpResponse, tags=["Pump"])
def update_pump_config(actuator_id: str, config_update: PumpUpdate, db: Session = Depends(get_db)):
    config = db.query(PumpConfig).filter(PumpConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Pump tidak ditemukan")
    
    config.interval_on_duration = config_update.interval_on_duration
    config.interval_off_duration = config_update.interval_off_duration
    
    db.commit()
    db.refresh(config)
    return config

# ==========================================
# 10. ENDPOINTS DIMMER
# ==========================================
@app.get("/dimmer/{actuator_id}", response_model=DimmerResponse, tags=["Dimmer"])
def get_dimmer_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(DimmerConfig).filter(DimmerConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Dimmer tidak ditemukan")
    return config

@app.put("/dimmer/{actuator_id}", response_model=DimmerResponse, tags=["Dimmer"])
def update_dimmer_config(actuator_id: str, config_update: DimmerUpdate, db: Session = Depends(get_db)):
    config = db.query(DimmerConfig).filter(DimmerConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Dimmer tidak ditemukan")
    
    config.min_brightness = config_update.min_brightness
    config.max_brightness = config_update.max_brightness
    
    db.commit()
    db.refresh(config)
    return config

# ==========================================
# 11. ENDPOINTS HEATER
# ==========================================
@app.get("/heater/{actuator_id}", response_model=HeaterResponse, tags=["Heater"])
def get_heater_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(HeaterConfig).filter(HeaterConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Heater tidak ditemukan")
    return config

@app.put("/heater/{actuator_id}", response_model=HeaterResponse, tags=["Heater"])
def update_heater_config(actuator_id: str, config_update: HeaterUpdate, db: Session = Depends(get_db)):
    config = db.query(HeaterConfig).filter(HeaterConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Heater tidak ditemukan")
    
    config.min_temperature = config_update.min_temperature
    config.max_temperature = config_update.max_temperature
    
    db.commit()
    db.refresh(config)
    return config

# ==========================================
# 12. ENDPOINTS AUDIT LOG
# ==========================================
@app.get("/audit-logs/", response_model=List[LogResponse], tags=["Audit Log"])
def get_all_logs(db: Session = Depends(get_db)):
    logs = db.query(ConfigAuditLog).order_by(ConfigAuditLog.timestamp.desc()).all()
    return logs

@app.get("/audit-logs/{actuator_id}", response_model=List[LogResponse], tags=["Audit Log"])
def get_logs_by_actuator(actuator_id: str, db: Session = Depends(get_db)):
    logs = db.query(ConfigAuditLog).filter(ConfigAuditLog.actuator_id == actuator_id).order_by(ConfigAuditLog.timestamp.desc()).all()
    return logs

# ==========================================
# 13. ENDPOINT UNTUK GET ALL CONFIGURATIONS
# ==========================================
@app.get("/all-configs/", tags=["Dashboard"])
def get_all_configs(db: Session = Depends(get_db)):
    blower = db.query(BlowerConfig).all()
    pump = db.query(PumpConfig).all()
    dimmer = db.query(DimmerConfig).all()
    heater = db.query(HeaterConfig).all()
    
    return {
        "blower": [{"actuator_id": b.actuator_id, "interval_on": b.interval_on_duration, 
                    "interval_off": b.interval_off_duration, "min_temp": b.min_temperature, 
                    "max_temp": b.max_temperature} for b in blower],
        "pump": [{"actuator_id": p.actuator_id, "interval_on": p.interval_on_duration, 
                  "interval_off": p.interval_off_duration} for p in pump],
        "dimmer": [{"actuator_id": d.actuator_id, "min_brightness": d.min_brightness, 
                    "max_brightness": d.max_brightness} for d in dimmer],
        "heater": [{"actuator_id": h.actuator_id, "min_temp": h.min_temperature, 
                    "max_temp": h.max_temperature} for h in heater]
    }

# ==========================================
# 14. VISUALISASI TABEL
# ==========================================
@app.get("/table-structure/", tags=["Database"])
def get_table_structure(db: Session = Depends(get_db)):
    tables = ['blower_config', 'pump_config', 'dimmer_config', 'heater_config', 'config_audit_log']
    structure = {}
    
    for table in tables:
        result = db.execute(text(f"PRAGMA table_info({table})"))
        columns = [{"name": row[1], "type": row[2], "nullable": not row[3], "default": row[4]} for row in result]
        structure[table] = columns
    
    return structure

# ==========================================
# 15. UI INTERAKTIF (HTML)
# ==========================================
@app.get("/", response_class=HTMLResponse, tags=["UI"])
def interactive_ui():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>IoT Actuator Control Panel</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }
            
            .dashboard {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .card {
                background: white;
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                transition: transform 0.3s ease;
            }
            
            .card:hover {
                transform: translateY(-5px);
            }
            
            .card h2 {
                color: #667eea;
                margin-bottom: 15px;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
            }
            
            .actuator-info {
                background: #f8f9fa;
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 15px;
            }
            
            .form-group {
                margin-bottom: 15px;
            }
            
            label {
                display: block;
                margin-bottom: 5px;
                color: #333;
                font-weight: 500;
            }
            
            input {
                width: 100%;
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
            }
            
            button {
                background: #667eea;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
                transition: background 0.3s ease;
                width: 100%;
            }
            
            button:hover {
                background: #764ba2;
            }
            
            .logs-section {
                background: white;
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            
            .logs-section h2 {
                color: #667eea;
                margin-bottom: 15px;
            }
            
            .filter-buttons {
                margin-bottom: 15px;
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }
            
            .filter-btn {
                background: #e0e0e0;
                color: #333;
                width: auto;
                padding: 8px 15px;
            }
            
            .filter-btn.active {
                background: #667eea;
                color: white;
            }
            
            .table-container {
                overflow-x: auto;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                min-width: 600px;
            }
            
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            
            th {
                background: #667eea;
                color: white;
            }
            
            tr:hover {
                background: #f5f5f5;
            }
            
            .status {
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            
            .success {
                background: #d4edda;
                color: #155724;
            }
            
            .error {
                background: #f8d7da;
                color: #721c24;
            }
            
            @media (max-width: 768px) {
                .dashboard {
                    grid-template-columns: 1fr;
                }
                
                th, td {
                    padding: 8px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 IoT Actuator Control Panel</h1>
            
            <div class="dashboard" id="dashboard">
                <!-- Cards will be loaded here -->
            </div>
            
            <div class="logs-section">
                <h2>📋 Audit Logs</h2>
                <div class="filter-buttons">
                    <button class="filter-btn active" onclick="filterLogs('all')">All</button>
                    <button class="filter-btn" onclick="filterLogs('BLOWER-01')">Blower</button>
                    <button class="filter-btn" onclick="filterLogs('PUMP-01')">Pump</button>
                    <button class="filter-btn" onclick="filterLogs('DIMMER-01')">Dimmer</button>
                    <button class="filter-btn" onclick="filterLogs('HEATER-01')">Heater</button>
                </div>
                <div id="logs-table">
                    <!-- Logs will be loaded here -->
                </div>
            </div>
        </div>
        
        <script>
            // Load all configurations
            async function loadConfigs() {
                try {
                    const response = await fetch('/all-configs/');
                    const data = await response.json();
                    displayConfigs(data);
                } catch (error) {
                    console.error('Error loading configs:', error);
                }
            }
            
            // Display configurations in cards
            function displayConfigs(data) {
                const dashboard = document.getElementById('dashboard');
                dashboard.innerHTML = '';
                
                // Blower Card
                if (data.blower.length > 0) {
                    const blower = data.blower[0];
                    dashboard.innerHTML += `
                        <div class="card">
                            <h2>🌬️ Blower</h2>
                            <div class="actuator-info">
                                <strong>ID:</strong> ${blower.actuator_id}
                            </div>
                            <form onsubmit="updateConfig(event, 'blower', '${blower.actuator_id}')">
                                <div class="form-group">
                                    <label>Interval On (seconds):</label>
                                    <input type="number" name="interval_on_duration" value="${blower.interval_on}" required>
                                </div>
                                <div class="form-group">
                                    <label>Interval Off (seconds):</label>
                                    <input type="number" name="interval_off_duration" value="${blower.interval_off}" required>
                                </div>
                                <div class="form-group">
                                    <label>Min Temperature (°C):</label>
                                    <input type="number" step="0.1" name="min_temperature" value="${blower.min_temp}" required>
                                </div>
                                <div class="form-group">
                                    <label>Max Temperature (°C):</label>
                                    <input type="number" step="0.1" name="max_temperature" value="${blower.max_temp}" required>
                                </div>
                                <button type="submit">Update Blower</button>
                            </form>
                        </div>
                    `;
                }
                
                // Pump Card
                if (data.pump.length > 0) {
                    const pump = data.pump[0];
                    dashboard.innerHTML += `
                        <div class="card">
                            <h2>💧 Pump</h2>
                            <div class="actuator-info">
                                <strong>ID:</strong> ${pump.actuator_id}
                            </div>
                            <form onsubmit="updateConfig(event, 'pump', '${pump.actuator_id}')">
                                <div class="form-group">
                                    <label>Interval On (seconds):</label>
                                    <input type="number" name="interval_on_duration" value="${pump.interval_on}" required>
                                </div>
                                <div class="form-group">
                                    <label>Interval Off (seconds):</label>
                                    <input type="number" name="interval_off_duration" value="${pump.interval_off}" required>
                                </div>
                                <button type="submit">Update Pump</button>
                            </form>
                        </div>
                    `;
                }
                
                // Dimmer Card
                if (data.dimmer.length > 0) {
                    const dimmer = data.dimmer[0];
                    dashboard.innerHTML += `
                        <div class="card">
                            <h2>💡 Dimmer</h2>
                            <div class="actuator-info">
                                <strong>ID:</strong> ${dimmer.actuator_id}
                            </div>
                            <form onsubmit="updateConfig(event, 'dimmer', '${dimmer.actuator_id}')">
                                <div class="form-group">
                                    <label>Min Brightness (0-100):</label>
                                    <input type="number" name="min_brightness" value="${dimmer.min_brightness}" min="0" max="100" required>
                                </div>
                                <div class="form-group">
                                    <label>Max Brightness (0-100):</label>
                                    <input type="number" name="max_brightness" value="${dimmer.max_brightness}" min="0" max="100" required>
                                </div>
                                <button type="submit">Update Dimmer</button>
                            </form>
                        </div>
                    `;
                }
                
                // Heater Card
                if (data.heater.length > 0) {
                    const heater = data.heater[0];
                    dashboard.innerHTML += `
                        <div class="card">
                            <h2>🔥 Heater</h2>
                            <div class="actuator-info">
                                <strong>ID:</strong> ${heater.actuator_id}
                            </div>
                            <form onsubmit="updateConfig(event, 'heater', '${heater.actuator_id}')">
                                <div class="form-group">
                                    <label>Min Temperature (°C):</label>
                                    <input type="number" step="0.1" name="min_temperature" value="${heater.min_temp}" required>
                                </div>
                                <div class="form-group">
                                    <label>Max Temperature (°C):</label>
                                    <input type="number" step="0.1" name="max_temperature" value="${heater.max_temp}" required>
                                </div>
                                <button type="submit">Update Heater</button>
                            </form>
                        </div>
                    `;
                }
            }
            
            // Update configuration
            async function updateConfig(event, type, actuatorId) {
                event.preventDefault();
                const form = event.target;
                const formData = new FormData(form);
                const data = {};
                
                formData.forEach((value, key) => {
                    if (key.includes('temperature') || key.includes('brightness')) {
                        data[key] = key.includes('brightness') ? parseInt(value) : parseFloat(value);
                    } else {
                        data[key] = parseInt(value);
                    }
                });
                
                try {
                    const response = await fetch(`/${type}/${actuatorId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data)
                    });
                    
                    if (response.ok) {
                        showStatus('Configuration updated successfully!', 'success');
                        loadConfigs();
                        loadLogs(getCurrentFilter());
                    } else {
                        showStatus('Error updating configuration', 'error');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showStatus('Error updating configuration', 'error');
                }
            }
            
            // Get current filter
            function getCurrentFilter() {
                const activeBtn = document.querySelector('.filter-btn.active');
                const filterText = activeBtn.textContent;
                return filterText === 'All' ? 'all' : filterText;
            }
            
            // Load audit logs
            async function loadLogs(filter = 'all') {
                try {
                    let url = '/audit-logs/';
                    if (filter !== 'all') {
                        url = `/audit-logs/${filter}`;
                    }
                    const response = await fetch(url);
                    const logs = await response.json();
                    displayLogs(logs);
                } catch (error) {
                    console.error('Error loading logs:', error);
                }
            }
            
            // Display logs in table
            function displayLogs(logs) {
                const logsDiv = document.getElementById('logs-table');
                if (logs.length === 0) {
                    logsDiv.innerHTML = '<p>No logs found</p>';
                    return;
                }
                
                let html = '<div class="table-container"> <table> <thead> <tr>';
                html += '<th>ID</th><th>Actuator ID</th><th>Parameter</th><th>Old Value</th><th>New Value</th><th>Timestamp</th>';
                html += '</tr> </thead> <tbody>';
                
                logs.forEach(log => {
                    html += `<tr>
                        <td>${log.id}</td>
                        <td>${log.actuator_id}</td>
                        <td>${log.parameter_yang_diubah}</td>
                        <td>${log.nilai_lama}</td>
                        <td>${log.nilai_baru}</td>
                        <td>${new Date(log.timestamp).toLocaleString()}</td>
                    </tr>`;
                });
                
                html += '</tbody> </table> </div>';
                logsDiv.innerHTML = html;
            }
            
            // Filter logs
            function filterLogs(filter) {
                // Update active button
                const btns = document.querySelectorAll('.filter-btn');
                btns.forEach(btn => {
                    btn.classList.remove('active');
                    if (btn.textContent === (filter === 'all' ? 'All' : filter)) {
                        btn.classList.add('active');
                    }
                });
                
                loadLogs(filter);
            }
            
            // Show status message
            function showStatus(message, type) {
                const statusDiv = document.createElement('div');
                statusDiv.className = `status ${type}`;
                statusDiv.textContent = message;
                statusDiv.style.position = 'fixed';
                statusDiv.style.top = '20px';
                statusDiv.style.right = '20px';
                statusDiv.style.zIndex = '1000';
                statusDiv.style.padding = '10px 20px';
                statusDiv.style.borderRadius = '5px';
                statusDiv.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
                document.body.appendChild(statusDiv);
                
                setTimeout(() => {
                    statusDiv.remove();
                }, 3000);
            }
            
            // Initial load
            loadConfigs();
            loadLogs('all');
            
            // Auto refresh every 10 seconds
            setInterval(() => {
                loadConfigs();
                const activeFilter = document.querySelector('.filter-btn.active').textContent;
                loadLogs(activeFilter === 'All' ? 'all' : activeFilter);
            }, 10000);
        </script>
    </body>
    </html>
    """)

# ==========================================
# 16. RUN SERVER
# ==========================================
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)