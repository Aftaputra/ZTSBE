from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List
import uuid
import os
import uvicorn
from datetime import datetime

from database import engine, Base, SessionLocal, get_db, create_sqlite_triggers
from database import Kandang, Lantai, Actuator, BlowerConfig, PumpConfig, DimmerConfig, HeaterConfig, ConfigAuditLog
from schemas import *
from database_viewer import router as db_viewer_router

# ========== LIFESPAN ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for q in create_sqlite_triggers():
            try:
                conn.execute(text(q))
            except Exception as e:
                print(f"Trigger error: {e}")
        # Seed data jika kosong
        db = SessionLocal()
        try:
            if not db.query(Kandang).first():
                k1 = Kandang(nama="Kandang Utama", lokasi="Blok A")
                db.add(k1)
                db.flush()
                l1 = Lantai(kandang_id=k1.id, nama="Lantai 1")
                db.add(l1)
                db.flush()
                act = Actuator(
                    uuid=str(uuid.uuid4()),
                    lantai_id=l1.id,
                    name="Blower 01",
                    type="blower",
                    mode="auto",
                    current_status=False,
                    current_value=0.0
                )
                db.add(act)
                db.flush()
                bc = BlowerConfig(
                    actuator_id=act.uuid,
                    interval_on_duration=10,
                    interval_off_duration=5,
                    min_temperature=25.0,
                    max_temperature=30.0
                )
                db.add(bc)
                db.commit()
        finally:
            db.close()
    yield

app = FastAPI(title="IoT Actuator API", version="1.0", lifespan=lifespan, docs_url="/docs", redoc_url="/redoc")
app.include_router(db_viewer_router)

# Buat folder templates jika belum ada
os.makedirs("templates", exist_ok=True)

def render_template(filename: str) -> str:
    with open(f"templates/{filename}", "r", encoding="utf-8") as f:
        return f.read()

# ========== UI ROUTES ==========
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    return HTMLResponse(render_template("index.html"))

@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return HTMLResponse(render_template("dashboard.html"))

# ========== API ENDPOINTS ==========

# Kandang
@app.get("/kandang/", response_model=List[KandangResponse], tags=["Kandang"])
def get_all_kandang(db: Session = Depends(get_db)):
    return db.query(Kandang).all()

@app.post("/kandang/", response_model=KandangResponse, tags=["Kandang"])
def create_kandang(k: KandangCreate, db: Session = Depends(get_db)):
    db_k = Kandang(**k.model_dump())
    db.add(db_k)
    db.commit()
    db.refresh(db_k)
    return db_k

@app.delete("/kandang/{kandang_id}", tags=["Kandang"])
def delete_kandang(kandang_id: int, db: Session = Depends(get_db)):
    k = db.query(Kandang).filter(Kandang.id == kandang_id).first()
    if not k:
        raise HTTPException(404)
    db.delete(k)
    db.commit()
    return {"ok": True}

# Lantai
@app.get("/lantai/", response_model=List[LantaiResponse], tags=["Lantai"])
def get_all_lantai(db: Session = Depends(get_db)):
    return db.query(Lantai).all()

@app.post("/lantai/", response_model=LantaiResponse, tags=["Lantai"])
def create_lantai(l: LantaiCreate, db: Session = Depends(get_db)):
    db_l = Lantai(**l.model_dump())
    db.add(db_l)
    db.commit()
    db.refresh(db_l)
    return db_l

@app.delete("/lantai/{lantai_id}", tags=["Lantai"])
def delete_lantai(lantai_id: int, db: Session = Depends(get_db)):
    l = db.query(Lantai).filter(Lantai.id == lantai_id).first()
    if not l:
        raise HTTPException(404)
    db.delete(l)
    db.commit()
    return {"ok": True}

# Actuator
@app.get("/actuator/", response_model=List[ActuatorResponse], tags=["Actuator"])
def get_all_actuator(db: Session = Depends(get_db)):
    return db.query(Actuator).all()

@app.post("/actuator/", response_model=ActuatorResponse, tags=["Actuator"])
def create_actuator(a: ActuatorCreate, db: Session = Depends(get_db)):
    new_uuid = str(uuid.uuid4())
    db_a = Actuator(uuid=new_uuid, **a.model_dump())
    db.add(db_a)
    db.flush()
    if a.type == "blower":
        db.add(BlowerConfig(actuator_id=new_uuid, interval_on_duration=10, interval_off_duration=5, min_temperature=25.0, max_temperature=30.0))
    elif a.type == "pump":
        db.add(PumpConfig(actuator_id=new_uuid, interval_on_duration=8, interval_off_duration=4))
    elif a.type == "dimmer":
        db.add(DimmerConfig(actuator_id=new_uuid, min_brightness=0, max_brightness=100))
    elif a.type == "heater":
        db.add(HeaterConfig(actuator_id=new_uuid, min_temperature=20.0, max_temperature=35.0))
    db.commit()
    db.refresh(db_a)
    return db_a

