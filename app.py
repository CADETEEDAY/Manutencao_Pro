import os
import sqlite3
import traceback
import urllib.parse
from datetime import datetime, timedelta
from flask import (
    Flask,
    request,
    session,
    redirect,
    url_for,
    render_template_string,
    jsonify,
)
from werkzeug.security import generate_password_hash, check_password_hash

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
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
        return DBWrapper(conn, is_pg=True)
    app_dir = os.environ.get("ANDROID_PRIVATE", os.path.dirname(os.path.abspath(__file__)))
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
                db.execute("INSERT INTO usuarios (usuario, senha, nome, nivel) VALUES ('admin', ?, 'Administrador Principal', 'admin')", (generate_password_hash("12345"),))
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
                db.execute("INSERT INTO usuarios (usuario, senha, nome, nivel) VALUES ('admin', ?, 'Administrador Principal', 'admin')", (generate_password_hash("12345"),))

init_db()


def verificar_gerar_preventivas():
    hoje = datetime.now().strftime("%Y-%m-%d")
    with get_db() as db:
        for p in db.execute("SELECT * FROM preventivas WHERE ativo = 1 AND proxima_data <= ?", (hoje,)).fetchall():
            agora = datetime.now().strftime("%d/%m/%Y %H:%M")
            db.execute(
                "INSERT INTO ordens_servico (equipamento, solicitante, problema, data_abertura, status, foto_problema) VALUES (?, ?, ?, ?, 'ABERTA', '')",
                (p["equipamento"], f"Preventiva ({p['solicitante']})", f"[ROTINA PREVENTIVA - A CADA {p['periodicidade_dias']} DIAS]\n" + p["descricao"], agora)
            )
            try:
                dt_base = datetime.strptime(p["proxima_data"], "%Y-%m-%d")
            except Exception:
                dt_base = datetime.now()
            dias = int(p["periodicidade_dias"]) if p["periodicidade_dias"] > 0 else 30
            while dt_base.strftime("%Y-%m-%d") <= hoje:
                dt_base += timedelta(days=dias)
            db.execute("UPDATE preventivas SET proxima_data = ?, ultima_geracao = ? WHERE id = ?", (dt_base.strftime("%Y-%m-%d"), hoje, p["id"]))


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
    info = {"usuario_logado_info": None, "modo_nuvem": IS_POSTGRES, "ultimo_id_sistema": 0, "eh_admin": False}
    if "usuario" in session:
        with get_db() as db:
            u = db.execute("SELECT * FROM usuarios WHERE usuario = ?", (session["usuario"],)).fetchone()
            info["usuario_logado_info"] = u
            if u:
                info["eh_admin"] = (u["usuario"] == "admin" or u["nivel"] == "admin")
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
                    "status": r["status"]
                }
    return jsonify({
        "total": tot,
        "ultimo_id": ult_id,
        "concluidas": concl,
        "ultimo_chamado": ult_chamado
    })


@app.route("/compartilhar-whatsapp/")
def compartilhar_whatsapp(os_id):
    return redirect(url_for("recibo", os_id=os_id) + "?share=1")


BASE_HTML = """


    
    {{ cfg['nome_empresa'] }}
