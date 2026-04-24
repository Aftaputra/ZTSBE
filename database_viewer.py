from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import text, inspect
from database import engine, get_db
from sqlalchemy.orm import Session
import csv
import io

router = APIRouter(prefix="/db-viewer", tags=["Database Viewer"])

@router.get("/", response_class=HTMLResponse)
def database_viewer():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SQLite Database Viewer</title>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/css/ionicons.min.css">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #fff; color: #000; }
            .header { background: #000; color: #fff; padding: 20px; border-bottom: 1px solid #ccc; }
            .header h1 { font-size: 1.5rem; font-weight: normal; }
            .container { display: flex; max-width: 1400px; margin: 20px auto; gap: 20px; padding: 0 20px; }
            .sidebar { width: 250px; background: #f8f8f8; padding: 20px; border: 1px solid #ccc; }
            .sidebar h3 { font-size: 1rem; margin-bottom: 15px; font-weight: 600; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
            .table-list { list-style: none; }
            .table-list li { padding: 8px 5px; cursor: pointer; border-bottom: 1px solid #eee; }
            .table-list li:hover { background: #e0e0e0; }
            .table-list li.active { background: #000; color: #fff; }
            .content { flex: 1; background: #fff; padding: 20px; border: 1px solid #ccc; overflow-x: auto; }
            .table-info { margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #ccc; }
            .table-info h2 { font-size: 1.2rem; font-weight: 600; }
            .stats { display: flex; gap: 20px; margin-top: 10px; }
            .stat-card { background: #f8f8f8; padding: 8px 15px; border-left: 3px solid #000; }
            .btn { padding: 6px 12px; background: #fff; border: 1px solid #000; cursor: pointer; font-size: 0.8rem; transition: 0.2s; }
            .btn:hover { background: #000; color: #fff; }
            .btn-primary { background: #000; color: #fff; }
            .btn-primary:hover { background: #333; }
            .btn-danger { border-color: #d00; color: #d00; }
            .btn-danger:hover { background: #d00; color: #fff; border-color: #d00; }
            .btn-success { border-color: #080; color: #080; }
            .btn-success:hover { background: #080; color: #fff; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ccc; }
            th { background: #f0f0f0; font-weight: 600; }
            tr:hover { background: #f9f9f9; }
            .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
            .modal-content { background: #fff; margin: 5% auto; padding: 20px; width: 90%; max-width: 500px; border: 1px solid #000; }
            .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #ccc; padding-bottom: 8px; }
            .close { font-size: 24px; cursor: pointer; }
            .form-group { margin-bottom: 12px; }
            .form-group label { display: block; font-weight: 600; margin-bottom: 4px; }
            .form-group input, .form-group textarea { width: 100%; padding: 6px; border: 1px solid #ccc; font-family: monospace; }
            .action-buttons { margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
            @media (max-width: 768px) { .container { flex-direction: column; } .sidebar { width: 100%; } }
        </style>
    </head>
    <body>
        <div class="header">
            <h1><i class="icon ion-database"></i> SQLite Database Manager</h1>
        </div>
        <div class="container">
            <div class="sidebar">
                <h3><i class="icon ion-filing"></i> Tables</h3>
                <ul class="table-list" id="table-list"><li>Loading...</li></ul>
            </div>
            <div class="content"><div id="table-content"><p>Select a table from the left</p></div></div>
        </div>
        <div id="modal" class="modal"><div class="modal-content"><div class="modal-header"><h2 id="modal-title">Add Record</h2><span class="close">&times;</span></div><div id="modal-body"></div></div></div>
        <script>
            let currentTable = '', currentData = [], currentColumns = [];
            async function loadTables() {
                try {
                    const res = await fetch('/db-viewer/tables');
                    const tables = await res.json();
                    const list = document.getElementById('table-list');
                    list.innerHTML = '';
                    tables.forEach(t => {
                        const li = document.createElement('li');
                        li.innerHTML = `<i class="icon ion-grid"></i> ${t}`;
                        li.onclick = () => loadTableData(t);
                        list.appendChild(li);
                    });
                } catch(e) { console.error(e); }
            }
            async function loadTableData(name) {
                currentTable = name;
                document.querySelectorAll('.table-list li').forEach(li => li.classList.remove('active'));
                event.target.classList.add('active');
                try {
                    const res = await fetch(`/db-viewer/table/${name}`);
                    const data = await res.json();
                    currentData = data.data;
                    currentColumns = data.columns;
                    displayTable(data);
                } catch(e) { console.error(e); }
            }
            function displayTable(data) {
                const container = document.getElementById('table-content');
                let html = `<div class="table-info"><h2>${data.table_name}</h2><div class="stats"><div class="stat-card">Records: ${data.total_records}</div><div class="stat-card">Columns: ${data.columns.length}</div></div></div>
                <div class="action-buttons"><button class="btn btn-success" onclick="showAddModal()"><i class="icon ion-plus"></i> Add</button>
                <button class="btn btn-primary" onclick="exportTable()"><i class="icon ion-ios-download"></i> Export CSV</button>
                <button class="btn" onclick="refreshTable()"><i class="icon ion-refresh"></i> Refresh</button></div>`;
                if(data.data.length===0) html+='<p>No data</p>';
                else {
                    html+='<div style="overflow-x:auto"> <table> <thead><tr>';
                    data.columns.forEach(c=>html+=`<th>${c}</th>`);
                    html+='<th>Actions</th></tr></thead><tbody>';
                    data.data.forEach((row,idx)=>{
                        html+='<tr>';
                        data.columns.forEach(c=>{
                            let val = row[c];
                            if(val===null) val='<em>NULL</em>';
                            if(typeof val==='object') val=JSON.stringify(val);
                            html+=`<td>${val}</td>`;
                        });
                        html+=`<td><button class="btn" style="margin-right:5px;" onclick="showEditModal(${idx})"><i class="icon ion-edit"></i></button>
                        <button class="btn btn-danger" onclick="deleteRecord(${row.id||row.id_log||idx})"><i class="icon ion-trash-b"></i></button></td></tr>`;
                    });
                    html+='</tbody></table></div>';
                }
                container.innerHTML = html;
            }
            function showAddModal() {
                const modal = document.getElementById('modal'), title = document.getElementById('modal-title'), body = document.getElementById('modal-body');
                title.innerText = `Add to ${currentTable}`;
                let form = '<form id="record-form">';
                currentColumns.forEach(col=>{
                    if(col!=='id' && col!=='id_log' && !col.includes('timestamp') && !col.includes('waktu') && !col.includes('updated_at')){
                        form+=`<div class="form-group"><label>${col}</label><input type="text" name="${col}" required></div>`;
                    }
                });
                form+=`<div class="form-group"><button type="submit" class="btn btn-success">Save</button> <button type="button" class="btn" onclick="closeModal()">Cancel</button></div></form>`;
                body.innerHTML = form;
                modal.style.display='block';
                document.getElementById('record-form').onsubmit = async(e)=>{
                    e.preventDefault();
                    const fd = new FormData(e.target);
                    const data = {};
                    fd.forEach((v,k)=>{ data[k] = isNaN(v) ? v : parseFloat(v); });
                    await addRecord(data);
                };
            }
            function showEditModal(idx) {
                const row = currentData[idx];
                const modal = document.getElementById('modal'), title = document.getElementById('modal-title'), body = document.getElementById('modal-body');
                title.innerText = `Edit in ${currentTable}`;
                let form = '<form id="record-form">';
                currentColumns.forEach(col=>{
                    if(col!=='id' && col!=='id_log' && !col.includes('timestamp') && !col.includes('waktu') && !col.includes('updated_at')){
                        let val = row[col] || '';
                        form+=`<div class="form-group"><label>${col}</label><input type="text" name="${col}" value="${val}" required></div>`;
                    }
                });
                form+=`<div class="form-group"><button type="submit" class="btn btn-success">Update</button> <button type="button" class="btn" onclick="closeModal()">Cancel</button></div></form>`;
                body.innerHTML = form;
                modal.style.display='block';
                document.getElementById('record-form').onsubmit = async(e)=>{
                    e.preventDefault();
                    const fd = new FormData(e.target);
                    const data = {};
                    fd.forEach((v,k)=>{ data[k] = isNaN(v) ? v : parseFloat(v); });
                    await updateRecord(row.id||row.id_log, data);
                };
            }
            async function addRecord(data) {
                try{
                    const res = await fetch(`/db-viewer/table/${currentTable}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
                    if(res.ok){ alert('Added'); closeModal(); loadTableData(currentTable); } else alert('Error');
                }catch(e){ alert('Error'); }
            }
            async function updateRecord(id, data) {
                try{
                    const res = await fetch(`/db-viewer/table/${currentTable}/${id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
                    if(res.ok){ alert('Updated'); closeModal(); loadTableData(currentTable); } else alert('Error');
                }catch(e){ alert('Error'); }
            }
            async function deleteRecord(id) {
                if(!confirm('Delete record?')) return;
                try{
                    const res = await fetch(`/db-viewer/table/${currentTable}/${id}`, {method:'DELETE'});
                    if(res.ok){ alert('Deleted'); loadTableData(currentTable); } else alert('Error');
                }catch(e){ alert('Error'); }
            }
            function exportTable(){ window.location.href = `/db-viewer/export/${currentTable}`; }
            function refreshTable(){ loadTableData(currentTable); }
            function closeModal(){ document.getElementById('modal').style.display='none'; }
            document.querySelector('.close').onclick = closeModal;
            window.onclick = function(e){ if(e.target === document.getElementById('modal')) closeModal(); }
            loadTables();
        </script>
    </body>
    </html>
    """)

@router.get("/tables")
def get_tables(db: Session = Depends(get_db)):
    inspector = inspect(engine)
    return inspector.get_table_names()

@router.get("/table/{table_name}")
def get_table_data(table_name: str, db: Session = Depends(get_db)):
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    result = db.execute(text(f"SELECT * FROM {table_name}"))
    data = [dict(zip(columns, row)) for row in result.fetchall()]
    return {"table_name": table_name, "columns": columns, "data": data, "total_records": len(data)}

@router.post("/table/{table_name}")
def add_record(table_name: str, record: dict, db: Session = Depends(get_db)):
    cols = ', '.join(record.keys())
    placeholders = ', '.join([f":{k}" for k in record.keys()])
    db.execute(text(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"), record)
    db.commit()
    return {"message": "ok"}

@router.put("/table/{table_name}/{record_id}")
def update_record(table_name: str, record_id: int, record: dict, db: Session = Depends(get_db)):
    # get primary key column name
    inspector = inspect(engine)
    pk = inspector.get_pk_constraint(table_name)['constrained_columns'][0]
    set_clause = ', '.join([f"{k} = :{k}" for k in record.keys()])
    query = text(f"UPDATE {table_name} SET {set_clause} WHERE {pk} = :pk")
    record['pk'] = record_id
    db.execute(query, record)
    db.commit()
    return {"message": "ok"}

@router.delete("/table/{table_name}/{record_id}")
def delete_record(table_name: str, record_id: int, db: Session = Depends(get_db)):
    inspector = inspect(engine)
    pk = inspector.get_pk_constraint(table_name)['constrained_columns'][0]
    db.execute(text(f"DELETE FROM {table_name} WHERE {pk} = :id"), {"id": record_id})
    db.commit()
    return {"message": "ok"}

@router.get("/export/{table_name}")
def export_csv(table_name: str, db: Session = Depends(get_db)):
    inspector = inspect(engine)
    cols = [c['name'] for c in inspector.get_columns(table_name)]
    result = db.execute(text(f"SELECT * FROM {table_name}"))
    data = result.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(cols)
    writer.writerows(data)
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={table_name}.csv"})