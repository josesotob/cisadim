from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime
import random
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
CORS(app)

# ── GOOGLE SHEETS SETUP ─────────────────────────────────────
SHEET_ID = "1E6Yqudw0c2MKjUsi9wkFxNQsFQLfTYhi0T_NK2FXzCE"

def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        return None
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

# ── DATABASE SETUP ──────────────────────────────────────────
# This creates the cisadim.db file automatically if it doesn't exist
DB_PATH = "cisadim.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS quejas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            referencia  TEXT,
            fecha_envio TEXT,

            -- Section 1: Client data
            nombre      TEXT,
            cargo       TEXT,
            empresa     TEXT,
            correo      TEXT,
            telefono    TEXT,

            -- Section 2: Work description
            fecha_trabajo   TEXT,
            codigo_servicio TEXT,
            tipo_servicio   TEXT,
            instrumento     TEXT,

            -- Section 3: Complaint info
            fecha_queja TEXT,
            naturaleza  TEXT,
            descripcion TEXT,
            evidencia   TEXT,

            -- Section 4: Requested action
            accion      TEXT,
            accion_otra TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ── SERVE THE WEBPAGE ────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'cisadim.html')

# ── RECEIVE THE FORM ─────────────────────────────────────────
@app.route('/enviar', methods=['POST'])
def enviar():
    data = request.json

    # Generate a reference number like QR-2025-4823
    ref = f"QR-{datetime.now().year}-{random.randint(1000, 9999)}"
    fecha_envio = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO quejas (
            referencia, fecha_envio,
            nombre, cargo, empresa, correo, telefono,
            fecha_trabajo, codigo_servicio, tipo_servicio, instrumento,
            fecha_queja, naturaleza, descripcion, evidencia,
            accion, accion_otra
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        ref, fecha_envio,
        data.get('nombre'), data.get('cargo'), data.get('empresa'),
        data.get('correo'), data.get('telefono'),
        data.get('fechaTrabajo'), data.get('codigoServicio'),
        data.get('tipoServicio'), data.get('instrumento'),
        data.get('fechaQueja'), data.get('naturaleza'),
        data.get('descripcion'), data.get('evidencia'),
        data.get('accion'), data.get('accionOtra')
    ))
    conn.commit()
    conn.close()

    print(f"✓ Nueva queja recibida: {ref} de {data.get('nombre')} ({data.get('correo')})")

    # ── SAVE TO GOOGLE SHEETS ──
    try:
        sheet = get_sheet()
        if sheet:
            sheet.append_row([
                ref, fecha_envio,
                data.get('nombre'), data.get('cargo'), data.get('empresa'),
                data.get('correo'), data.get('telefono'),
                data.get('fechaTrabajo'), data.get('codigoServicio'),
                data.get('tipoServicio'), data.get('instrumento'),
                data.get('fechaQueja'), data.get('naturaleza'),
                data.get('descripcion'), data.get('evidencia'),
                data.get('accion'), data.get('accionOtra')
            ])
            print(f"✓ Guardado en Google Sheets")
    except Exception as e:
        print(f"⚠ Error guardando en Sheets: {e}")

    return jsonify({ "ok": True, "referencia": ref })

