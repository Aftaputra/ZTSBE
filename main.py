from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text
from typing import List
import uvicorn

from database import engine, Base, SessionLocal, get_db, create_sqlite_triggers
from database import BlowerConfig, PumpConfig, DimmerConfig, HeaterConfig, ConfigAuditLog
from schemas import *
from database_viewer import router as db_viewer_router
from sqlalchemy.orm import Session

# ==========================================
# LIFESPAN
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for query in create_sqlite_triggers():
            try:
                conn.execute(text(query))
            except Exception as e:
                print(f"Error executing trigger: {e}")
        db = SessionLocal()
        try:
            if not db.query(BlowerConfig).first():
                db.add(BlowerConfig(actuator_id="BLOWER-01", interval_on_duration=10, interval_off_duration=5, min_temperature=25.0, max_temperature=30.0))
            if not db.query(PumpConfig).first():
                db.add(PumpConfig(actuator_id="PUMP-01", interval_on_duration=8, interval_off_duration=4))
            if not db.query(DimmerConfig).first():
                db.add(DimmerConfig(actuator_id="DIMMER-01", min_brightness=0, max_brightness=100))
            if not db.query(HeaterConfig).first():
                db.add(HeaterConfig(actuator_id="HEATER-01", min_temperature=20.0, max_temperature=35.0))
            db.commit()
        finally:
            db.close()
    yield

