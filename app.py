import base64
from datetime import datetime, timedelta
import io
import os
import sqlite3
import traceback
import urllib.parse
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "chave_mestra_manutencao_predial_segura_2026"

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = False

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    try:
        import psycopg2
        import psycopg2.extras
        IS_POSTGRES = True
    except ImportError:
        IS_POSTGRES = False


class DBWrapper:
    def __init__(self, conn, is_pg=False):
        self.conn = conn
        self.is_pg = is_pg

    def execute(self, sql, params=None):
        cur = self.conn.cursor()
        if self.is_pg:
            cur.execute(sql.replace("?", "%s"), params or ())
        else:
            cur.execute(sql, params or ())
        return cur

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        self.close()


def get_db():
    if IS_POSTGRES:
        conn = psycopg2.connect(
            DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor
        )
        return DBWrapper(conn, is_pg=True)
    app_dir = os.environ.get(
        "ANDROID_PRIVATE", os.path.dirname(os.path.abspath(__file__))
    )
    conn = sqlite3.connect(os.path.join(app_dir, "manutencao.db"))
    conn.row_factory = sqlite3.Row
    return DBWrapper(conn, is_pg=False)


def init_db():
    with get_db() as db:
        if IS_POSTGRES:
            db.execute("""CREATE TABLE IF NOT EXISTS ordens_servico (
                id SERIAL PRIMARY KEY, equipamento TEXT NOT NULL, solicitante TEXT NOT NULL, problema TEXT NOT NULL,
                data_abertura TEXT NOT NULL, operador TEXT, data_finalizacao TEXT, servico_executado TEXT, pecas TEXT,
                status TEXT NOT NULL, foto_problema TEXT);""")
            db.execute("ALTER TABLE ordens_servico ADD COLUMN IF NOT EXISTS foto_problema TEXT;")
            db.execute("""CREATE TABLE IF NOT EXISTS preventivas (
                id SERIAL PRIMARY KEY, equipamento TEXT NOT NULL, solicitante TEXT NOT NULL, descricao TEXT NOT NULL,
                periodicidade_dias INTEGER NOT NULL, proxima_data TEXT NOT NULL, ultima_geracao TEXT, ativo INTEGER DEFAULT 1);""")
            db.execute("""CREATE TABLE IF NOT EXISTS configuracoes (
                id INTEGER PRIMARY KEY, nome_empresa TEXT, subtitulo TEXT, contato TEXT, logo_base64 TEXT);""")
            db.execute("INSERT INTO configuracoes (id, nome_empresa, subtitulo) VALUES (1, 'Manutenção Predial', 'Gestão Operacional') ON CONFLICT (id) DO NOTHING;")
            db.execute("""CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY, usuario TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, nome TEXT NOT NULL,
                nivel TEXT DEFAULT 'comum', foto_base64 TEXT);""")
            if not db.execute("SELECT id FROM usuarios WHERE usuario = 'admin'").fetchone():
                db.execute(
                    "INSERT INTO usuarios (usuario, senha, nome, nivel) VALUES ('admin', ?, 'Administrador Principal', 'admin')",
                    (generate_password_hash("12345"),),
                )
        else:
            db.execute("""CREATE TABLE IF NOT EXISTS ordens_servico (
                id INTEGER PRIMARY KEY AUTOINCREMENT, equipamento TEXT NOT NULL, solicitante TEXT NOT NULL, problema TEXT NOT NULL,
                data_abertura TEXT NOT NULL, operador TEXT, data_finalizacao TEXT, servico_executado TEXT, pecas TEXT,
                status TEXT NOT NULL, foto_problema TEXT);""")
            cols = [c[1] for c in db.execute("PRAGMA table_info(ordens_servico)").fetchall()]
            if "foto_problema" not in cols:
                db.execute("ALTER TABLE ordens_servico ADD COLUMN foto_problema TEXT")
            db.execute("""CREATE TABLE IF NOT EXISTS preventivas (
                id INTEGER PRIMARY KEY AUTOINCREMENT, equipamento TEXT NOT NULL, solicitante TEXT NOT NULL, descricao TEXT NOT NULL,
                periodicidade_dias INTEGER NOT NULL, proxima_data TEXT NOT NULL, ultima_geracao TEXT, ativo INTEGER DEFAULT 1);""")
            db.execute("""CREATE TABLE IF NOT EXISTS configuracoes (
                id INTEGER PRIMARY KEY, nome_empresa TEXT, subtitulo TEXT, contato TEXT, logo_base64 TEXT);""")
            db.execute("INSERT OR IGNORE INTO configuracoes (id, nome_empresa, subtitulo) VALUES (1, 'Manutenção Predial', 'Gestão Operacional')")
            db.execute("""CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, nome TEXT NOT NULL,
                nivel TEXT DEFAULT 'comum', foto_base64 TEXT);""")
            if not db.execute("SELECT id FROM usuarios WHERE usuario = 'admin'").fetchone():
                db.execute(
                    "INSERT INTO usuarios (usuario, senha, nome, nivel) VALUES ('admin', ?, 'Administrador Principal', 'admin')",
                    (generate_password_hash("12345"),),
                )


init_db()


