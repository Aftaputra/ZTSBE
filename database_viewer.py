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
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/css/ionicons.min.css">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header h1 { margin-bottom: 10px; }
            .container { display: flex; max-width: 1400px; margin: 20px auto; gap: 20px; padding: 0 20px; }
            .sidebar { width: 250px; background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); height: fit-content; }
            .sidebar h3 { color: #667eea; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }
            .table-list { list-style: none; }
            .table-list li { padding: 10px; margin: 5px 0; cursor: pointer; border-radius: 5px; transition: all 0.3s ease; }
            .table-list li:hover { background: #f0f0f0; }
            .table-list li.active { background: #667eea; color: white; }
            .content { flex: 1; background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow-x: auto; }
            .table-info { margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #e0e0e0; }
            .table-info h2 { color: #667eea; margin-bottom: 10px; }
            .stats { display: flex; gap: 20px; margin-top: 10px; flex-wrap: wrap; }
            .stat-card { background: #f8f9fa; padding: 10px 20px; border-radius: 5px; border-left: 4px solid #667eea; }
            .stat-card strong { color: #667eea; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #667eea; color: white; position: sticky; top: 0; }
            tr:hover { background: #f5f5f5; }
            .action-buttons { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
            .btn { padding: 8px 16px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; transition: all 0.3s ease; }
            .btn-primary { background: #667eea; color: white; }
            .btn-primary:hover { background: #764ba2; }
            .btn-danger { background: #dc3545; color: white; }
            .btn-danger:hover { background: #c82333; }
            .btn-success { background: #28a745; color: white; }
            .btn-success:hover { background: #218838; }
            .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
            .modal-content { background: white; margin: 5% auto; padding: 20px; width: 90%; max-width: 600px; border-radius: 10px; max-height: 80%; overflow-y: auto; }
            .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #e0e0e0; }
            .close { font-size: 28px; font-weight: bold; cursor: pointer; color: #aaa; }
            .close:hover { color: #000; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
            .form-group input, .form-group textarea { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 5px; font-family: monospace; }
            .loading { text-align: center; padding: 40px; color: #667eea; }
            .export-section { margin-top: 20px; padding-top: 20px; border-top: 2px solid #e0e0e0; }
            @media (max-width: 768px) { .container { flex-direction: column; } .sidebar { width: 100%; } .stats { flex-direction: column; } }
        </style>
    </head>
    <body>
        <div class="header">
            <h1><i class="icon ion-database"></i> SQLite Database Manager</h1>
            <p>Native SQLite database viewer and manager</p>
        </div>
        <div class="container">
            <div class="sidebar">
                <h3><i class="icon ion-filing"></i> Tables</h3>
                <ul class="table-list" id="table-list"><li>Loading...</li></ul>
            </div>
            <div class="content"><div id="table-content"><div class="loading">Select a table from the left to view data</div></div></div>
        </div>
        <div id="modal" class="modal">
            <div class="modal-content">
                <div class="modal-header"><h2 id="modal-title">Add Record</h2><span class="close">&times;</span></div>
                <div id="modal-body"></div>
            </div>
        </div>
        <script>
            let currentTable = '', currentData = [], currentColumns = [];
            async function loadTables() {
                try {
                    const response = await fetch('/db-viewer/tables');
                    const tables = await response.json();
                    const tableList = document.getElementById('table-list');
                    tableList.innerHTML = '';
                    tables.forEach(table => {
                        const li = document.createElement('li');
                        li.innerHTML = `<i class="icon ion-grid"></i> ${table}`;
                        li.onclick = () => loadTableData(table);
                        tableList.appendChild(li);
                    });
                } catch (error) { console.error('Error loading tables:', error); }
            }
            async function loadTableData(tableName) {
                currentTable = tableName;
                document.querySelectorAll('.table-list li').forEach(li => { li.classList.remove('active'); if (li.textContent.trim() === tableName) li.classList.add('active'); });
                try {
                    const response = await fetch(`/db-viewer/table/${tableName}`);
                    const data = await response.json();
                    currentData = data.data;
                    currentColumns = data.columns;
                    displayTable(data);
                } catch (error) { console.error('Error loading table data:', error); }
            }
            function displayTable(data) {
                const content = document.getElementById('table-content');
                let html = `<div class="table-info"><h2><i class="icon ion-android-list"></i> Table: ${data.table_name}</h2>
                    <div class="stats"><div class="stat-card"><strong><i class="icon ion-document-text"></i> Total Records:</strong> ${data.total_records}</div>
                    <div class="stat-card"><strong><i class="icon ion-cube"></i> Total Columns:</strong> ${data.columns.length}</div></div></div>
                    <div class="action-buttons"><button class="btn btn-success" onclick="showAddModal()"><i class="icon ion-plus"></i> Add New Record</button>
                    <button class="btn btn-primary" onclick="exportTable()"><i class="icon ion-ios-download"></i> Export to CSV</button>
                    <button class="btn btn-danger" onclick="refreshTable()"><i class="icon ion-refresh"></i> Refresh</button></div>`;
                if (data.data.length === 0) html += '<p>No data found in this table.</p>';
                else {
                    html += '<div style="overflow-x: auto;"><table><thead><tr>';
                    data.columns.forEach(col => html += `<th>${col}</th>`);
                    html += '<th>Actions</th></tr></thead><tbody>';
                    data.data.forEach((row, index) => {
                        html += '<tr>';
                        data.columns.forEach(col => { let value = row[col]; if (value === null) value = '<em>NULL</em>'; if (typeof value === 'object') value = JSON.stringify(value); html += `<td>${value}</td>`; });
                        html += `<td><button class="btn" style="background:#ffc107;color:#333;margin-right:5px;" onclick="showEditModal(${index})"><i class="icon ion-edit"></i> Edit</button>
                        <button class="btn" style="background:#dc3545;color:white;" onclick="deleteRecord(${row.id || index})"><i class="icon ion-trash-b"></i> Delete</button></td></tr>`;
                    });
                    html += '</tbody></table></div>';
                }
                content.innerHTML = html;
            }
            function showAddModal() {
                const modal = document.getElementById('modal'), modalTitle = document.getElementById('modal-title'), modalBody = document.getElementById('modal-body');
                modalTitle.textContent = `Add New Record to ${currentTable}`;
                let formHtml = '<form id="record-form">';
                currentColumns.forEach(col => { if (col !== 'id' && !col.includes('timestamp')) formHtml += `<div class="form-group"><label>${col}:</label><input type="text" name="${col}" placeholder="Enter ${col}" required></div>`; });
                formHtml += `<div class="form-group"><button type="submit" class="btn btn-success"><i class="icon ion-checkmark"></i> Save Record</button>
                <button type="button" class="btn" onclick="closeModal()"><i class="icon ion-close"></i> Cancel</button></div></form>`;
                modalBody.innerHTML = formHtml;
                modal.style.display = 'block';
                document.getElementById('record-form').onsubmit = async (e) => { e.preventDefault(); const formData = new FormData(e.target); const data = {}; formData.forEach((value, key) => { data[key] = isNaN(value) ? value : parseFloat(value); }); await addRecord(data); };
            }
            function showEditModal(index) {
                const row = currentData[index], modal = document.getElementById('modal'), modalTitle = document.getElementById('modal-title'), modalBody = document.getElementById('modal-body');
                modalTitle.textContent = `Edit Record in ${currentTable}`;
                let formHtml = '<form id="record-form">';
                currentColumns.forEach(col => { let value = row[col]; if (value === null) value = ''; if (col !== 'id' && !col.includes('timestamp')) formHtml += `<div class="form-group"><label>${col}:</label><input type="text" name="${col}" value="${value}" required></div>`; });
                formHtml += `<div class="form-group"><button type="submit" class="btn btn-success"><i class="icon ion-checkmark"></i> Update Record</button>
                <button type="button" class="btn" onclick="closeModal()"><i class="icon ion-close"></i> Cancel</button></div></form>`;
                modalBody.innerHTML = formHtml;
                modal.style.display = 'block';
                document.getElementById('record-form').onsubmit = async (e) => { e.preventDefault(); const formData = new FormData(e.target); const data = {}; formData.forEach((value, key) => { data[key] = isNaN(value) ? value : parseFloat(value); }); await updateRecord(row.id, data); };
            }
            async function addRecord(data) { try { const response = await fetch(`/db-viewer/table/${currentTable}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); if (response.ok) { alert('Record added successfully!'); closeModal(); loadTableData(currentTable); } else alert('Error adding record'); } catch (error) { console.error('Error:', error); alert('Error adding record'); } }
            async function updateRecord(id, data) { try { const response = await fetch(`/db-viewer/table/${currentTable}/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); if (response.ok) { alert('Record updated successfully!'); closeModal(); loadTableData(currentTable); } else alert('Error updating record'); } catch (error) { console.error('Error:', error); alert('Error updating record'); } }
            async function deleteRecord(id) { if (confirm('Are you sure you want to delete this record?')) { try { const response = await fetch(`/db-viewer/table/${currentTable}/${id}`, { method: 'DELETE' }); if (response.ok) { alert('Record deleted successfully!'); loadTableData(currentTable); } else alert('Error deleting record'); } catch (error) { console.error('Error:', error); alert('Error deleting record'); } } }
            function exportTable() { window.location.href = `/db-viewer/export/${currentTable}`; }
            function refreshTable() { loadTableData(currentTable); }
            function closeModal() { document.getElementById('modal').style.display = 'none'; }
            document.querySelector('.close').onclick = closeModal;
            window.onclick = function(event) { if (event.target === document.getElementById('modal')) closeModal(); }
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
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        result = db.execute(text(f"SELECT * FROM {table_name}"))
        data = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"table_name": table_name, "columns": columns, "data": data, "total_records": len(data)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/table/{table_name}")
def add_record(table_name: str, record: dict, db: Session = Depends(get_db)):
    try:
        columns = ', '.join(record.keys())
        placeholders = ', '.join([f":{key}" for key in record.keys()])
        query = text(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})")
        db.execute(query, record)
        db.commit()
        return {"message": "Record added successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/table/{table_name}/{record_id}")
def update_record(table_name: str, record_id: int, record: dict, db: Session = Depends(get_db)):
    try:
        set_clause = ', '.join([f"{key} = :{key}" for key in record.keys()])
        query = text(f"UPDATE {table_name} SET {set_clause} WHERE id = :id")
        record['id'] = record_id
        db.execute(query, record)
        db.commit()
        return {"message": "Record updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/table/{table_name}/{record_id}")
def delete_record(table_name: str, record_id: int, db: Session = Depends(get_db)):
    try:
        query = text(f"DELETE FROM {table_name} WHERE id = :id")
        db.execute(query, {"id": record_id})
        db.commit()
        return {"message": "Record deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/export/{table_name}")
def export_table_csv(table_name: str, db: Session = Depends(get_db)):
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    result = db.execute(text(f"SELECT * FROM {table_name}"))
    data = result.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    writer.writerows(data)
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={table_name}.csv"})