# Inisialisasi FastAPI dengan custom OpenAPI (hanya backend)
app = FastAPI(
    title="IoT Actuator API",
    description="Backend API untuk mengatur konfigurasi aktuator (Blower, Pump, Dimmer, Heater)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Register database viewer router
app.include_router(db_viewer_router)

# ==========================================
# UI HOMEPAGE (dengan Ionicons)
# ==========================================
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>IoT Actuator System</title>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/css/ionicons.min.css">
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; margin: 0; padding: 20px; }
            .container { background: white; border-radius: 20px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; max-width: 600px; }
            h1 { color: #667eea; margin-bottom: 10px; }
            .subtitle { color: #666; margin-bottom: 30px; }
            .menu { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 30px; }
            .card { background: #f8f9fa; padding: 20px; border-radius: 10px; text-decoration: none; color: #333; transition: transform 0.3s ease; display: block; }
            .card:hover { transform: translateY(-5px); box-shadow: 0 5px 20px rgba(0,0,0,0.1); }
            .card h3 { color: #667eea; margin-bottom: 10px; }
            .card p { font-size: 14px; color: #666; }
            .icon { font-size: 48px; margin-bottom: 10px; display: inline-block; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1><i class="icon ion-ios-analytics"></i> IoT Actuator System</h1>
            <p class="subtitle">Control and Monitor Your IoT Devices</p>
            <div class="menu">
                <a href="/dashboard" class="card"><div class="icon"><i class="icon ion-android-options"></i></div><h3>Control Panel</h3><p>Manage device configurations</p></a>
                <a href="/db-viewer/" class="card"><div class="icon"><i class="icon ion-database"></i></div><h3>Database Manager</h3><p>View and manage SQLite database</p></a>
                <a href="/docs" class="card"><div class="icon"><i class="icon ion-code"></i></div><h3>API Documentation</h3><p>Backend API endpoints</p></a>
            </div>
        </div>
    </body>
    </html>
    """)

# ==========================================
# DASHBOARD (dengan fitur tambah/delete device)
# ==========================================
@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>IoT Control Panel</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/css/ionicons.min.css">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { color: white; text-align: center; margin-bottom: 30px; font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
            .add-device-bar { background: white; border-radius: 15px; padding: 20px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
            .add-device-bar h3 { color: #667eea; margin-bottom: 15px; }
            .add-form { display: flex; gap: 15px; flex-wrap: wrap; align-items: flex-end; }
            .form-group { flex: 1; min-width: 150px; }
            .form-group label { display: block; margin-bottom: 5px; color: #333; font-weight: 500; }
            .form-group input, .form-group select { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 5px; }
            .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .card { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); transition: transform 0.3s ease; position: relative; }
            .card:hover { transform: translateY(-5px); }
            .card h2 { color: #667eea; margin-bottom: 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
            .delete-btn { position: absolute; top: 20px; right: 20px; background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 12px; }
            .delete-btn:hover { background: #c82333; }
            .actuator-info { background: #f8f9fa; padding: 10px; border-radius: 8px; margin-bottom: 15px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; color: #333; font-weight: 500; }
            input { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 14px; transition: background 0.3s ease; width: 100%; }
            button:hover { background: #764ba2; }
            .logs-section { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
            .logs-section h2 { color: #667eea; margin-bottom: 15px; }
            .filter-buttons { margin-bottom: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
            .filter-btn { background: #e0e0e0; color: #333; width: auto; padding: 8px 15px; }
            .filter-btn.active { background: #667eea; color: white; }
            .table-container { overflow-x: auto; }
            table { width: 100%; border-collapse: collapse; min-width: 600px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #667eea; color: white; }
            tr:hover { background: #f5f5f5; }
            .status { padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; position: fixed; top: 20px; right: 20px; z-index: 1000; padding: 10px 20px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            @media (max-width: 768px) { .dashboard { grid-template-columns: 1fr; } }
        </style>
    </head>
    <body>
        <div class="container">
            <h1><i class="icon ion-android-options"></i> IoT Actuator Control Panel</h1>
            
            <div class="add-device-bar">
                <h3><i class="icon ion-plus-circled"></i> Add New Device</h3>
                <div class="add-form">
                    <div class="form-group">
                        <label>Device Type</label>
                        <select id="device-type">
                            <option value="blower">Blower</option>
                            <option value="pump">Pump</option>
                            <option value="dimmer">Dimmer</option>
                            <option value="heater">Heater</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Device ID</label>
                        <input type="text" id="device-id" placeholder="e.g., BLOWER-02">
                    </div>
                    <div class="form-group">
                        <button onclick="addDevice()"><i class="icon ion-android-add"></i> Add Device</button>
                    </div>
                </div>
            </div>
            
            <div class="dashboard" id="dashboard"><div class="loading">Loading...</div></div>
            
            <div class="logs-section">
                <h2><i class="icon ion-document-text"></i> Audit Logs</h2>
                <div class="filter-buttons">
                    <button class="filter-btn active" onclick="filterLogs('all')">All</button>
                    <button class="filter-btn" onclick="filterLogs('BLOWER')">Blower</button>
                    <button class="filter-btn" onclick="filterLogs('PUMP')">Pump</button>
                    <button class="filter-btn" onclick="filterLogs('DIMMER')">Dimmer</button>
                    <button class="filter-btn" onclick="filterLogs('HEATER')">Heater</button>
                </div>
                <div id="logs-table">Loading...</div>
            </div>
        </div>
        
        <script>
            async function loadDevices() {
                try {
                    const response = await fetch('/all-configs/');
                    const data = await response.json();
                    displayDevices(data);
                } catch (error) { console.error('Error loading devices:', error); }
            }
            
            function displayDevices(data) {
                const dashboard = document.getElementById('dashboard');
                dashboard.innerHTML = '';
                
                data.blower.forEach(device => {
                    dashboard.innerHTML += getDeviceCard('blower', device);
                });
                data.pump.forEach(device => {
                    dashboard.innerHTML += getDeviceCard('pump', device);
                });
                data.dimmer.forEach(device => {
                    dashboard.innerHTML += getDeviceCard('dimmer', device);
                });
                data.heater.forEach(device => {
                    dashboard.innerHTML += getDeviceCard('heater', device);
                });
            }
            
            function getDeviceCard(type, device) {
                if (type === 'blower') {
                    return `
                        <div class="card" data-id="${device.actuator_id}">
                            <button class="delete-btn" onclick="deleteDevice('blower', '${device.actuator_id}')"><i class="icon ion-trash-b"></i> Delete</button>
                            <h2><i class="icon ion-android-fan"></i> Blower</h2>
                            <div class="actuator-info"><strong>ID:</strong> ${device.actuator_id}</div>
                            <form onsubmit="updateConfig(event, 'blower', '${device.actuator_id}')">
                                <div class="form-group"><label>Interval On (seconds):</label><input type="number" name="interval_on_duration" value="${device.interval_on}" required></div>
                                <div class="form-group"><label>Interval Off (seconds):</label><input type="number" name="interval_off_duration" value="${device.interval_off}" required></div>
                                <div class="form-group"><label>Min Temperature (°C):</label><input type="number" step="0.1" name="min_temperature" value="${device.min_temp}" required></div>
                                <div class="form-group"><label>Max Temperature (°C):</label><input type="number" step="0.1" name="max_temperature" value="${device.max_temp}" required></div>
                                <button type="submit"><i class="icon ion-android-sync"></i> Update</button>
                            </form>
                        </div>
                    `;
                } else if (type === 'pump') {
                    return `
                        <div class="card" data-id="${device.actuator_id}">
                            <button class="delete-btn" onclick="deleteDevice('pump', '${device.actuator_id}')"><i class="icon ion-trash-b"></i> Delete</button>
                            <h2><i class="icon ion-waterdrop"></i> Pump</h2>
                            <div class="actuator-info"><strong>ID:</strong> ${device.actuator_id}</div>
                            <form onsubmit="updateConfig(event, 'pump', '${device.actuator_id}')">
                                <div class="form-group"><label>Interval On (seconds):</label><input type="number" name="interval_on_duration" value="${device.interval_on}" required></div>
                                <div class="form-group"><label>Interval Off (seconds):</label><input type="number" name="interval_off_duration" value="${device.interval_off}" required></div>
                                <button type="submit"><i class="icon ion-android-sync"></i> Update</button>
                            </form>
                        </div>
                    `;
                } else if (type === 'dimmer') {
                    return `
                        <div class="card" data-id="${device.actuator_id}">
                            <button class="delete-btn" onclick="deleteDevice('dimmer', '${device.actuator_id}')"><i class="icon ion-trash-b"></i> Delete</button>
                            <h2><i class="icon ion-android-bulb"></i> Dimmer</h2>
                            <div class="actuator-info"><strong>ID:</strong> ${device.actuator_id}</div>
                            <form onsubmit="updateConfig(event, 'dimmer', '${device.actuator_id}')">
                                <div class="form-group"><label>Min Brightness (0-100):</label><input type="number" name="min_brightness" value="${device.min_brightness}" min="0" max="100" required></div>
                                <div class="form-group"><label>Max Brightness (0-100):</label><input type="number" name="max_brightness" value="${device.max_brightness}" min="0" max="100" required></div>
                                <button type="submit"><i class="icon ion-android-sync"></i> Update</button>
                            </form>
                        </div>
                    `;
                } else if (type === 'heater') {
                    return `
                        <div class="card" data-id="${device.actuator_id}">
                            <button class="delete-btn" onclick="deleteDevice('heater', '${device.actuator_id}')"><i class="icon ion-trash-b"></i> Delete</button>
                            <h2><i class="icon ion-fireball"></i> Heater</h2>
                            <div class="actuator-info"><strong>ID:</strong> ${device.actuator_id}</div>
                            <form onsubmit="updateConfig(event, 'heater', '${device.actuator_id}')">
                                <div class="form-group"><label>Min Temperature (°C):</label><input type="number" step="0.1" name="min_temperature" value="${device.min_temp}" required></div>
                                <div class="form-group"><label>Max Temperature (°C):</label><input type="number" step="0.1" name="max_temperature" value="${device.max_temp}" required></div>
                                <button type="submit"><i class="icon ion-android-sync"></i> Update</button>
                            </form>
                        </div>
                    `;
                }
            }
            
            async function addDevice() {
                const type = document.getElementById('device-type').value;
                const actuatorId = document.getElementById('device-id').value;
                
                if (!actuatorId) {
                    showStatus('Please enter Device ID', 'error');
                    return;
                }
                
                try {
                    let response;
                    if (type === 'blower') {
                        response = await fetch(`/blower/`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ actuator_id: actuatorId, interval_on_duration: 10, interval_off_duration: 5, min_temperature: 25, max_temperature: 30 })
                        });
                    } else if (type === 'pump') {
                        response = await fetch(`/pump/`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ actuator_id: actuatorId, interval_on_duration: 8, interval_off_duration: 4 })
                        });
                    } else if (type === 'dimmer') {
                        response = await fetch(`/dimmer/`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ actuator_id: actuatorId, min_brightness: 0, max_brightness: 100 })
                        });
                    } else {
                        response = await fetch(`/heater/`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ actuator_id: actuatorId, min_temperature: 20, max_temperature: 35 })
                        });
                    }
                    
                    if (response.ok) {
                        showStatus('Device added successfully!', 'success');
                        document.getElementById('device-id').value = '';
                        loadDevices();
                    } else {
                        showStatus('Error adding device', 'error');
                    }
                } catch (error) {
                    showStatus('Error adding device', 'error');
                }
            }
            
            async function deleteDevice(type, actuatorId) {
                if (confirm(`Are you sure you want to delete ${actuatorId}?`)) {
                    try {
                        const response = await fetch(`/${type}/${actuatorId}`, { method: 'DELETE' });
                        if (response.ok) {
                            showStatus('Device deleted successfully!', 'success');
                            loadDevices();
                            loadLogs(getCurrentFilter());
                        } else {
                            showStatus('Error deleting device', 'error');
                        }
                    } catch (error) {
                        showStatus('Error deleting device', 'error');
                    }
                }
            }
            
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
                    const response = await fetch(`/${type}/${actuatorId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
                    if (response.ok) { showStatus('Configuration updated!', 'success'); loadDevices(); loadLogs(getCurrentFilter()); }
                    else { showStatus('Error updating configuration', 'error'); }
                } catch (error) { showStatus('Error updating configuration', 'error'); }
            }
            
            function getCurrentFilter() {
                const activeBtn = document.querySelector('.filter-btn.active');
                const filterText = activeBtn.textContent;
                return filterText === 'All' ? 'all' : filterText;
            }
            
            async function loadLogs(filter = 'all') {
                try {
                    let url = '/audit-logs/';
                    if (filter !== 'all') url = `/audit-logs/${filter}`;
                    const response = await fetch(url);
                    const logs = await response.json();
                    displayLogs(logs);
                } catch (error) { console.error('Error loading logs:', error); }
            }
            
            function displayLogs(logs) {
                const logsDiv = document.getElementById('logs-table');
                if (logs.length === 0) { logsDiv.innerHTML = '<p>No logs found</p>'; return; }
                let html = '<div class="table-container"><table><thead><tr><th>ID</th><th>Actuator ID</th><th>Parameter</th><th>Old Value</th><th>New Value</th><th>Timestamp</th></tr></thead><tbody>';
                logs.forEach(log => { html += `<tr><td>${log.id}</td><td>${log.actuator_id}</td><td>${log.parameter_yang_diubah}</td><td>${log.nilai_lama}</td><td>${log.nilai_baru}</td><td>${new Date(log.timestamp).toLocaleString()}</td></tr>`; });
                html += '</tbody></table></div>';
                logsDiv.innerHTML = html;
            }
            
            function filterLogs(filter) {
                const btns = document.querySelectorAll('.filter-btn');
                btns.forEach(btn => { btn.classList.remove('active'); if (btn.textContent === (filter === 'all' ? 'All' : filter)) btn.classList.add('active'); });
                loadLogs(filter);
            }
            
            function showStatus(message, type) {
                const statusDiv = document.createElement('div');
                statusDiv.className = `status ${type}`;
                statusDiv.innerHTML = `<i class="icon ion-${type === 'success' ? 'checkmark-circled' : 'close-circled'}"></i> ${message}`;
                document.body.appendChild(statusDiv);
                setTimeout(() => statusDiv.remove(), 3000);
            }
            
            loadDevices();
            loadLogs('all');
            setInterval(() => { loadDevices(); const activeFilter = document.querySelector('.filter-btn.active').textContent; loadLogs(activeFilter === 'All' ? 'all' : activeFilter); }, 10000);
        </script>
    </body>
    </html>
    """)

# ==========================================
# API ENDPOINTS (Backend Only - untuk Swagger)
# ==========================================

# BLOWER ENDPOINTS
@app.get("/blower/{actuator_id}", response_model=BlowerResponse, tags=["Blower"])
def get_blower_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(BlowerConfig).filter(BlowerConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Blower tidak ditemukan")
    return config

@app.get("/blower/", response_model=List[BlowerResponse], tags=["Blower"])
def get_all_blower_configs(db: Session = Depends(get_db)):
    return db.query(BlowerConfig).all()

@app.post("/blower/", response_model=BlowerResponse, tags=["Blower"])
def create_blower_config(config: BlowerCreate, db: Session = Depends(get_db)):
    existing = db.query(BlowerConfig).filter(BlowerConfig.actuator_id == config.actuator_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device already exists")
    new_config = BlowerConfig(**config.model_dump())
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    return new_config

@app.put("/blower/{actuator_id}", response_model=BlowerResponse, tags=["Blower"])
def update_blower_config(actuator_id: str, config_update: BlowerUpdate, db: Session = Depends(get_db)):
    config = db.query(BlowerConfig).filter(BlowerConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Blower tidak ditemukan")
    for key, value in config_update.model_dump().items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config

@app.delete("/blower/{actuator_id}", tags=["Blower"])
def delete_blower_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(BlowerConfig).filter(BlowerConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Blower tidak ditemukan")
    db.delete(config)
    db.commit()
    return {"message": "Device deleted successfully"}

# PUMP ENDPOINTS
@app.get("/pump/{actuator_id}", response_model=PumpResponse, tags=["Pump"])
def get_pump_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(PumpConfig).filter(PumpConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Pump tidak ditemukan")
    return config

@app.get("/pump/", response_model=List[PumpResponse], tags=["Pump"])
def get_all_pump_configs(db: Session = Depends(get_db)):
    return db.query(PumpConfig).all()

@app.post("/pump/", response_model=PumpResponse, tags=["Pump"])
def create_pump_config(config: PumpCreate, db: Session = Depends(get_db)):
    existing = db.query(PumpConfig).filter(PumpConfig.actuator_id == config.actuator_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device already exists")
    new_config = PumpConfig(**config.model_dump())
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    return new_config

@app.put("/pump/{actuator_id}", response_model=PumpResponse, tags=["Pump"])
def update_pump_config(actuator_id: str, config_update: PumpUpdate, db: Session = Depends(get_db)):
    config = db.query(PumpConfig).filter(PumpConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Pump tidak ditemukan")
    for key, value in config_update.model_dump().items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config

@app.delete("/pump/{actuator_id}", tags=["Pump"])
def delete_pump_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(PumpConfig).filter(PumpConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Pump tidak ditemukan")
    db.delete(config)
    db.commit()
    return {"message": "Device deleted successfully"}

# DIMMER ENDPOINTS
@app.get("/dimmer/{actuator_id}", response_model=DimmerResponse, tags=["Dimmer"])
def get_dimmer_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(DimmerConfig).filter(DimmerConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Dimmer tidak ditemukan")
    return config

@app.get("/dimmer/", response_model=List[DimmerResponse], tags=["Dimmer"])
def get_all_dimmer_configs(db: Session = Depends(get_db)):
    return db.query(DimmerConfig).all()

@app.post("/dimmer/", response_model=DimmerResponse, tags=["Dimmer"])
def create_dimmer_config(config: DimmerCreate, db: Session = Depends(get_db)):
    existing = db.query(DimmerConfig).filter(DimmerConfig.actuator_id == config.actuator_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device already exists")
    new_config = DimmerConfig(**config.model_dump())
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    return new_config

@app.put("/dimmer/{actuator_id}", response_model=DimmerResponse, tags=["Dimmer"])
def update_dimmer_config(actuator_id: str, config_update: DimmerUpdate, db: Session = Depends(get_db)):
    config = db.query(DimmerConfig).filter(DimmerConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Dimmer tidak ditemukan")
    for key, value in config_update.model_dump().items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config

@app.delete("/dimmer/{actuator_id}", tags=["Dimmer"])
def delete_dimmer_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(DimmerConfig).filter(DimmerConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Dimmer tidak ditemukan")
    db.delete(config)
    db.commit()
    return {"message": "Device deleted successfully"}

# HEATER ENDPOINTS
@app.get("/heater/{actuator_id}", response_model=HeaterResponse, tags=["Heater"])
def get_heater_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(HeaterConfig).filter(HeaterConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Heater tidak ditemukan")
    return config

@app.get("/heater/", response_model=List[HeaterResponse], tags=["Heater"])
def get_all_heater_configs(db: Session = Depends(get_db)):
    return db.query(HeaterConfig).all()

@app.post("/heater/", response_model=HeaterResponse, tags=["Heater"])
def create_heater_config(config: HeaterCreate, db: Session = Depends(get_db)):
    existing = db.query(HeaterConfig).filter(HeaterConfig.actuator_id == config.actuator_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device already exists")
    new_config = HeaterConfig(**config.model_dump())
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    return new_config

@app.put("/heater/{actuator_id}", response_model=HeaterResponse, tags=["Heater"])
def update_heater_config(actuator_id: str, config_update: HeaterUpdate, db: Session = Depends(get_db)):
    config = db.query(HeaterConfig).filter(HeaterConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Heater tidak ditemukan")
    for key, value in config_update.model_dump().items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config

@app.delete("/heater/{actuator_id}", tags=["Heater"])
def delete_heater_config(actuator_id: str, db: Session = Depends(get_db)):
    config = db.query(HeaterConfig).filter(HeaterConfig.actuator_id == actuator_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Heater tidak ditemukan")
    db.delete(config)
    db.commit()
    return {"message": "Device deleted successfully"}

# AUDIT LOG ENDPOINTS
@app.get("/audit-logs/", response_model=List[LogResponse], tags=["Audit Log"])
def get_all_logs(db: Session = Depends(get_db)):
    return db.query(ConfigAuditLog).order_by(ConfigAuditLog.timestamp.desc()).all()

@app.get("/audit-logs/{actuator_id}", response_model=List[LogResponse], tags=["Audit Log"])
def get_logs_by_actuator(actuator_id: str, db: Session = Depends(get_db)):
    return db.query(ConfigAuditLog).filter(ConfigAuditLog.actuator_id == actuator_id).order_by(ConfigAuditLog.timestamp.desc()).all()

# ALL CONFIGS ENDPOINT
@app.get("/all-configs/", tags=["Dashboard"], include_in_schema=False)
def get_all_configs(db: Session = Depends(get_db)):
    return {
        "blower": [{"actuator_id": b.actuator_id, "interval_on": b.interval_on_duration, "interval_off": b.interval_off_duration, "min_temp": b.min_temperature, "max_temp": b.max_temperature} for b in db.query(BlowerConfig).all()],
        "pump": [{"actuator_id": p.actuator_id, "interval_on": p.interval_on_duration, "interval_off": p.interval_off_duration} for p in db.query(PumpConfig).all()],
        "dimmer": [{"actuator_id": d.actuator_id, "min_brightness": d.min_brightness, "max_brightness": d.max_brightness} for d in db.query(DimmerConfig).all()],
        "heater": [{"actuator_id": h.actuator_id, "min_temp": h.min_temperature, "max_temp": h.max_temperature} for h in db.query(HeaterConfig).all()]
    }

# TABLE STRUCTURE ENDPOINT
@app.get("/table-structure/", tags=["Database"], include_in_schema=False)
def get_table_structure(db: Session = Depends(get_db)):
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = ['blower_config', 'pump_config', 'dimmer_config', 'heater_config', 'config_audit_log']
    structure = {}
    for table in tables:
        columns = inspector.get_columns(table)
        structure[table] = [{"name": col["name"], "type": str(col["type"]), "nullable": col["nullable"]} for col in columns]
    return structure

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)