def verificar_gerar_preventivas():
    hoje = datetime.now().strftime("%Y-%m-%d")
    with get_db() as db:
        for p in db.execute("SELECT * FROM preventivas WHERE ativo = 1 AND proxima_data <= ?", (hoje,)).fetchall():
            agora = datetime.now().strftime("%d/%m/%Y %H:%M")
            db.execute(
                "INSERT INTO ordens_servico (equipamento, solicitante, problema, data_abertura, status, foto_problema) VALUES (?, ?, ?, ?, 'ABERTA', '')",
                (
                    p["equipamento"],
                    f"Preventiva ({p['solicitante']})",
                    f"[ROTINA PREVENTIVA - A CADA {p['periodicidade_dias']} DIAS]\n" + p["descricao"],
                    agora,
                ),
            )
            try:
                dt_base = datetime.strptime(p["proxima_data"], "%Y-%m-%d")
            except Exception:
                dt_base = datetime.now()
            dias = int(p["periodicidade_dias"]) if p["periodicidade_dias"] > 0 else 30
            while dt_base.strftime("%Y-%m-%d") <= hoje:
                dt_base += timedelta(days=dias)
            db.execute(
                "UPDATE preventivas SET proxima_data = ?, ultima_geracao = ? WHERE id = ?",
                (dt_base.strftime("%Y-%m-%d"), hoje, p["id"]),
            )


def obter_configuracoes():
    with get_db() as db:
        return db.execute("SELECT * FROM configuracoes WHERE id = 1").fetchone()


def montar_texto_whatsapp(os_item, cfg):
    empresa = cfg["nome_empresa"] if cfg else "Manutenção Predial"
    linhas = [
        "*COMPROVANTE DE MANUTENÇÃO* 🛠️",
        "-----------------------------------",
        "🏢 *Empresa:* " + str(empresa),
        "📋 *OS Nº:* #" + f"{os_item['id']:05d}",
        "📌 *Status:* " + str(os_item["status"]),
        "",
        "🔧 *Equipamento/Local:* " + str(os_item["equipamento"]),
        "👤 *Solicitante:* " + str(os_item["solicitante"]),
        "👷 *Técnico:* " + str(os_item["operador"] or "Não atribuído"),
        "📅 *Data Conclusão:* " + str(os_item["data_finalizacao"] or os_item["data_abertura"]),
        "",
        "⚠️ *Defeito Informado:*",
        str(os_item["problema"]),
        "",
        "✅ *Serviço Realizado:*",
        str(os_item["servico_executado"] or "Em andamento"),
        "",
        "📦 *Peças/Insumos:*",
        str(os_item["pecas"] or "Nenhum material extra cadastrado"),
        "-----------------------------------",
        "_Comprovante emitido via Sistema de Manutenção_",
    ]
    return "\n".join(linhas)


@app.context_processor
def injetar_usuario():
    info = {
        "usuario_logado_info": None,
        "modo_nuvem": IS_POSTGRES,
        "ultimo_id_sistema": 0,
        "eh_admin": False,
    }
    if "usuario" in session:
        with get_db() as db:
            u = db.execute("SELECT * FROM usuarios WHERE usuario = ?", (session["usuario"],)).fetchone()
            info["usuario_logado_info"] = u
            if u:
                info["eh_admin"] = u["usuario"] == "admin" or u["nivel"] == "admin"
            info["ultimo_id_sistema"] = db.execute("SELECT COALESCE(MAX(id), 0) FROM ordens_servico").fetchone()[0]
    return info


@app.before_request
def checar_auth():
    rotas = ["login", "static", "recibo", "ping", "api_status_sync", "compartilhar_whatsapp"]
    if request.endpoint not in rotas and "usuario" not in session:
        return redirect(url_for("login"))


@app.route("/ping")
def ping():
    return "pong", 200


@app.route("/api/status-sync")
def api_status_sync():
    verificar_gerar_preventivas()
    with get_db() as db:
        tot, ult_id = db.execute("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM ordens_servico").fetchone()
        concl = db.execute("SELECT COUNT(*) FROM ordens_servico WHERE status = 'CONCLUÍDA'").fetchone()[0]
        ult_chamado = None
        if ult_id > 0:
            r = db.execute("SELECT id, equipamento, solicitante, problema, status FROM ordens_servico WHERE id = ?", (ult_id,)).fetchone()
            if r:
                ult_chamado = {
                    "id": r["id"],
                    "equipamento": r["equipamento"],
                    "solicitante": r["solicitante"],
                    "problema": r["problema"][:60],
                    "status": r["status"],
                }
    return jsonify({
        "total": tot,
        "ultimo_id": ult_id,
        "concluidas": concl,
        "ultimo_chamado": ult_chamado,
    })


