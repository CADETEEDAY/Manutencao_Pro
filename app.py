import os, sqlite3, traceback
from datetime import datetime, timedelta
from flask import Flask, request, session, redirect, url_for, render_template_string, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "chave_mestra_manutencao_2026"

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_PG = bool(DATABASE_URL)
if IS_PG and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

class DB:
    def __init__(self):
        if IS_PG:
            import psycopg2, psycopg2.extras
            self.conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
        else:
            p = os.path.join(os.environ.get("ANDROID_PRIVATE", os.path.dirname(__file__)), "manutencao.db")
            self.conn = sqlite3.connect(p)
            self.conn.row_factory = sqlite3.Row
    def ex(self, sql, params=()):
        c = self.conn.cursor()
        c.execute(sql.replace("?", "%s") if IS_PG else sql, params)
        return c
    def commit(self): self.conn.commit()
    def close(self): self.conn.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.commit(); self.close()

def init_db():
    with DB() as db:
        auto = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
        db.ex("CREATE TABLE IF NOT EXISTS ordens_servico (id " + auto + ", equipamento TEXT, solicitante TEXT, problema TEXT, data_abertura TEXT, operador TEXT, data_finalizacao TEXT, servico_executado TEXT, pecas TEXT, status TEXT, foto_problema TEXT);")
        db.ex("CREATE TABLE IF NOT EXISTS preventivas (id " + auto + ", equipamento TEXT, solicitante TEXT, descricao TEXT, periodicidade_dias INTEGER, proxima_data TEXT, ultima_geracao TEXT, ativo INTEGER DEFAULT 1);")
        db.ex("CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, nome_empresa TEXT, subtitulo TEXT, contato TEXT, logo_base64 TEXT);")
        db.ex("CREATE TABLE IF NOT EXISTS usuarios (id " + auto + ", usuario TEXT UNIQUE, senha TEXT, nome TEXT, nivel TEXT DEFAULT 'comum', foto_base64 TEXT);")
        if IS_PG:
            db.ex("INSERT INTO configuracoes (id, nome_empresa, subtitulo) VALUES (1, 'Manutenção Predial', 'Gestão Operacional') ON CONFLICT (id) DO NOTHING;")
        else:
            db.ex("INSERT OR IGNORE INTO configuracoes (id, nome_empresa, subtitulo) VALUES (1, 'Manutenção Predial', 'Gestão Operacional');")
            cols = [c[1] for c in db.ex("PRAGMA table_info(ordens_servico)").fetchall()]
            if "foto_problema" not in cols: db.ex("ALTER TABLE ordens_servico ADD COLUMN foto_problema TEXT")
        if not db.ex("SELECT id FROM usuarios WHERE usuario='admin'").fetchone():
            db.ex("INSERT INTO usuarios (usuario, senha, nome, nivel) VALUES ('admin', ?, 'Administrador', 'admin');", (generate_password_hash("12345"),))

init_db()

def verificar_preventivas():
    hoje = datetime.now().strftime("%Y-%m-%d")
    with DB() as db:
        for p in db.ex("SELECT * FROM preventivas WHERE ativo=1 AND proxima_data<=?", (hoje,)).fetchall():
            agora = datetime.now().strftime("%d/%m/%Y %H:%M")
            desc = "[PREVENTIVA PROGRAMADA]\n" + str(p['descricao'])
            db.ex("INSERT INTO ordens_servico (equipamento, solicitante, problema, data_abertura, status, foto_problema) VALUES (?, ?, ?, ?, 'ABERTA', '')",
                  (p['equipamento'], "Preventiva (" + str(p['solicitante']) + ")", desc, agora))
            try: dt = datetime.strptime(p['proxima_data'], "%Y-%m-%d")
            except: dt = datetime.now()
            dias = int(p['periodicidade_dias']) if p['periodicidade_dias'] > 0 else 30
            while dt.strftime("%Y-%m-%d") <= hoje: dt += timedelta(days=dias)
            db.ex("UPDATE preventivas SET proxima_data=?, ultima_geracao=? WHERE id=?", (dt.strftime("%Y-%m-%d"), hoje, p['id']))

def obter_cfg():
    with DB() as db:
        return db.ex("SELECT * FROM configuracoes WHERE id=1").fetchone()

def texto_zap(os_item, cfg):
    emp = cfg['nome_empresa'] if cfg else 'Manutenção Predial'
    return "\n".join([
        "*COMPROVANTE DE MANUTENÇÃO*",
        "Empresa: " + str(emp),
        "OS: #" + ("%05d" % os_item['id']) + " | Status: " + str(os_item['status']),
        "Equipamento: " + str(os_item['equipamento']),
        "Solicitante: " + str(os_item['solicitante']),
        "Técnico: " + str(os_item['operador'] or 'Pendente'),
        "Conclusão: " + str(os_item['data_finalizacao'] or os_item['data_abertura']),
        "Defeito: " + str(os_item['problema']),
        "Serviço: " + str(os_item['servico_executado'] or 'Em andamento'),
        "Peças: " + str(os_item['pecas'] or 'Nenhum material extra')
    ])

@app.before_request
def auth_check():
    livres = ['login', 'static', 'recibo', 'ping', 'api_status_sync']
    if request.endpoint not in livres and 'usuario' not in session:
        return redirect(url_for('login'))

@app.route('/ping')
def ping(): return "pong", 200

@app.route('/api/status-sync')
def api_status_sync():
    verificar_preventivas()
    with DB() as db:
        tot, ult_id = db.ex("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM ordens_servico").fetchone()
        concl = db.ex("SELECT COUNT(*) FROM ordens_servico WHERE status='CONCLUÍDA'").fetchone()[0]
        chamado = None
        if ult_id > 0:
            r = db.ex("SELECT id, equipamento, solicitante, status FROM ordens_servico WHERE id=?", (ult_id,)).fetchone()
            if r: chamado = {'id': r['id'], 'equipamento': r['equipamento'], 'solicitante': r['solicitante']}
    return jsonify({'total': tot, 'ultimo_id': ult_id, 'concluidas': concl, 'ultimo_chamado': chamado})

T_BASE = """
{{ cfg['nome_empresa'] }}