# ── ADMIN PAGE — see all complaints ─────────────────────────
@app.route('/admin')
def admin():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM quejas ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
    <meta charset="UTF-8">
    <title>Admin – Quejas CISADIM</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', sans-serif; background: #f7f5f1; color: #1c1c1c; }

        /* TOP BAR */
        .topbar {
            background: #0d1f3c; color: white;
            padding: 1rem 2rem; display: flex; align-items: center; justify-content: space-between;
        }
        .topbar h1 { font-size: 1.1rem; font-weight: 600; }
        .topbar span { font-size: 0.8rem; color: rgba(255,255,255,0.5); }
        .logo { font-size: 1.2rem; font-weight: 700; }
        .logo b { color: #c8973a; }

        /* LAYOUT */
        .layout { display: flex; height: calc(100vh - 56px); }

        /* LEFT — list */
        .list-panel {
            width: 360px; min-width: 360px;
            background: white; border-right: 1px solid #e0dbd4;
            overflow-y: auto;
        }
        .list-header {
            padding: 1rem 1.2rem; border-bottom: 1px solid #e0dbd4;
            font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.07em; color: #6b6560;
            display: flex; justify-content: space-between; align-items: center;
        }
        .list-header .badge {
            background: #0d1f3c; color: white;
            border-radius: 20px; padding: 0.15rem 0.6rem;
            font-size: 0.72rem;
        }
        .complaint-item {
            padding: 1rem 1.2rem; border-bottom: 1px solid #f0ece6;
            cursor: pointer; transition: background 0.15s;
        }
        .complaint-item:hover { background: #faf8f5; }
        .complaint-item.active { background: #eef2f8; border-left: 3px solid #0d1f3c; }
        .item-ref { font-size: 0.75rem; font-weight: 600; color: #c8973a; margin-bottom: 0.2rem; }
        .item-name { font-size: 0.9rem; font-weight: 500; color: #1c1c1c; }
        .item-meta { font-size: 0.75rem; color: #6b6560; margin-top: 0.15rem; }
        .item-preview {
            font-size: 0.78rem; color: #999; margin-top: 0.3rem;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .nat-badge {
            display: inline-block; font-size: 0.68rem; font-weight: 600;
            padding: 0.15rem 0.5rem; border-radius: 3px; margin-top: 0.3rem;
            text-transform: uppercase; letter-spacing: 0.04em;
        }
        .nat-tec  { background: #e8f0fe; color: #1a56a0; }
        .nat-adm  { background: #fef3e2; color: #a05a00; }
        .nat-ate  { background: #e8f5ee; color: #1a6e40; }

        /* RIGHT — detail */
        .detail-panel {
            flex: 1; overflow-y: auto; padding: 2rem;
        }
        .detail-empty {
            height: 100%; display: flex; flex-direction: column;
            align-items: center; justify-content: center; color: #aaa;
            font-size: 0.95rem; gap: 0.5rem;
        }
        .detail-empty .icon { font-size: 2.5rem; }

        .detail-card { display: none; }
        .detail-card.show { display: block; }

        .detail-top {
            display: flex; align-items: flex-start;
            justify-content: space-between; margin-bottom: 1.5rem;
            flex-wrap: wrap; gap: 1rem;
        }
        .detail-ref { font-size: 1.4rem; font-weight: 700; color: #c8973a; }
        .detail-date { font-size: 0.8rem; color: #6b6560; margin-top: 0.2rem; }

        .section-block {
            background: white; border: 1px solid #e0dbd4;
            border-radius: 6px; margin-bottom: 1.2rem; overflow: hidden;
        }
        .section-block-title {
            background: #f7f5f1; border-bottom: 1px solid #e0dbd4;
            padding: 0.6rem 1.2rem; font-size: 0.72rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.08em; color: #6b6560;
            display: flex; align-items: center; gap: 0.5rem;
        }
        .section-block-body { padding: 1.2rem; }
        .field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        .field-item label {
            font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.06em; color: #999; display: block; margin-bottom: 0.2rem;
        }
        .field-item p { font-size: 0.88rem; color: #1c1c1c; }
        .field-item.full { grid-column: 1 / -1; }
        .desc-text {
            font-size: 0.9rem; line-height: 1.7; color: #1c1c1c;
            background: #fafafa; border: 1px solid #e0dbd4;
            border-radius: 4px; padding: 1rem;
        }

        .empty-state { text-align: center; padding: 3rem; color: #6b6560; }
    </style>
    </head>
    <body>

    <div class="topbar">
        <div class="logo">CISA<b>DIM</b> &nbsp;<span style="font-weight:300;color:rgba(255,255,255,0.4)">|</span>&nbsp; Panel de Quejas</div>
        <span>FC 7.9-01_VIG · v1.0</span>
    </div>

    <div class="layout">
    """

    # ── LEFT PANEL ──
    html += '<div class="list-panel">'
    html += f'<div class="list-header"><span>Quejas recibidas</span><span class="badge">{len(rows)}</span></div>'

    if not rows:
        html += '<div class="empty-state">No hay quejas registradas aún.</div>'
    else:
        for row in rows:
            nat = row['naturaleza'] or ''
            nat_class = 'nat-tec' if 'Técnico' in nat else ('nat-adm' if 'Admin' in nat else 'nat-ate')
            preview = (row['descripcion'] or '')[:80]
            html += f"""
            <div class="complaint-item" onclick="showDetail({row['id']})" id="item-{row['id']}">
                <div class="item-ref">{row['referencia']}</div>
                <div class="item-name">{row['nombre']}</div>
                <div class="item-meta">{row['fecha_envio']} · {row['correo']}</div>
                <div class="item-preview">{preview}...</div>
                <span class="nat-badge {nat_class}">{nat}</span>
            </div>
            """
    html += '</div>'

    # ── RIGHT PANEL ──
    html += '<div class="detail-panel" id="detailPanel">'
    html += '''
        <div class="detail-empty" id="emptyState">
            <div class="icon">📋</div>
            <div>Seleccione una queja para ver el detalle completo</div>
        </div>
    '''

    if rows:
        for row in rows:
            nat = row['naturaleza'] or '—'
            nat_class = 'nat-tec' if 'Técnico' in nat else ('nat-adm' if 'Admin' in nat else 'nat-ate')
            html += f"""
            <div class="detail-card" id="detail-{row['id']}">
                <div class="detail-top">
                    <div>
                        <div class="detail-ref">{row['referencia']}</div>
                        <div class="detail-date">Recibido el {row['fecha_envio']}</div>
                    </div>
                    <span class="nat-badge {nat_class}" style="font-size:0.8rem;padding:0.3rem 0.8rem">{nat}</span>
                </div>

                <div class="section-block">
                    <div class="section-block-title">👤 Datos del Cliente</div>
                    <div class="section-block-body">
                        <div class="field-grid">
                            <div class="field-item"><label>Nombre</label><p>{row['nombre']}</p></div>
                            <div class="field-item"><label>Cargo</label><p>{row['cargo']}</p></div>
                            <div class="field-item"><label>Empresa</label><p>{row['empresa'] or '—'}</p></div>
                            <div class="field-item"><label>Correo</label><p>{row['correo']}</p></div>
                            <div class="field-item"><label>Teléfono</label><p>{row['telefono']}</p></div>
                        </div>
                    </div>
                </div>

                <div class="section-block">
                    <div class="section-block-title">🔧 Trabajo Realizado</div>
                    <div class="section-block-body">
                        <div class="field-grid">
                            <div class="field-item"><label>Fecha de Trabajo</label><p>{row['fecha_trabajo']}</p></div>
                            <div class="field-item"><label>Código del Servicio</label><p>{row['codigo_servicio']}</p></div>
                            <div class="field-item"><label>Tipo de Servicio</label><p>{row['tipo_servicio']}</p></div>
                            <div class="field-item"><label>Instrumento Calibrado</label><p>{row['instrumento']}</p></div>
                        </div>
                    </div>
                </div>

                <div class="section-block">
                    <div class="section-block-title">📝 Descripción de la Queja</div>
                    <div class="section-block-body">
                        <div class="field-grid" style="margin-bottom:1rem">
                            <div class="field-item"><label>Fecha de Queja</label><p>{row['fecha_queja']}</p></div>
                            <div class="field-item"><label>Evidencia Adjunta</label><p>{row['evidencia'] or 'Ninguna'}</p></div>
                        </div>
                        <div class="field-item full">
                            <label>Descripción completa</label>
                            <div class="desc-text">{row['descripcion']}</div>
                        </div>
                    </div>
                </div>

                <div class="section-block">
                    <div class="section-block-title">✅ Acción Solicitada</div>
                    <div class="section-block-body">
                        <div class="field-grid">
                            <div class="field-item"><label>Acción</label><p>{row['accion']}</p></div>
                            <div class="field-item"><label>Especificación</label><p>{row['accion_otra'] or '—'}</p></div>
                        </div>
                    </div>
                </div>
            </div>
            """

    html += '</div></div>'

    html += """
    <script>
    function showDetail(id) {
        document.querySelectorAll('.detail-card').forEach(d => d.classList.remove('show'));
        document.querySelectorAll('.complaint-item').forEach(i => i.classList.remove('active'));
        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('detail-' + id).classList.add('show');
        document.getElementById('item-' + id).classList.add('active');
    }
    </script>
    </body></html>
    """
    return html

# ── START ────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("─────────────────────────────────────")
    print("  CISADIM backend running!")
    print("  Webpage  → http://localhost:5000")
    print("  Admin    → http://localhost:5000/admin")
    print("─────────────────────────────────────")
    app.run(debug=True)