BASE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ cfg['nome_empresa'] }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,500,1,0" />
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background:#f8f9ff; font-family:'Plus Jakarta Sans',sans-serif; margin:0; padding-bottom:95px; }
        .m3-bar { background:#fff; padding:12px 18px; border-bottom:1px solid #c3c7d0; position:sticky; top:0; z-index:100; }
        .m3-icon { background:#e0edff; color:#004c78; width:40px; height:40px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; text-decoration:none; border:none; }
        .m3-icon.danger { background:#ffe0e0; color:#ba1a1a; }
        .m3-card { background:#fff; border-radius:20px; border:1px solid #c3c7d0; box-shadow:0 2px 6px rgba(0,0,0,0.04); padding:20px; }
        .m3-btn { background:#00639b; color:#fff; border:none; border-radius:50px; padding:10px 20px; font-weight:600; text-decoration:none; display:inline-flex; align-items:center; gap:8px; }
        .m3-btn-sec { background:#e0edff; color:#001d33; border:none; border-radius:50px; padding:8px 16px; font-weight:600; text-decoration:none; display:inline-flex; align-items:center; gap:6px; }
        .m3-input { background:#f2f3f9; border:1px solid #c3c7d0; border-radius:12px; padding:12px; width:100%; font-weight:500; margin-bottom:12px; }
        .m3-fab { position:fixed; bottom:24px; right:24px; background:#cee5ff; color:#001d33; border-radius:30px; padding:14px 22px; font-weight:700; text-decoration:none; box-shadow:0 4px 12px rgba(0,0,0,0.15); z-index:90; }
        #toastNotif { position:fixed; top:18px; left:50%; transform:translateX(-50%); z-index:999; width:90%; max-width:440px; background:#fff; border:2px solid #00639b; border-radius:18px; padding:14px; display:none; box-shadow:0 10px 25px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <header class="m3-bar mb-3 d-flex justify-content-between align-items-center">
        <a href="/" class="text-decoration-none d-flex align-items-center gap-2">
            {% if cfg['logo_base64'] %}<img src="{{ cfg['logo_base64'] }}" style="height:36px; max-width:80px; object-fit:contain;">{% else %}<span class="material-symbols-rounded fs-2 text-primary">domain</span>{% endif %}
            <div><h6 class="fw-bold mb-0 text-dark">{{ cfg['nome_empresa'] }}</h6><small class="text-muted">{{ cfg['subtitulo'] }}</small></div>
        </a>
        <div class="d-flex gap-2">
            <a href="/preventivas" class="m3-icon" title="Preventivas"><span class="material-symbols-rounded">event_repeat</span></a>
            <button id="btnSom" onclick="alternarSom()" class="m3-icon"><span class="material-symbols-rounded" id="icoSom">notifications_active</span></button>
            <a href="/usuarios" class="m3-icon" title="Usuários"><span class="material-symbols-rounded">group</span></a>
            <a href="/configuracoes" class="m3-icon" title="Ajustes"><span class="material-symbols-rounded">settings</span></a>
            <a href="/logout" class="m3-icon danger" title="Sair"><span class="material-symbols-rounded">logout</span></a>
        </div>
    </header>
    <div id="toastNotif">
        <div class="d-flex align-items-center justify-content-between mb-1"><span class="badge bg-danger">NOVA REQUISIÇÃO</span><button class="btn-close btn-sm" onclick="fecharToast()"></button></div>
        <h6 class="fw-bold mb-1" id="notifEq"></h6><small class="text-secondary d-block mb-2" id="notifSol"></small>
        <a href="/" class="btn btn-sm btn-primary rounded-pill px-3">Ver Ordem</a>
    </div>
    <main class="container">
        <!-- CONTEUDO -->
    </main>
    <!-- FAB -->
    <script>
    let som = localStorage.getItem('som') !== '0';
    let ultId = {{ ultimo_id_sistema or 0 }};
    function alternarSom() { som = !som; localStorage.setItem('som', som ? '1':'0'); document.getElementById('icoSom').innerText = som ? 'notifications_active':'notifications_off'; }
    function tocarAlerta() {
        if (!som) return;
        try {
            let ctx = new (window.AudioContext || window.webkitAudioContext)();
            let o = ctx.createOscillator(), g = ctx.createGain();
            o.frequency.setValueAtTime(600, ctx.currentTime);
            o.frequency.exponentialRampToValueAtTime(900, ctx.currentTime + 0.3);
            g.gain.setValueAtTime(0.5, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
            o.connect(g); g.connect(ctx.destination);
            o.start(); o.stop(ctx.currentTime + 0.4);
        } catch(e){}
    }
    function fecharToast() { document.getElementById('toastNotif').style.display='none'; }
    setInterval(() => {
        fetch('/api/status-sync').then(r=>r.json()).then(d=>{
            if (d.ultimo_id > ultId) {
                ultId = d.ultimo_id;
                tocarAlerta();
                if(d.ultimo_chamado){
                    document.getElementById('notifEq').innerText = '#' + d.ultimo_chamado.id + ' ' + d.ultimo_chamado.equipamento;
                    document.getElementById('notifSol').innerText = 'Solicitante: ' + d.ultimo_chamado.solicitante;
                    document.getElementById('toastNotif').style.display = 'block';
                }
                if (window.location.pathname === '/') setTimeout(()=>window.location.reload(), 3000);
            }
        });
    }, 4000);
    </script>
</body>
</html>"""

INDEX_BODY = """
<div class="row g-2 mb-3">
    <div class="col-4"><div class="m3-card text-center p-2"><small class="text-muted fw-bold">TOTAL</small><h5 class="fw-bold mb-0 text-primary">{{ total_os }}</h5></div></div>
    <div class="col-4"><div class="m3-card text-center p-2"><small class="text-muted fw-bold">ABERTAS</small><h5 class="fw-bold mb-0 text-warning">{{ os_abertas }}</h5></div></div>
    <div class="col-4"><div class="m3-card text-center p-2"><small class="text-muted fw-bold">CONCLUÍDAS</small><h5 class="fw-bold mb-0 text-success">{{ os_concluidas }}</h5></div></div>
</div>
<div class="m3-card mb-3 p-2"><input type="text" id="filtro" class="form-control border-0 bg-transparent" placeholder="Buscar chamados..." onkeyup="filtrar()"></div>
<div class="m3-card p-0 overflow-hidden"><table class="table align-middle mb-0"><thead class="table-light small">
<tr><th class="ps-3">OS</th><th>Foto</th><th>Equipamento</th><th>Solicitante</th><th>Técnico</th><th>Status</th><th class="text-end pe-3">Ações</th></tr></thead>
<tbody id="tabela">{% for os in ordens %}<tr class="linha-os">
<td class="ps-3 fw-bold text-primary">#{{ "%05d" % os['id'] }}</td>
<td>{% if os['foto_problema'] %}<img src="{{ os['foto_problema'] }}" style="width:36px;height:36px;object-fit:cover;border-radius:6px;cursor:pointer;" onclick="window.open('{{ os['foto_problema'] }}')">{% else %}<span class="text-muted">-</span>{% endif %}</td>
<td class="fw-bold">{{ os['equipamento'] }}</td><td>{{ os['solicitante'] }}</td>
<td>{{ os['operador'] or 'Pendente' }}</td>
<td><span class="badge {{ 'bg-warning text-dark' if os['status']=='ABERTA' else 'bg-success' }}">{{ os['status'] }}</span></td>
<td class="text-end pe-3">
{% if os['status']=='ABERTA' %}<a href="/finalizar/{{ os['id'] }}" class="btn btn-sm btn-primary rounded-pill px-2">Executar</a>
{% else %}<a href="/recibo/{{ os['id'] }}" class="btn btn-sm btn-secondary rounded-pill px-2">Recibo</a>{% endif %}
<a href="/excluir/{{ os['id'] }}" class="btn btn-sm btn-outline-danger rounded-pill px-2" onclick="return confirm('Excluir OS?');">X</a>
</td></tr>{% else %}<tr><td colspan="7" class="text-center py-4 text-muted">Nenhuma ordem de serviço.</td></tr>{% endfor %}</tbody></table></div>
<script>function filtrar(){let q=document.getElementById('filtro').value.toLowerCase();document.querySelectorAll('.linha-os').forEach(r=>{r.style.display=r.innerText.toLowerCase().includes(q)?'':'none';});}</script>
"""

LOGIN_HTML = """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#f8f9ff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;font-family:sans-serif;} .card{background:#fff;border-radius:24px;border:1px solid #c3c7d0;max-width:380px;width:100%;padding:30px;box-shadow:0 4px 15px rgba(0,0,0,0.05);}</style>
</head><body><div class="card text-center">
<h4 class="fw-bold mb-1">{{ cfg['nome_empresa'] }}</h4><small class="text-muted d-block mb-3">Acesso ao Painel</small>
{% if erro %}<div class="alert alert-danger py-1 small rounded-3">{{ erro }}</div>{% endif %}
<form method="POST"><input type="text" name="usuario" class="form-control mb-2 rounded-3" placeholder="Usuário" required autofocus>
<input type="password" name="senha" class="form-control mb-3 rounded-3" placeholder="Senha" required>
<button class="btn btn-primary w-100 rounded-pill py-2 fw-bold">Entrar</button></form>
<small class="text-muted d-block mt-3">Padrão: admin / 12345</small></div></body></html>"""

NOVA_BODY = """
<div class="m3-card" style="max-width:560px; margin:0 auto;">
<h5 class="fw-bold mb-3">Nova Requisição de Manutenção</h5>
<form method="POST"><input type="hidden" name="foto_problema" id="foto_b64" value="">
<label class="small fw-bold">EQUIPAMENTO / LOCAL:</label><input type="text" name="equipamento" class="m3-input" placeholder="Ex: Bomba D'água, Elevador" required>
<label class="small fw-bold">SOLICITANTE:</label><input type="text" name="solicitante" class="m3-input" placeholder="Ex: Portaria, Apto 101" required>
<label class="small fw-bold">DESCRIÇÃO DO DEFEITO:</label><textarea name="problema" rows="3" class="m3-input" placeholder="Descreva o problema observado..." required></textarea>
<div class="p-2 border rounded-3 bg-light text-center mb-3">
<img id="prevFoto" src="" style="max-height:140px; display:none; margin:0 auto 10px; border-radius:8px;">
<div class="d-flex gap-2 justify-content-center">
<label class="m3-btn-sec py-1 px-3" style="cursor:pointer;">📷 Foto Câmera<input type="file" accept="image/*" capture="environment" style="display:none;" onchange="pegarFoto(this)"></label>
<label class="m3-btn-sec py-1 px-3" style="cursor:pointer;">🖼️ Galeria<input type="file" accept="image/*" style="display:none;" onchange="pegarFoto(this)"></label>
</div></div>
<div class="d-flex justify-content-between"><a href="/" class="m3-btn-sec">Voltar</a><button class="m3-btn">Salvar Requisição</button></div>
</form></div>
<script>
function pegarFoto(el){
    if (el.files && el.files[0]) {
        let r = new FileReader();
        r.onload = e => {
            let img = new Image();
            img.onload = () => {
                let c = document.createElement('canvas'), max = 1200;
                let w = img.width, h = img.height;
                if (w > max || h > max) { if (w > h) { h = Math.round(h*max/w); w = max; } else { w = Math.round(w*max/h); h = max; } }
                c.width = w; c.height = h;
                c.getContext('2d').drawImage(img, 0, 0, w, h);
                let b64 = c.toDataURL('image/jpeg', 0.85);
                document.getElementById('prevFoto').src = b64;
                document.getElementById('prevFoto').style.display = 'block';
                document.getElementById('foto_b64').value = b64;
            };
            img.src = e.target.result;
        };
        r.readAsDataURL(el.files[0]);
    }
}
</script>"""

FINALIZAR_BODY = """
<div class="m3-card" style="max-width:560px; margin:0 auto;">
<h5 class="fw-bold mb-3">Finalizar OS #{{ "%05d" % os['id'] }}</h5>
<div class="p-2 bg-light rounded-3 mb-3 small"><strong>Equipamento:</strong> {{ os['equipamento'] }}<br><strong>Problema:</strong> {{ os['problema'] }}</div>
<form method="POST">
<label class="small fw-bold">TÉCNICO / EXECUTOR:</label><input type="text" name="operador" class="m3-input" value="{{ os['operador'] or session.get('nome','') }}" required>
<label class="small fw-bold">DATA DE CONCLUSÃO:</label><input type="text" name="data_finalizacao" class="m3-input" value="{{ agora }}" required>
<label class="small fw-bold">PEÇAS / MATERIAIS:</label><input type="text" name="pecas" class="m3-input" placeholder="Ex: Relé, fiação, óleo">
<label class="small fw-bold">SERVIÇO EXECUTADO:</label><textarea name="servico_executado" rows="3" class="m3-input" required></textarea>
<div class="d-flex justify-content-between"><a href="/" class="m3-btn-sec">Voltar</a><button class="m3-btn">Concluir e Emitir Recibo</button></div>
</form></div>"""

RECIBO_HTML = """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><title>Recibo OS #{{ "%05d" % os['id'] }}</title>
<style>@page{size:A4;margin:8mm;} body{font-family:sans-serif;font-size:9pt;margin:0;} .via{border:1px solid #cbd5e1;border-radius:6px;padding:12px;height:130mm;box-sizing:border-box;}
.cut{height:8mm;border-top:1.5px dashed #94a3b8;margin:2mm 0;text-align:center;font-size:7pt;color:#64748b;} @media print{.no-p{display:none;}}</style>
</head><body>
<div class="no-p" style="padding:10px;text-align:center;background:#e0f2fe;margin-bottom:10px;">
<button onclick="acionarPrint()" style="padding:8px 16px;border-radius:20px;background:#00639b;color:#fff;border:none;font-weight:bold;cursor:pointer;">🖨️ Imprimir / Salvar PDF</button>
<button onclick="acionarZap()" style="padding:8px 16px;border-radius:20px;background:#25d366;color:#fff;border:none;font-weight:bold;cursor:pointer;">💬 WhatsApp</button>
<a href="/" style="margin-left:10px;color:#333;text-decoration:none;">⬅ Voltar</a>
</div>
<script>
const zapTxt = {{ texto_whatsapp | tojson }};
function acionarZap(){ document.title = 'CMD_WHATSAPP:' + encodeURIComponent(zapTxt); if(navigator.share){ navigator.share({title:'Recibo', text:zapTxt}); } else { window.open('https://wa.me/?text=' + encodeURIComponent(zapTxt), '_blank'); } }
function acionarPrint(){ document.title = 'CMD_PRINT:{{ os["id"] }}'; window.print(); }
if(window.location.search.includes('share=1')) setTimeout(acionarZap, 400);
</script>
{% macro render_via(titulo) %}
<div class="via">
<div style="display:flex;justify-content:space-between;border-bottom:2px solid #000;padding-bottom:4px;margin-bottom:6px;">
<div><strong>{{ titulo }}</strong><br><span style="font-size:11pt;font-weight:bold;">{{ cfg['nome_empresa'] }}</span></div>
<div style="text-align:right;"><span style="font-size:12pt;font-weight:bold;">OS #{{ "%05d" % os['id'] }}</span><br>Status: {{ os['status'] }}</div>
</div>
<p style="margin:4px 0;"><strong>Equipamento:</strong> {{ os['equipamento'] }} | <strong>Solicitante:</strong> {{ os['solicitante'] }}</p>
<p style="margin:4px 0;"><strong>Abertura:</strong> {{ os['data_abertura'] }} | <strong>Conclusão:</strong> {{ os['data_finalizacao'] or '-' }} | <strong>Técnico:</strong> {{ os['operador'] or '-' }}</p>
<div style="background:#f8fafc;padding:6px;border:1px solid #e2e8f0;margin:6px 0;"><strong>Defeito:</strong><br>{{ os['problema'] }}</div>
<div style="background:#f8fafc;padding:6px;border:1px solid #e2e8f0;margin:6px 0;"><strong>Serviço Técnico:</strong><br>{{ os['servico_executado'] or 'Em andamento' }}</div>
<div style="background:#f8fafc;padding:6px;border:1px solid #e2e8f0;margin:6px 0;"><strong>Peças/Insumos:</strong><br>{{ os['pecas'] or 'Nenhum material extra' }}</div>
<table style="width:100%;margin-top:20px;"><tr><td style="text-align:center;border-top:1px solid #000;width:45%;">Assinatura Solicitante</td><td style="width:10%;"></td><td style="text-align:center;border-top:1px solid #000;width:45%;">Técnico Responsável</td></tr></table>
</div>
{% endmacro %}
{{ render_via('1ª VIA - CONTROLE DA EMPRESA') }}
<div class="cut">✂ DESTAQUE AQUI ✂</div>
{{ render_via('2ª VIA - CLIENTE / OPERADOR') }}
</body></html>"""

PREVENTIVAS_BODY = """
<div class="d-flex justify-content-between align-items-center mb-3">
<h5 class="fw-bold mb-0">Planos de Manutenção Preventiva</h5><a href="/nova-preventiva" class="m3-btn py-1 px-3">+ Nova Rotina</a>
</div>
<div class="m3-card p-0 overflow-hidden"><table class="table align-middle mb-0"><thead class="table-light small">
<tr><th class="ps-3">Equipamento</th><th>Ciclo</th><th>Próxima Revisão</th><th>Instruções</th><th class="text-end pe-3">Ações</th></tr></thead>
<tbody>{% for p in rotinas %}<tr>
<td class="ps-3 fw-bold">{{ p['equipamento'] }}<br><small class="text-muted">{{ p['solicitante'] }}</small></td>
<td>A cada {{ p['periodicidade_dias'] }} dias</td>
<td><span class="badge {{ 'bg-danger' if p['proxima_data'] <= hoje else 'bg-primary' }}">{{ p['proxima_data'] }}</span></td>
<td><small>{{ p['descricao'][:50] }}...</small></td>
<td class="text-end pe-3">
<a href="/gerar-preventiva-agora/{{ p['id'] }}" class="btn btn-sm btn-outline-primary py-0 px-2" title="Gerar OS Agora">Disparar</a>
<a href="/excluir-preventiva/{{ p['id'] }}" class="btn btn-sm btn-outline-danger py-0 px-2" onclick="return confirm('Excluir rotina?');">X</a>
</td></tr>{% else %}<tr><td colspan="5" class="text-center py-4 text-muted">Nenhuma preventiva programada.</td></tr>{% endfor %}</tbody></table></div>
"""

NOVA_PREVENTIVA_BODY = """
<div class="m3-card" style="max-width:540px; margin:0 auto;">
<h5 class="fw-bold mb-3">Cadastrar Manutenção Preventiva</h5>
<form method="POST">
<label class="small fw-bold">EQUIPAMENTO:</label><input type="text" name="equipamento" class="m3-input" required>
<label class="small fw-bold">SETOR / RESPONSÁVEL:</label><input type="text" name="solicitante" class="m3-input" required>
<label class="small fw-bold">PERIODICIDADE (DIAS):</label><input type="number" name="periodicidade_dias" class="m3-input" value="30" required>
<label class="small fw-bold">DATA DA 1ª REVISÃO:</label><input type="date" name="proxima_data" class="m3-input" value="{{ hoje }}" required>
<label class="small fw-bold">CHECKLIST / INSTRUÇÕES:</label><textarea name="descricao" rows="3" class="m3-input" required></textarea>
<div class="d-flex justify-content-between"><a href="/preventivas" class="m3-btn-sec">Voltar</a><button class="m3-btn">Salvar Rotina</button></div>
</form></div>"""

USUARIOS_BODY = """
<div class="m3-card mb-4" style="max-width:600px; margin:0 auto;">
<h5 class="fw-bold mb-3">Usuários do Sistema</h5>
{% if eh_admin %}
<form method="POST" class="mb-4 p-3 bg-light rounded-3 border">
<h6 class="fw-bold mb-2">Cadastrar Novo Usuário</h6>
<input type="text" name="nome" class="m3-input" placeholder="Nome Completo" required>
<div class="row g-2"><div class="col-6"><input type="text" name="usuario" class="m3-input" placeholder="Login" required></div>
<div class="col-6"><select name="nivel" class="m3-input"><option value="comum">Usuário Comum</option><option value="admin">Administrador</option></select></div></div>
<input type="password" name="senha" class="m3-input" placeholder="Senha" required>
<button class="m3-btn w-100 justify-content-center">Cadastrar Usuário</button>
</form>{% endif %}
<table class="table align-middle"><thead><tr><th>Nome</th><th>Login</th><th>Perfil</th><th class="text-end">Ações</th></tr></thead>
<tbody>{% for u in lista %}<tr>
<td class="fw-bold">{{ u['nome'] }}</td><code>{{ u['usuario'] }}</code></td>
<td><span class="badge {{ 'bg-primary' if u['nivel']=='admin' else 'bg-secondary' }}">{{ u['nivel'] }}</span></td>
<td class="text-end">{% if eh_admin and u['usuario'] != 'admin' and u['usuario'] != session.get('usuario') %}
<a href="/excluir-usuario/{{ u['id'] }}" class="btn btn-sm btn-outline-danger py-0" onclick="return confirm('Excluir?');">Excluir</a>{% endif %}</td>
</tr>{% endfor %}</tbody></table>
<a href="/" class="m3-btn-sec mt-2">Voltar ao Início</a></div>"""

CONFIGURACOES_BODY = """
<div class="m3-card" style="max-width:540px; margin:0 auto;">
<h5 class="fw-bold mb-3">Configurações da Empresa</h5>
<form method="POST">
<label class="small fw-bold">NOME DA EMPRESA:</label><input type="text" name="nome_empresa" class="m3-input" value="{{ cfg['nome_empresa'] }}" required>
<label class="small fw-bold">SUBTÍTULO / SETOR:</label><input type="text" name="subtitulo" class="m3-input" value="{{ cfg['subtitulo'] }}">
<label class="small fw-bold">CONTATO (TEL/EMAIL):</label><input type="text" name="contato" class="m3-input" value="{{ cfg['contato'] or '' }}">
<label class="small fw-bold">URL DO LOGOTIPO:</label><input type="url" name="logo_url" class="m3-input" value="{{ cfg['logo_base64'] or '' }}" placeholder="https://exemplo.com/logo.png">
<div class="d-flex justify-content-between"><a href="/" class="m3-btn-sec">Voltar</a><button class="m3-btn">Salvar Alterações</button></div>
</form></div>"""


@app.route("/login", methods=["GET", "POST"])
def login():
    cfg = obter_configuracoes()
    erro = None
    if request.method == "POST":
        u = request.form["usuario"].strip()
        s = request.form["senha"].strip()
        with get_db() as db:
            user = db.execute("SELECT * FROM usuarios WHERE usuario = ?", (u,)).fetchone()
        if user and check_password_hash(user["senha"], s):
            session["usuario"] = user["usuario"]
            session["nome"] = user["nome"]
            session["nivel"] = user["nivel"] or "comum"
            return redirect(url_for("index"))
        erro = "Usuário ou senha incorretos."
    return render_template_string(LOGIN_HTML, cfg=cfg, erro=erro)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    verificar_gerar_preventivas()
    cfg = obter_configuracoes()
    with get_db() as db:
        ordens = db.execute("SELECT * FROM ordens_servico ORDER BY id DESC").fetchall()
    return render_template_string(
        BASE_HTML.replace("<!-- CONTEUDO -->", INDEX_BODY).replace(
            "<!-- FAB -->", '<a href="/nova-os" class="m3-fab">+ Nova Requisição</a>'
        ),
        cfg=cfg,
        ordens=ordens,
        total_os=len(ordens),
        os_abertas=sum(1 for o in ordens if o["status"] == "ABERTA"),
        os_concluidas=sum(1 for o in ordens if o["status"] == "CONCLUÍDA"),
    )


@app.route("/nova-os", methods=["GET", "POST"])
def nova_os():
    cfg = obter_configuracoes()
    if request.method == "POST":
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        with get_db() as db:
            db.execute(
                "INSERT INTO ordens_servico (equipamento, solicitante, problema, data_abertura, status, foto_problema) VALUES (?, ?, ?, ?, 'ABERTA', ?)",
                (
                    request.form["equipamento"].strip(),
                    request.form["solicitante"].strip(),
                    request.form["problema"].strip(),
                    agora,
                    request.form.get("foto_problema", "").strip(),
                ),
            )
        return redirect(url_for("index"))
    return render_template_string(
        BASE_HTML.replace("<!-- CONTEUDO -->", NOVA_BODY).replace("<!-- FAB -->", ""),
        cfg=cfg,
    )


@app.route("/finalizar/<int:os_id>", methods=["GET", "POST"])
def finalizar(os_id):
    cfg = obter_configuracoes()
    with get_db() as db:
        item = db.execute("SELECT * FROM ordens_servico WHERE id = ?", (os_id,)).fetchone()
    if not item:
        return "OS não encontrada", 404
    if request.method == "POST":
        with get_db() as db:
            db.execute(
                "UPDATE ordens_servico SET operador = ?, data_finalizacao = ?, servico_executado = ?, pecas = ?, status = 'CONCLUÍDA' WHERE id = ?",
                (
                    request.form["operador"].strip(),
                    request.form["data_finalizacao"].strip(),
                    request.form["servico_executado"].strip(),
                    request.form.get("pecas", "").strip(),
                    os_id,
                ),
            )
        return redirect(url_for("recibo", os_id=os_id))
    return render_template_string(
        BASE_HTML.replace("<!-- CONTEUDO -->", FINALIZAR_BODY).replace("<!-- FAB -->", ""),
        cfg=cfg,
        os=item,
        agora=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )


@app.route("/excluir/<int:os_id>")
def excluir(os_id):
    with get_db() as db:
        db.execute("DELETE FROM ordens_servico WHERE id = ?", (os_id,))
    return redirect(url_for("index"))


@app.route("/recibo/<int:os_id>")
def recibo(os_id):
    cfg = obter_configuracoes()
    with get_db() as db:
        item = db.execute("SELECT * FROM ordens_servico WHERE id = ?", (os_id,)).fetchone()
    if not item:
        return "OS não encontrada", 404
    return render_template_string(
        RECIBO_HTML,
        cfg=cfg,
        os=item,
        texto_whatsapp=montar_texto_whatsapp(item, cfg),
    )


@app.route("/preventivas")
def preventivas():
    verificar_gerar_preventivas()
    cfg = obter_configuracoes()
    with get_db() as db:
        rotinas = db.execute("SELECT * FROM preventivas WHERE ativo = 1 ORDER BY proxima_data ASC").fetchall()
    return render_template_string(
        BASE_HTML.replace("<!-- CONTEUDO -->", PREVENTIVAS_BODY).replace("<!-- FAB -->", ""),
        cfg=cfg,
        rotinas=rotinas,
        hoje=datetime.now().strftime("%Y-%m-%d"),
    )


@app.route("/nova-preventiva", methods=["GET", "POST"])
def nova_preventiva():
    cfg = obter_configuracoes()
    hoje = datetime.now().strftime("%Y-%m-%d")
    if request.method == "POST":
        with get_db() as db:
            db.execute(
                "INSERT INTO preventivas (equipamento, solicitante, periodicidade_dias, proxima_data, descricao, ativo) VALUES (?, ?, ?, ?, ?, 1)",
                (
                    request.form["equipamento"].strip(),
                    request.form["solicitante"].strip(),
                    int(request.form.get("periodicidade_dias", 30)),
                    request.form.get("proxima_data", hoje),
                    request.form["descricao"].strip(),
                ),
            )
        return redirect(url_for("preventivas"))
    return render_template_string(
        BASE_HTML.replace("<!-- CONTEUDO -->", NOVA_PREVENTIVA_BODY).replace("<!-- FAB -->", ""),
        cfg=cfg,
        hoje=hoje,
    )


@app.route("/gerar-preventiva-agora/<int:prev_id>")
def gerar_preventiva_agora(prev_id):
    with get_db() as db:
        p = db.execute("SELECT * FROM preventivas WHERE id = ?", (prev_id,)).fetchone()
        if p:
            db.execute(
                "INSERT INTO ordens_servico (equipamento, solicitante, problema, data_abertura, status, foto_problema) VALUES (?, ?, ?, ?, 'ABERTA', '')",
                (
                    p["equipamento"],
                    f"Preventiva ({p['solicitante']})",
                    f"[ROTINA PREVENTIVA ANTECIPADA]\n" + p["descricao"],
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                ),
            )
            dt_prox = datetime.now() + timedelta(days=int(p["periodicidade_dias"]))
            db.execute(
                "UPDATE preventivas SET proxima_data = ? WHERE id = ?",
                (dt_prox.strftime("%Y-%m-%d"), prev_id),
            )
    return redirect(url_for("index"))


@app.route("/excluir-preventiva/<int:prev_id>")
def excluir_preventiva(prev_id):
    with get_db() as db:
        db.execute("DELETE FROM preventivas WHERE id = ?", (prev_id,))
    return redirect(url_for("preventivas"))


@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    cfg = obter_configuracoes()
    with get_db() as db:
        u_log = db.execute("SELECT * FROM usuarios WHERE usuario = ?", (session.get("usuario"),)).fetchone()
        eh_adm = (u_log and u_log["nivel"] == "admin") or session.get("usuario") == "admin"
        if request.method == "POST" and eh_adm:
            db.execute(
                "INSERT INTO usuarios (usuario, senha, nome, nivel) VALUES (?, ?, ?, ?)",
                (
                    request.form["usuario"].strip().lower(),
                    generate_password_hash(request.form["senha"].strip()),
                    request.form["nome"].strip(),
                    request.form.get("nivel", "comum"),
                ),
            )
        lista = db.execute("SELECT id, usuario, nome, nivel FROM usuarios ORDER BY id ASC").fetchall()
    return render_template_string(
        BASE_HTML.replace("<!-- CONTEUDO -->", USUARIOS_BODY).replace("<!-- FAB -->", ""),
        cfg=cfg,
        lista=lista,
        eh_admin=eh_adm,
    )


@app.route("/excluir-usuario/<int:user_id>")
def excluir_usuario(user_id):
    with get_db() as db:
        db.execute("DELETE FROM usuarios WHERE id = ? AND usuario != 'admin'", (user_id,))
    return redirect(url_for("usuarios"))


@app.route("/configuracoes", methods=["GET", "POST"])
def configuracoes():
    cfg = obter_configuracoes()
    if request.method == "POST":
        with get_db() as db:
            db.execute(
                "UPDATE configuracoes SET nome_empresa = ?, subtitulo = ?, contato = ?, logo_base64 = ? WHERE id = 1",
                (
                    request.form["nome_empresa"].strip(),
                    request.form.get("subtitulo", "").strip(),
                    request.form.get("contato", "").strip(),
                    request.form.get("logo_url", "").strip(),
                ),
            )
        return redirect(url_for("index"))
    return render_template_string(
        BASE_HTML.replace("<!-- CONTEUDO -->", CONFIGURACOES_BODY).replace("<!-- FAB -->", ""),
        cfg=cfg,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