@app.patch("/actuator/{uuid}", response_model=ActuatorResponse, tags=["Actuator"])
def patch_actuator(uuid: str, patch: ActuatorPatch, db: Session = Depends(get_db)):
    actuator = db.query(Actuator).filter(Actuator.uuid == uuid).first()
    if not actuator:
        raise HTTPException(404, "Actuator not found")
    if patch.current_status is not None:
        actuator.current_status = patch.current_status
    if patch.current_value is not None:
        actuator.current_value = patch.current_value
    actuator.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(actuator)
    return actuator

@app.delete("/actuator/{uuid}", tags=["Actuator"])
def delete_actuator(uuid: str, db: Session = Depends(get_db)):
    a = db.query(Actuator).filter(Actuator.uuid == uuid).first()
    if not a:
        raise HTTPException(404)
    db.delete(a)
    db.commit()
    return {"ok": True}

# Konfigurasi
@app.put("/blower/{actuator_id}", response_model=BlowerConfigResponse, tags=["Blower"])
def update_blower(actuator_id: str, cfg: BlowerConfigBase, db: Session = Depends(get_db)):
    bc = db.query(BlowerConfig).filter(BlowerConfig.actuator_id == actuator_id).first()
    if not bc:
        raise HTTPException(404)
    for k, v in cfg.model_dump().items():
        setattr(bc, k, v)
    db.commit()
    db.refresh(bc)
    return bc

@app.put("/pump/{actuator_id}", response_model=PumpConfigResponse, tags=["Pump"])
def update_pump(actuator_id: str, cfg: PumpConfigBase, db: Session = Depends(get_db)):
    pc = db.query(PumpConfig).filter(PumpConfig.actuator_id == actuator_id).first()
    if not pc:
        raise HTTPException(404)
    for k, v in cfg.model_dump().items():
        setattr(pc, k, v)
    db.commit()
    db.refresh(pc)
    return pc

@app.put("/dimmer/{actuator_id}", response_model=DimmerConfigResponse, tags=["Dimmer"])
def update_dimmer(actuator_id: str, cfg: DimmerConfigBase, db: Session = Depends(get_db)):
    dc = db.query(DimmerConfig).filter(DimmerConfig.actuator_id == actuator_id).first()
    if not dc:
        raise HTTPException(404)
    for k, v in cfg.model_dump().items():
        setattr(dc, k, v)
    db.commit()
    db.refresh(dc)
    return dc

@app.put("/heater/{actuator_id}", response_model=HeaterConfigResponse, tags=["Heater"])
def update_heater(actuator_id: str, cfg: HeaterConfigBase, db: Session = Depends(get_db)):
    hc = db.query(HeaterConfig).filter(HeaterConfig.actuator_id == actuator_id).first()
    if not hc:
        raise HTTPException(404)
    for k, v in cfg.model_dump().items():
        setattr(hc, k, v)
    db.commit()
    db.refresh(hc)
    return hc

# Audit Log
@app.get("/audit-logs/", response_model=List[AuditLogResponse], tags=["Audit"])
def get_all_audit_logs(db: Session = Depends(get_db)):
    return db.query(ConfigAuditLog).order_by(ConfigAuditLog.waktu_perubahan.desc()).all()

@app.get("/audit-logs/{type}", response_model=List[AuditLogResponse], tags=["Audit"])
def get_audit_by_actuator_type(type: str, db: Session = Depends(get_db)):
    subq = db.query(Actuator.uuid).filter(Actuator.type == type).subquery()
    logs = db.query(ConfigAuditLog).filter(ConfigAuditLog.actuator_id.in_(subq)).order_by(ConfigAuditLog.waktu_perubahan.desc()).all()
    return logs

# Hierarchy for UI
@app.get("/hierarchy/", tags=["UI"], include_in_schema=False)
def get_hierarchy(db: Session = Depends(get_db)):
    kandangs = db.query(Kandang).all()
    result = []
    for k in kandangs:
        lantais = db.query(Lantai).filter(Lantai.kandang_id == k.id).all()
        lantai_list = []
        for l in lantais:
            actuators = db.query(Actuator).filter(Actuator.lantai_id == l.id).all()
            act_list = []
            for a in actuators:
                cfg = None
                if a.type == "blower":
                    cfg = db.query(BlowerConfig).filter(BlowerConfig.actuator_id == a.uuid).first()
                elif a.type == "pump":
                    cfg = db.query(PumpConfig).filter(PumpConfig.actuator_id == a.uuid).first()
                elif a.type == "dimmer":
                    cfg = db.query(DimmerConfig).filter(DimmerConfig.actuator_id == a.uuid).first()
                elif a.type == "heater":
                    cfg = db.query(HeaterConfig).filter(HeaterConfig.actuator_id == a.uuid).first()
                act_list.append({
                    "uuid": a.uuid,
                    "name": a.name,
                    "type": a.type,
                    "current_status": a.current_status,
                    "current_value": a.current_value,
                    "config": cfg.__dict__ if cfg else {}
                })
            lantai_list.append({"id": l.id, "nama": l.nama, "actuators": act_list})
        result.append({"id": k.id, "nama": k.nama, "lokasi": k.lokasi, "lantai": lantai_list})
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)