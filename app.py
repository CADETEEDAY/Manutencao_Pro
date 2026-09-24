import base64
from datetime import datetime, timedelta
import io
import os
import sqlite3
import traceback
import urllib.parse
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

try:
  import weasyprint

  TEM_WEASYPRINT = True
except ImportError:
  TEM_WEASYPRINT = False

app = Flask(__name__)
app.secret_key = "chave_mestra_manutencao_predial_segura_2026"

GLOBAL_WEBVIEW = None
GLOBAL_ACTIVITY = None
LOCAL_IP = "127.0.0.1"

# ================= CAMADA HÍBRIDA DE BANCO (POSTGRESQL / SQLITE) =================
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
  """Compatibiliza a sintaxe de parâmetros SQL entre PostgreSQL (%s) e SQLite (?)."""

  def __init__(self, conn, is_pg=False):
    self.conn = conn
    self.is_pg = is_pg

  def execute(self, sql, params=None):
    cur = self.conn.cursor()
    if self.is_pg:
      sql_formatado = sql.replace("?", "%s")
      cur.execute(sql_formatado, params or ())
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
  else:
    app_dir = os.environ.get(
        "ANDROID_PRIVATE", os.path.dirname(os.path.abspath(__file__))
    )
    db_path = os.path.join(app_dir, "manutencao.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return DBWrapper(conn, is_pg=False)


def init_db():
  with get_db() as db:
    if IS_POSTGRES:
      db.execute("""
                CREATE TABLE IF NOT EXISTS ordens_servico (
                    id SERIAL PRIMARY KEY,
                    equipamento TEXT NOT NULL,
                    solicitante TEXT NOT NULL,
                    problema TEXT NOT NULL,
                    data_abertura TEXT NOT NULL,
                    operador TEXT,
                    data_finalizacao TEXT,
                    servico_executado TEXT,
                    pecas TEXT,
                    status TEXT NOT NULL,
                    foto_problema TEXT
                )
            """)
      db.execute(
          "ALTER TABLE ordens_servico ADD COLUMN IF NOT EXISTS foto_problema"
          " TEXT;"
      )

      db.execute("""
                CREATE TABLE IF NOT EXISTS preventivas (
                    id SERIAL PRIMARY KEY,
                    equipamento TEXT NOT NULL,
                    solicitante TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    periodicidade_dias INTEGER NOT NULL,
                    proxima_data TEXT NOT NULL,
                    ultima_geracao TEXT,
                    ativo INTEGER DEFAULT 1
                )
            """)

      db.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes (
                    id INTEGER PRIMARY KEY,
                    nome_empresa TEXT,
                    subtitulo TEXT,
                    contato TEXT,
                    logo_base64 TEXT
                )
            """)
      db.execute("""
                INSERT INTO configuracoes (id, nome_empresa, subtitulo, contato, logo_base64)
                VALUES (1, 'Manutenção Predial', 'Gestão Operacional de Serviços', '', '')
                ON CONFLICT (id) DO NOTHING
            """)
      db.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    usuario TEXT UNIQUE NOT NULL,
                    senha TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    nivel TEXT DEFAULT 'admin',
                    foto_base64 TEXT
                )
            """)
      cur = db.execute("SELECT id FROM usuarios WHERE usuario = 'admin'")
      if not cur.fetchone():
        senha_hash = generate_password_hash("12345")
        db.execute(
            """
                    INSERT INTO usuarios (usuario, senha, nome, nivel, foto_base64)
                    VALUES ('admin', ?, 'Administrador Principal', 'admin', '')
                """,
            (senha_hash,),
        )
    else:
      db.execute("""
                CREATE TABLE IF NOT EXISTS ordens_servico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipamento TEXT NOT NULL,
                    solicitante TEXT NOT NULL,
                    problema TEXT NOT NULL,
                    data_abertura TEXT NOT NULL,
                    operador TEXT,
                    data_finalizacao TEXT,
                    servico_executado TEXT,
                    pecas TEXT,
                    status TEXT NOT NULL,
                    foto_problema TEXT
                )
            """)
      cur = db.execute("PRAGMA table_info(ordens_servico)")
      cols = [c[1] for c in cur.fetchall()]
      if "foto_problema" not in cols:
        db.execute("ALTER TABLE ordens_servico ADD COLUMN foto_problema TEXT")

      db.execute("""
                CREATE TABLE IF NOT EXISTS preventivas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipamento TEXT NOT NULL,
                    solicitante TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    periodicidade_dias INTEGER NOT NULL,
                    proxima_data TEXT NOT NULL,
                    ultima_geracao TEXT,
                    ativo INTEGER DEFAULT 1
                )
            """)

      db.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes (
                    id INTEGER PRIMARY KEY,
                    nome_empresa TEXT,
                    subtitulo TEXT,
                    contato TEXT,
                    logo_base64 TEXT
                )
            """)
      db.execute("""
                INSERT OR IGNORE INTO configuracoes (id, nome_empresa, subtitulo, contato, logo_base64)
                VALUES (1, 'Manutenção Predial', 'Gestão Operacional de Serviços', '', '')
            """)
      db.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    senha TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    nivel TEXT DEFAULT 'admin',
                    foto_base64 TEXT
                )
            """)
      cur_u = db.execute("PRAGMA table_info(usuarios)")
      cols_u = [c[1] for c in cur_u.fetchall()]
      if "foto_base64" not in cols_u:
        db.execute("ALTER TABLE usuarios ADD COLUMN foto_base64 TEXT")

      cur_adm = db.execute("SELECT id FROM usuarios WHERE usuario = 'admin'")
      if not cur_adm.fetchone():
        senha_hash = generate_password_hash("12345")
        db.execute(
            """
                    INSERT INTO usuarios (usuario, senha, nome, nivel, foto_base64)
                    VALUES ('admin', ?, 'Administrador Principal', 'admin', '')
                """,
            (senha_hash,),
        )


init_db()


# ================= MOTOR DE REVISÕES PREVENTIVAS AUTOMÁTICAS =================
def verificar_gerar_preventivas():
  hoje_iso = datetime.now().strftime("%Y-%m-%d")
  with get_db() as db:
    pendentes = db.execute(
        "SELECT * FROM preventivas WHERE ativo = 1 AND proxima_data <= ?",
        (hoje_iso,),
    ).fetchall()
    for p in pendentes:
      agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
      desc_os = (
          f"[REVISÃO PREVENTIVA PROGRAMADA - A CADA {p['periodicidade_dias']}"
          f" DIAS]\n{p['descricao']}"
      )
      solic = f"Preventiva ({p['solicitante']})"

      db.execute(
          """
                INSERT INTO ordens_servico (equipamento, solicitante, problema, data_abertura, status, foto_problema)
                VALUES (?, ?, ?, ?, 'ABERTA', '')
            """,
          (p["equipamento"], solic, desc_os, agora_str),
      )

      try:
        dt_base = datetime.strptime(p["proxima_data"], "%Y-%m-%d")
      except Exception:
        dt_base = datetime.now()

      dias = int(p["periodicidade_dias"]) if p["periodicidade_dias"] > 0 else 30
      while dt_base.strftime("%Y-%m-%d") <= hoje_iso:
        dt_base += timedelta(days=dias)

      db.execute(
          """
                UPDATE preventivas 
                SET proxima_data = ?, ultima_geracao = ? 
                WHERE id = ?
            """,
          (dt_base.strftime("%Y-%m-%d"), hoje_iso, p["id"]),
      )


def obter_configuracoes():
  with get_db() as db:
    cfg = db.execute("SELECT * FROM configuracoes WHERE id = 1").fetchone()
  return cfg


@app.context_processor
def injetar_usuario_logado():
  info = {
      "usuario_logado_info": None,
      "modo_nuvem": IS_POSTGRES,
  }
  if "usuario" in session:
    with get_db() as db:
      u = db.execute(
          "SELECT * FROM usuarios WHERE usuario = ?", (session["usuario"],)
      ).fetchone()
      info["usuario_logado_info"] = u
  return info


# ================= PROTEÇÃO DE ACESSO =================
@app.before_request
def checar_autenticacao():
  rotas_livres = [
      "login",
      "static",
      "recibo",
      "ping",
      "api_status_sync",
      "compartilhar_whatsapp",
  ]
  if request.endpoint not in rotas_livres and "usuario" not in session:
    return redirect(url_for("login"))


@app.route("/ping")
def ping():
  return "pong", 200


@app.errorhandler(Exception)
def tratar_erro(e):
  erro_detalhado = traceback.format_exc()
  return (
      f"<div style='padding:16px; font-family:sans-serif; color:#991b1b;'>"
      f"<h3>Ocorreu um erro no servidor:</h3>"
      f"<pre"
      f" style='background:#fee2e2;border:1px solid"
      f" #ef4444;padding:12px;border-radius:8px;font-size:11px;overflow-x:auto;'>{erro_detalhado}</pre>"
      f"<br><a href='/' style='padding:10px"
      f" 20px;background:#00639b;color:#fff;text-decoration:none;border-radius:24px;font-weight:bold;'>Voltar"
      f" ao Início</a></div>",
      500,
  )


# ================= SINCRONIZAÇÃO EM TEMPO REAL =================
@app.route("/api/status-sync")
def api_status_sync():
  verificar_gerar_preventivas()
  with get_db() as db:
    total = db.execute(
        "SELECT COUNT(*), COALESCE(MAX(id), 0) FROM ordens_servico"
    ).fetchone()
    concluidas = db.execute(
        "SELECT COUNT(*) FROM ordens_servico WHERE status = 'CONCLUÍDA'"
    ).fetchone()[0]
  return jsonify(
      {"total": total[0], "ultimo_id": total[1], "concluidas": concluidas}
  )


@app.route("/compartilhar-whatsapp/<int:os_id>")
def compartilhar_whatsapp(os_id):
  cfg = obter_configuracoes()
  with get_db() as db:
    os_item = db.execute(
        "SELECT * FROM ordens_servico WHERE id = ?", (os_id,)
    ).fetchone()

  if not os_item:
    return "Ordem de Serviço não encontrada", 404

  empresa = cfg["nome_empresa"] if cfg else "Manutenção Predial"
  mensagem = f"""*COMPROVANTE DE MANUTENÇÃO* 🛠️
-----------------------------------
🏢 *Empresa:* {empresa}
📋 *OS Nº:* #{os_item['id']:05d}
📌 *Status:* {os_item['status']}

🔧 *Equipamento/Local:* {os_item['equipamento']}
👤 *Solicitante:* {os_item['solicitante']}
👷 *Técnico Responsável:* {os_item['operador'] or 'Não atribuído'}
📅 *Data Conclusão:* {os_item['data_finalizacao'] or os_item['data_abertura']}

⚠️ *Defeito / Ocorrência:*
{os_item['problema']}

✅ *Serviço Técnico Executado:*
{os_item['servico_executado'] or 'Em andamento'}

📦 *Peças / Insumos Utilizados:*
{os_item['pecas'] or 'Nenhum material extra cadastrado'}
-----------------------------------
_Comprovante emitido via Sistema de Manutenção_"""

  texto_url = urllib.parse.quote(mensagem)
  return redirect(f"https://api.whatsapp.com/send?text={texto_url}")


# ================= TEMPLATES (MATERIAL 3 EXPRESSIVE) =================
LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Acesso ao Sistema &bull; {{ cfg['nome_empresa'] }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9ff; font-family: 'Plus Jakarta Sans', system-ui, sans-serif; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; margin: 0; }
        .login-card { background: #ffffff; border-radius: 28px; border: 1px solid #c3c7d0; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05); max-width: 400px; width: 100%; padding: 36px 30px; }
        .m3-input { background: #f2f3f9; border: 1px solid #c3c7d0; border-radius: 16px; padding: 14px 18px; font-size: 0.95rem; color: #191c20; font-weight: 500; }
        .m3-input:focus { background: #ffffff; border-color: #00639b; box-shadow: 0 0 0 3px rgba(0, 99, 155, 0.15); outline: none; }
        .btn-entrar { background-color: #00639b; color: #ffffff; border: none; border-radius: 9999px; padding: 14px 24px; font-weight: 700; font-size: 1rem; width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 4px 12px rgba(0, 99, 155, 0.2); }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="text-center mb-4">
            {% if cfg['logo_base64'] %}
                <img src="{{ cfg['logo_base64'] }}" alt="Logo" style="max-height: 55px; max-width: 160px; object-fit: contain; margin-bottom: 12px;">
            {% else %}
                <div style="width: 58px; height: 58px; background: #cee5ff; border-radius: 20px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 12px;">
                    <span class="material-symbols-rounded text-primary fs-1">shield_person</span>
                </div>
            {% endif %}
            <h4 class="fw-bold mb-1 text-dark">{{ cfg['nome_empresa'] }}</h4>
            <span class="text-muted small">Controle de Manutenção Preventiva & Corretiva</span>
        </div>
        {% if erro %}
            <div class="alert alert-danger py-2 px-3 small rounded-3 mb-3 border-0 d-flex align-items-center gap-2">
                <span class="material-symbols-rounded fs-5">warning</span>
                <span>{{ erro }}</span>
            </div>
        {% endif %}
        <form method="POST">
            <div class="mb-3">
                <label class="form-label small fw-bold text-uppercase text-secondary">Usuário:</label>
                <input type="text" name="usuario" class="form-control m3-input" placeholder="Digite seu login" required autofocus>
            </div>
            <div class="mb-4">
                <label class="form-label small fw-bold text-uppercase text-secondary">Senha:</label>
                <input type="password" name="senha" class="form-control m3-input" placeholder="Digite sua senha" required>
            </div>
            <button type="submit" class="btn btn-entrar">
                <span class="material-symbols-rounded">login</span> Acessar Sistema
            </button>
        </form>
        <div class="text-center mt-4 pt-3 border-top">
            <span class="text-muted" style="font-size: 0.78rem;">Padrão: Usuário <strong>admin</strong> | Senha <strong>12345</strong></span>
        </div>
    </div>
</body>
</html>"""

BASE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{ cfg['nome_empresa'] }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --md-sys-color-primary: #00639b;
            --md-sys-color-on-primary: #ffffff;
            --md-sys-color-primary-container: #cee5ff;
            --md-sys-color-on-primary-container: #001d33;
            --md-sys-color-secondary-container: #d9e3f8;
            --md-sys-color-on-secondary-container: #121c2b;
            --md-sys-color-tertiary-container: #e8def8;
            --md-sys-color-surface: #f8f9ff;
            --md-sys-color-surface-container-low: #f2f3f9;
            --md-sys-color-surface-container: #eceef4;
            --md-sys-color-on-surface: #191c20;
            --md-sys-color-outline-variant: #c3c7d0;
            --md-sys-color-warning-container: #ffe08b;
            --md-sys-color-success-container: #b4f3b7;
            --md-sys-color-error-container: #ffdad6;
            --md-sys-color-on-error-container: #410002;
            --md-shape-md: 16px;
            --md-shape-lg: 24px;
            --md-shape-xl: 32px;
            --md-shape-full: 9999px;
        }
        body { background-color: var(--md-sys-color-surface); color: var(--md-sys-color-on-surface); font-family: 'Plus Jakarta Sans', system-ui, sans-serif; -webkit-tap-highlight-color: transparent; margin: 0; padding-bottom: 95px; }
        .material-symbols-rounded { font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24; vertical-align: middle; line-height: 1; }
        .m3-top-app-bar { background: var(--md-sys-color-surface-container-low); padding: 10px 20px; position: sticky; top: 0; z-index: 1000; border-bottom: 1px solid var(--md-sys-color-outline-variant); }
        .m3-card { background: #ffffff; border-radius: var(--md-shape-lg); border: 1px solid var(--md-sys-color-outline-variant); box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
        .m3-card-tonal { background: var(--md-sys-color-surface-container); border-radius: var(--md-shape-lg); border: none; }
        .m3-stat-box { border-radius: var(--md-shape-lg); padding: 16px; display: flex; align-items: center; gap: 14px; }
        .m3-stat-primary { background: var(--md-sys-color-primary-container); color: var(--md-sys-color-on-primary-container); }
        .m3-stat-warning { background: var(--md-sys-color-warning-container); color: #241a00; }
        .m3-stat-success { background: var(--md-sys-color-success-container); color: #002107; }
        .m3-stat-tertiary { background: var(--md-sys-color-tertiary-container); color: #1d192b; }
        .m3-icon-badge { width: 44px; height: 44px; border-radius: var(--md-shape-md); background: rgba(255, 255, 255, 0.5); display: flex; align-items: center; justify-content: center; }
        .m3-segmented-tabs { display: flex; background: var(--md-sys-color-surface-container); padding: 4px; border-radius: var(--md-shape-full); gap: 4px; }
        .m3-tab-item { flex: 1; text-align: center; padding: 8px 16px; border-radius: var(--md-shape-full); font-weight: 700; font-size: 0.82rem; cursor: pointer; color: var(--md-sys-color-on-surface); }
        .m3-tab-item.active { background: #ffffff; color: var(--md-sys-color-primary); box-shadow: 0 2px 6px rgba(0,0,0,0.08); }
        .m3-badge-aberta { background-color: var(--md-sys-color-warning-container); color: #241a00; font-weight: 700; font-size: 0.75rem; padding: 6px 14px; border-radius: var(--md-shape-full); display: inline-flex; align-items: center; gap: 4px; }
        .m3-badge-concluida { background-color: var(--md-sys-color-success-container); color: #002107; font-weight: 700; font-size: 0.75rem; padding: 6px 14px; border-radius: var(--md-shape-full); display: inline-flex; align-items: center; gap: 4px; }
        .m3-input { background: var(--md-sys-color-surface-container-low); border: 1px solid var(--md-sys-color-outline-variant); border-radius: var(--md-shape-md); padding: 12px 16px; color: var(--md-sys-color-on-surface); font-weight: 500; }
        .m3-input:focus { background: #ffffff; border-color: var(--md-sys-color-primary); box-shadow: 0 0 0 3px rgba(0, 99, 155, 0.15); outline: none; }
        .m3-fab { position: fixed; bottom: 24px; right: 24px; background: var(--md-sys-color-primary-container); color: var(--md-sys-color-on-primary-container); border: none; border-radius: var(--md-shape-xl); padding: 16px 24px; font-size: 1rem; font-weight: 700; display: flex; align-items: center; gap: 10px; box-shadow: 0 6px 16px rgba(0,0,0,0.14); text-decoration: none; z-index: 1050; }
        .m3-btn-filled { background-color: var(--md-sys-color-primary); color: var(--md-sys-color-on-primary); border: none; border-radius: var(--md-shape-full); padding: 10px 22px; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; }
        .m3-btn-tonal { background-color: var(--md-sys-color-secondary-container); color: var(--md-sys-color-on-secondary-container); border: none; border-radius: var(--md-shape-full); padding: 8px 16px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; text-decoration: none; }
        .m3-btn-danger { background-color: var(--md-sys-color-error-container); color: var(--md-sys-color-on-error-container); border: none; border-radius: var(--md-shape-full); padding: 6px 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; text-decoration: none; }
        .avatar-3x4-top { width: 28px; height: 36px; object-fit: cover; border-radius: 6px; border: 1px solid #cbd5e1; }
    </style>
</head>
<body>
    <header class="m3-top-app-bar mb-3">
        <div class="container d-flex justify-content-between align-items-center flex-wrap gap-2">
            <a href="/" class="text-decoration-none d-flex align-items-center gap-3">
                {% if cfg['logo_base64'] %}
                    <img src="{{ cfg['logo_base64'] }}" alt="Logo" style="height: 42px; max-width: 90px; object-fit: contain; border-radius: 8px;">
                {% else %}
                    <div class="m3-icon-badge" style="background: var(--md-sys-color-primary-container); width: 42px; height: 42px;">
                        <span class="material-symbols-rounded text-primary fs-3">domain</span>
                    </div>
                {% endif %}
                <div>
                    <h5 class="fw-bold mb-0 text-dark">{{ cfg['nome_empresa'] }}</h5>
                    <span class="text-muted" style="font-size: 0.72rem; letter-spacing: 0.5px;">{{ cfg['subtitulo'] or 'GESTÃO DE MANUTENÇÃO' }}</span>
                </div>
            </a>
            <div class="d-flex align-items-center gap-2">
                {% if usuario_logado_info %}
                <div class="d-none d-md-inline-flex align-items-center gap-2 bg-white px-2 py-1 rounded-pill border">
                    {% if usuario_logado_info['foto_base64'] %}
                        <img src="{{ usuario_logado_info['foto_base64'] }}" class="avatar-3x4-top">
                    {% else %}
                        <span class="material-symbols-rounded text-secondary fs-4 ps-1">account_circle</span>
                    {% endif %}
                    <span class="small fw-bold text-dark pe-2">{{ usuario_logado_info['nome'].split()[0] }}</span>
                </div>
                {% endif %}

                <!-- BOTÃO DE MANUTENÇÕES PREVENTIVAS -->
                <a href="/preventivas" class="m3-btn-tonal" title="Manutenções Preventivas Periódicas">
                    <span class="material-symbols-rounded fs-5">event_repeat</span>
                    <span class="d-none d-sm-inline">Preventivas</span>
                </a>

                <!-- BOTÃO DE ATIVAR/SILENCIAR ÁUDIO -->
                <button type="button" id="btnSomNotif" onclick="alternarSom()" class="m3-btn-tonal py-1 px-3" title="Ativar/Desativar som de novos chamados">
                    <span class="material-symbols-rounded fs-5" id="iconeSom">notifications_active</span>
                </button>

                <a href="/usuarios" class="m3-btn-tonal" title="Gerenciar Usuários">
                    <span class="material-symbols-rounded fs-5">manage_accounts</span>
                    <span class="d-none d-sm-inline">Usuários</span>
                </a>
                <a href="/configuracoes" class="m3-btn-tonal" title="Configurações">
                    <span class="material-symbols-rounded fs-5">settings</span>
                    <span class="d-none d-sm-inline">Ajustes</span>
                </a>
                <a href="/logout" class="m3-btn-danger" title="Encerrar Sessão">
                    <span class="material-symbols-rounded fs-5">logout</span>
                </a>
            </div>
        </div>
    </header>

    <div id="bannerNovaOS" class="container mb-3" style="display: none;">
        <div class="alert alert-warning border-warning shadow-sm py-2 px-3 rounded-4 d-flex align-items-center justify-content-between">
            <div class="d-flex align-items-center gap-2">
                <span class="material-symbols-rounded fs-4 text-warning">notification_important</span>
                <strong>Atenção:</strong> Uma nova requisição de manutenção acabou de chegar!
            </div>
            <button onclick="window.location.reload()" class="btn btn-sm btn-warning fw-bold rounded-pill px-3">Atualizar Agora</button>
        </div>
    </div>

    <main class="container">
        <!-- CORPO_DA_PAGINA -->
    </main>
    <a href="/nova-os" class="m3-fab">
        <span class="material-symbols-rounded">add</span>
        <span>Nova Requisição</span>
    </a>

    <script>
    let somHabilitado = localStorage.getItem('manutencao_som') !== 'desativado';
    let audioCtx = null;

    function getAudioContext() {
        if (!audioCtx) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            audioCtx = new AudioCtx();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        return audioCtx;
    }

    document.addEventListener('click', function() { getAudioContext(); }, { once: true });
    document.addEventListener('touchstart', function() { getAudioContext(); }, { once: true });

    function atualizarIconeSom() {
        const icon = document.getElementById('iconeSom');
        if (icon) {
            icon.innerText = somHabilitado ? 'notifications_active' : 'notifications_off';
        }
    }
    atualizarIconeSom();

    function alternarSom() {
        somHabilitado = !somHabilitado;
        localStorage.setItem('manutencao_som', somHabilitado ? 'ativado' : 'desativado');
        atualizarIconeSom();
        if (somHabilitado) {
            tocarSomNotificacao();
        }
    }

    function tocarSomNotificacao() {
        if (!somHabilitado) return;
        try {
            const ctx = getAudioContext();
            const now = ctx.currentTime;

            // Tom 1 (D5 - 587Hz)
            const osc1 = ctx.createOscillator();
            const gain1 = ctx.createGain();
            osc1.type = 'sine';
            osc1.frequency.setValueAtTime(587.33, now);
            gain1.gain.setValueAtTime(0.5, now);
            gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
            osc1.connect(gain1);
            gain1.connect(ctx.destination);
            osc1.start(now);
            osc1.stop(now + 0.4);

            // Tom 2 (A5 - 880Hz)
            const osc2 = ctx.createOscillator();
            const gain2 = ctx.createGain();
            osc2.type = 'sine';
            osc2.frequency.setValueAtTime(880.00, now + 0.15);
            gain2.gain.setValueAtTime(0.6, now + 0.15);
            gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.8);
            osc2.connect(gain2);
            gain2.connect(ctx.destination);
            osc2.start(now + 0.15);
            osc2.stop(now + 0.8);

            // Vibração no Android
            if ('vibrate' in navigator) {
                navigator.vibrate([200, 100, 250]);
            }
        } catch (e) {
            console.log('Áudio:', e);
        }
    }
    </script>
</body>
</html>"""

INDEX_BODY = """
<div class="row g-3 mb-4">
    <div class="col-6 col-lg-3">
        <div class="m3-stat-box m3-stat-primary">
            <div class="m3-icon-badge"><span class="material-symbols-rounded fs-4">assignment</span></div>
            <div>
                <div class="small fw-semibold text-uppercase" style="opacity: 0.85;">Total OS</div>
                <div class="fs-4 fw-bold">{{ total_os }}</div>
            </div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="m3-stat-box m3-stat-warning">
            <div class="m3-icon-badge"><span class="material-symbols-rounded fs-4">pending_actions</span></div>
            <div>
                <div class="small fw-semibold text-uppercase" style="opacity: 0.85;">Abertas</div>
                <div class="fs-4 fw-bold">{{ os_abertas }}</div>
            </div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="m3-stat-box m3-stat-success">
            <div class="m3-icon-badge"><span class="material-symbols-rounded fs-4">task_alt</span></div>
            <div>
                <div class="small fw-semibold text-uppercase" style="opacity: 0.85;">Concluídas</div>
                <div class="fs-4 fw-bold">{{ os_concluidas }}</div>
            </div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="m3-stat-box m3-stat-tertiary">
            <div class="m3-icon-badge"><span class="material-symbols-rounded fs-4">event_repeat</span></div>
            <div>
                <div class="small fw-semibold text-uppercase" style="opacity: 0.85;">Preventivas</div>
                <div class="fs-4 fw-bold">{{ total_preventivas }}</div>
            </div>
        </div>
    </div>
</div>

<div class="m3-card p-3 mb-4">
    <div class="row align-items-center g-3">
        <div class="col-12 col-md-6">
            <div class="d-flex align-items-center gap-2 bg-light px-3 rounded-pill border">
                <span class="material-symbols-rounded text-secondary">search</span>
                <input type="text" id="filtroM3" class="form-control border-0 bg-transparent py-2" placeholder="Buscar por equipamento, técnico ou solicitante..." onkeyup="filtrarOrdens()">
            </div>
        </div>
        <div class="col-12 col-md-6">
            <div class="m3-segmented-tabs">
                <div class="m3-tab-item active" id="tab-todas" onclick="selecionarAba('todas')">Todas ({{ total_os }})</div>
                <div class="m3-tab-item" id="tab-abertas" onclick="selecionarAba('aberta')">Abertas ({{ os_abertas }})</div>
                <div class="m3-tab-item" id="tab-concluidas" onclick="selecionarAba('concluida')">Concluídas ({{ os_concluidas }})</div>
            </div>
        </div>
    </div>
</div>

<div class="m3-card overflow-hidden">
    <div class="table-responsive">
        <table class="table table-hover align-middle mb-0" id="tabelaM3">
            <thead style="background: var(--md-sys-color-surface-container-low);">
                <tr class="small text-uppercase fw-bold text-secondary">
                    <th class="ps-4 py-3">Código</th>
                    <th style="width: 60px;">Foto</th>
                    <th>Equipamento / Local</th>
                    <th>Solicitante</th>
                    <th>Operador Técnico</th>
                    <th>Abertura</th>
                    <th>Status</th>
                    <th class="text-end pe-4">Ações</th>
                </tr>
            </thead>
            <tbody>
                {% for os in ordens %}
                <tr class="linha-os" data-status="{{ os['status']|lower }}">
                    <td class="ps-4 fw-bold text-primary">#{{ "%05d" % os['id'] }}</td>
                    <td>
                        {% if os['foto_problema'] %}
                            <img src="{{ os['foto_problema'] }}" style="width: 44px; height: 44px; object-fit: cover; border-radius: 8px; border: 1px solid #cbd5e1; cursor: pointer;" onclick="window.open('{{ os['foto_problema'] }}', '_blank')" title="Ampliar foto da avaria">
                        {% else %}
                            <div style="width: 44px; height: 44px; background: #f1f5f9; border-radius: 8px; display: flex; align-items: center; justify-content: center;" title="Sem foto">
                                <span class="material-symbols-rounded text-muted fs-5">image_not_supported</span>
                            </div>
                        {% endif %}
                    </td>
                    <td class="fw-bold">{{ os['equipamento'] }}</td>
                    <td>
                        {{ os['solicitante'] }}
                        {% if 'Preventiva' in os['solicitante'] %}
                            <span class="badge bg-info text-dark rounded-pill" style="font-size:0.65rem;">ROTINA</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if os['operador'] %}
                            <span class="fw-semibold text-dark">{{ os['operador'] }}</span>
                        {% else %}
                            <a href="/assumir-os/{{ os['id'] }}" class="btn btn-sm btn-outline-primary py-0 px-2 rounded-pill small" title="Assumir esta OS">
                                <span class="material-symbols-rounded fs-6 align-middle">front_hand</span> Assumir
                            </a>
                        {% endif %}
                    </td>
                    <td class="small text-muted">{{ os['data_abertura'] }}</td>
                    <td>
                        {% if os['status'] == 'ABERTA' %}
                            <span class="m3-badge-aberta"><span class="material-symbols-rounded fs-6">schedule</span> ABERTA</span>
                        {% else %}
                            <span class="m3-badge-concluida"><span class="material-symbols-rounded fs-6">check</span> CONCLUÍDA</span>
                        {% endif %}
                    </td>
                    <td class="text-end pe-4">
                        <div class="d-inline-flex align-items-center gap-1">
                            {% if os['status'] == 'ABERTA' %}
                                <a href="/finalizar/{{ os['id'] }}" class="m3-btn-tonal py-1 px-3" title="Executar e finalizar">
                                    <span class="material-symbols-rounded fs-6">build</span> Executar
                                </a>
                            {% else %}
                                <a href="/recibo/{{ os['id'] }}" class="m3-btn-filled py-1 px-3" style="background: var(--md-sys-color-secondary-container); color: var(--md-sys-color-on-secondary-container);" title="Visualizar Recibo">
                                    <span class="material-symbols-rounded fs-6">receipt_long</span> Recibo
                                </a>
                            {% endif %}
                            <a href="/excluir/{{ os['id'] }}" class="m3-btn-danger" onclick="return confirm('Deseja realmente excluir a requisição #{{ '%05d' % os['id'] }}?');" title="Excluir requisição">
                                <span class="material-symbols-rounded fs-6">delete</span>
                            </a>
                        </div>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="8" class="text-center py-5 text-muted">
                        <span class="material-symbols-rounded fs-1 d-block mb-2 text-secondary">inbox</span>
                        Nenhuma ordem de serviço cadastrada no momento.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<script>
let abaAtiva = 'todas';
let totalAtual = {{ total_os }};
let concluidasAtual = {{ os_concluidas }};

function selecionarAba(tipo) {
    abaAtiva = tipo;
    document.querySelectorAll('.m3-tab-item').forEach(el => el.classList.remove('active'));
    if (tipo === 'todas') document.getElementById('tab-todas').classList.add('active');
    if (tipo === 'aberta') document.getElementById('tab-abertas').classList.add('active');
    if (tipo === 'concluida') document.getElementById('tab-concluidas').classList.add('active');
    filtrarOrdens();
}

function filtrarOrdens() {
    let filtroTexto = document.getElementById("filtroM3").value.toLowerCase();
    let linhas = document.querySelectorAll(".linha-os");
    linhas.forEach(linha => {
        let statusLinha = linha.getAttribute("data-status");
        let textoLinha = linha.textContent.toLowerCase();
        let passaAba = (abaAtiva === 'todas') || (statusLinha.indexOf(abaAtiva) > -1);
        let passaTexto = textoLinha.indexOf(filtroTexto) > -1;
        linha.style.display = (passaAba && passaTexto) ? "" : "none";
    });
}

// SINCRONIZAÇÃO EM TEMPO REAL: Dispara som ao receber nova chamada
setInterval(function() {
    fetch('/api/status-sync')
        .then(r => r.json())
        .then(data => {
            if (data.total > totalAtual) {
                tocarSomNotificacao();
                const banner = document.getElementById('bannerNovaOS');
                if (banner) {
                    banner.style.display = 'block';
                    banner.scrollIntoView({ behavior: 'smooth' });
                }
                totalAtual = data.total;
                setTimeout(() => { window.location.reload(); }, 2500);
            } else if (data.concluidas !== concluidasAtual) {
                window.location.reload();
            }
        }).catch(e => {});
}, 6000);
</script>
"""

# ================= TELA: NOVA REQUISIÇÃO COM CAPTURA DE FOTO =================
NOVA_BODY = """
<div class="row justify-content-center">
    <div class="col-12 col-md-8 col-lg-7">
        <div class="m3-card p-4 p-md-5">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-primary-container);"><span class="material-symbols-rounded fs-2 text-primary">add_circle</span></div>
                <div><h4 class="fw-bold mb-0">Nova Requisição</h4><span class="text-muted small">Adicione o local, descrição e foto do problema</span></div>
            </div>

            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="foto_problema" id="foto_problema" value="">

                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Equipamento ou Local:</label>
                    <input type="text" name="equipamento" class="form-control m3-input" placeholder="Ex: Bomba D'água, Elevador 01, Portão da Garagem" required autofocus>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Solicitante:</label>
                    <input type="text" name="solicitante" class="form-control m3-input" placeholder="Ex: Portaria, Gerência ou Apto 302" required>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Descrição da Ocorrência:</label>
                    <textarea name="problema" rows="3" class="form-control m3-input" placeholder="Descreva ruídos, vazamentos, avarias ou inspeção solicitada..." required></textarea>
                </div>

                <!-- SEÇÃO VISÍVEL E COMPLETA DE FOTOGRAFIA DO DEFEITO -->
                <div class="mb-4 p-3 bg-light rounded-4 border">
                    <label class="form-label small fw-bold text-uppercase text-secondary d-block">
                        <span class="material-symbols-rounded fs-5 align-middle text-primary">add_a_photo</span>
                        Foto do Defeito / Ocorrência:
                    </label>

                    <div class="text-center mb-3">
                        <div style="width: 100%; max-height: 250px; min-height: 130px; border: 2px dashed #cbd5e1; border-radius: 16px; display: flex; align-items: center; justify-content: center; overflow: hidden; background: #ffffff;">
                            <img id="previewFoto" src="" style="width: 100%; max-height: 250px; object-fit: contain; display: none;">
                            <div id="placeholderFoto" class="text-secondary p-3 text-center">
                                <span class="material-symbols-rounded fs-1 text-muted d-block mb-1">image</span>
                                <span class="small text-muted fw-bold">Nenhuma foto anexada</span>
                                <div class="text-muted" style="font-size: 0.72rem;">Tire uma foto com a câmara ou escolha da galeria</div>
                            </div>
                        </div>
                        <div id="btnRemoverFoto" class="mt-2" style="display: none;">
                            <button type="button" class="btn btn-sm btn-outline-danger py-1 px-3 rounded-pill" onclick="removerFoto()">
                                <span class="material-symbols-rounded fs-6 align-middle">delete</span> Remover Foto
                            </button>
                        </div>
                    </div>

                    <div class="d-flex gap-2">
                        <label class="m3-btn-filled flex-fill py-2 text-center" style="cursor: pointer; margin-bottom: 0;">
                            <span class="material-symbols-rounded fs-5 align-middle">photo_camera</span> 
                            <span class="align-middle fw-bold">Tirar Foto</span>
                            <input type="file" accept="image/*" capture="environment" style="display: none;" onchange="processarFoto(this)">
                        </label>
                        <label class="m3-btn-tonal flex-fill py-2 text-center" style="cursor: pointer; margin-bottom: 0;">
                            <span class="material-symbols-rounded fs-5 align-middle">photo_library</span> 
                            <span class="align-middle fw-bold">Galeria</span>
                            <input type="file" accept="image/*" style="display: none;" onchange="processarFoto(this)">
                        </label>
                    </div>
                </div>

                <div class="d-flex justify-content-between align-items-center pt-2">
                    <a href="/" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled"><span class="material-symbols-rounded">send</span> Publicar Chamado</button>
                </div>
            </form>
        </div>
    </div>
</div>

<script>
function processarFoto(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                const canvas = document.createElement('canvas');
                const maxDim = 1280;
                let w = img.width;
                let h = img.height;
                if (w > maxDim || h > maxDim) {
                    if (w > h) { h = Math.round((h * maxDim) / w); w = maxDim; }
                    else { w = Math.round((w * maxDim) / h); h = maxDim; }
                }
                canvas.width = w;
                canvas.height = h;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, w, h);
                const b64 = canvas.toDataURL('image/jpeg', 0.85);

                const prev = document.getElementById('previewFoto');
                const plc = document.getElementById('placeholderFoto');
                const btnRemover = document.getElementById('btnRemoverFoto');
                if (prev) { prev.src = b64; prev.style.display = 'block'; }
                if (plc) { plc.style.display = 'none'; }
                if (btnRemover) { btnRemover.style.display = 'block'; }
                document.getElementById('foto_problema').value = b64;
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

function removerFoto() {
    const prev = document.getElementById('previewFoto');
    const plc = document.getElementById('placeholderFoto');
    const btnRemover = document.getElementById('btnRemoverFoto');
    if (prev) { prev.src = ''; prev.style.display = 'none'; }
    if (plc) { plc.style.display = 'block'; }
    if (btnRemover) { btnRemover.style.display = 'none'; }
    document.getElementById('foto_problema').value = '';
}
</script>
"""

FINALIZAR_BODY = """
<div class="row justify-content-center">
    <div class="col-12 col-lg-8">
        <div class="m3-card p-4 p-md-5">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div class="d-flex align-items-center gap-3">
                    <div class="m3-icon-badge" style="background: var(--md-sys-color-success-container);"><span class="material-symbols-rounded fs-2 text-success">verified</span></div>
                    <div><h4 class="fw-bold mb-0">Concluir Manutenção</h4><span class="text-muted small">OS #{{ "%05d" % os['id'] }}</span></div>
                </div>
                <span class="m3-badge-aberta">Aberta em: {{ os['data_abertura'] }}</span>
            </div>

            <div class="m3-card-tonal p-3 mb-4">
                <div class="row g-3">
                    <div class="col-12 col-md-6"><span class="text-secondary small fw-bold text-uppercase">Equipamento:</span><div class="fw-bold">{{ os['equipamento'] }}</div></div>
                    <div class="col-12 col-md-6"><span class="text-secondary small fw-bold text-uppercase">Solicitante:</span><div>{{ os['solicitante'] }}</div></div>
                    <div class="col-12 mt-2 pt-2 border-top">
                        <span class="text-secondary small fw-bold text-uppercase">Problema Informado:</span>
                        <div class="text-dark">{{ os['problema'] }}</div>
                    </div>

                    {% if os['foto_problema'] %}
                    <div class="col-12 mt-2 pt-2 border-top">
                        <span class="text-secondary small fw-bold text-uppercase d-block mb-1">Foto da Ocorrência Anexada:</span>
                        <img src="{{ os['foto_problema'] }}" style="max-height: 240px; border-radius: 12px; border: 1px solid #cbd5e1; cursor: pointer;" onclick="window.open('{{ os['foto_problema'] }}', '_blank')" title="Toque para ampliar">
                    </div>
                    {% endif %}
                </div>
            </div>

            <form method="POST">
                <div class="row g-3 mb-3">
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Técnico / Operador:</label>
                        <input type="text" name="operador" class="form-control m3-input" value="{{ os['operador'] or session.get('nome', '') }}" placeholder="Nome do executor" required autofocus>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Data e Hora de Conclusão:</label>
                        <input type="text" name="data_finalizacao" class="form-control m3-input" value="{{ agora }}" required>
                    </div>
                </div>
                <div class="mb-3"><label class="form-label small fw-bold text-uppercase text-secondary">Peças & Insumos Aplicados:</label><input type="text" name="pecas" class="form-control m3-input" placeholder="Ex: 1x Relé térmico, 2x Vedações, 1L Óleo lubrificante"></div>
                <div class="mb-4"><label class="form-label small fw-bold text-uppercase text-secondary">Serviço Técnico Executado:</label><textarea name="servico_executado" rows="4" class="form-control m3-input" placeholder="Descreva os reparos feitos, medições, testes e laudo da manutenção..." required></textarea></div>
                <div class="d-flex justify-content-between align-items-center pt-2">
                    <a href="/" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled" style="background-color: #007a3d;"><span class="material-symbols-rounded">print</span> Concluir & Emitir Recibo</button>
                </div>
            </form>
        </div>
    </div>
</div>
"""

PREVENTIVAS_BODY = """
<div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
    <div>
        <h4 class="fw-bold mb-0 text-dark">Planos de Manutenção Preventiva</h4>
        <span class="text-muted small">Rotinas periódicas que geram chamados automaticamente</span>
    </div>
    <a href="/nova-preventiva" class="m3-btn-filled">
        <span class="material-symbols-rounded">add</span> Nova Rotina Preventiva
    </a>
</div>

{% if msg_sucesso %}<div class="alert alert-success py-2 px-3 small rounded-3 mb-3 border-0 d-flex align-items-center gap-2"><span class="material-symbols-rounded fs-5">check_circle</span><span>{{ msg_sucesso }}</span></div>{% endif %}

<div class="m3-card overflow-hidden">
    <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
            <thead style="background: var(--md-sys-color-surface-container-low);">
                <tr class="small text-uppercase fw-bold text-secondary">
                    <th class="ps-4 py-3">Equipamento / Ativo</th>
                    <th>Periodicidade</th>
                    <th>Próxima Revisão</th>
                    <th>Último Disparo</th>
                    <th>Checklist / Tarefa</th>
                    <th class="text-end pe-4">Ações</th>
                </tr>
            </thead>
            <tbody>
                {% for p in rotinas %}
                <tr>
                    <td class="ps-4 fw-bold text-dark">
                        {{ p['equipamento'] }}
                        <div class="text-muted small fw-normal">{{ p['solicitante'] }}</div>
                    </td>
                    <td>
                        <span class="badge bg-secondary rounded-pill py-1 px-2">
                            A cada {{ p['periodicidade_dias'] }} dias
                        </span>
                    </td>
                    <td>
                        {% if p['proxima_data'] <= hoje_iso %}
                            <span class="badge bg-danger rounded-pill py-1 px-2">Vence Hoje / Atrasada</span>
                        {% else %}
                            <span class="fw-bold text-primary">{{ p['proxima_data_formatada'] }}</span>
                        {% endif %}
                    </td>
                    <td class="small text-muted">
                        {{ p['ultima_geracao'] or 'Aguardando 1º ciclo' }}
                    </td>
                    <td>
                        <span class="small text-truncate d-inline-block" style="max-width: 220px;" title="{{ p['descricao'] }}">
                            {{ p['descricao'] }}
                        </span>
                    </td>
                    <td class="text-end pe-4">
                        <div class="d-inline-flex align-items-center gap-1">
                            <a href="/gerar-preventiva-agora/{{ p['id'] }}" class="m3-btn-tonal py-1 px-2" title="Disparar Ordem de Serviço Imediatamente">
                                <span class="material-symbols-rounded fs-6">play_arrow</span> Disparar
                            </a>
                            <a href="/editar-preventiva/{{ p['id'] }}" class="m3-btn-tonal py-1 px-2" title="Editar Rotina">
                                <span class="material-symbols-rounded fs-6">edit</span>
                            </a>
                            <a href="/excluir-preventiva/{{ p['id'] }}" class="m3-btn-danger py-1 px-2" onclick="return confirm('Deseja excluir esta rotina preventiva?');" title="Excluir Rotina">
                                <span class="material-symbols-rounded fs-6">delete</span>
                            </a>
                        </div>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="text-center py-5 text-muted">
                        <span class="material-symbols-rounded fs-1 d-block mb-2 text-secondary">event_busy</span>
                        Nenhuma manutenção preventiva cadastrada. Crie uma nova rotina para automatizar seu cronograma.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

NOVA_PREVENTIVA_BODY = """
<div class="row justify-content-center">
    <div class="col-12 col-md-8 col-lg-7">
        <div class="m3-card p-4 p-md-5">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-primary-container);"><span class="material-symbols-rounded fs-2 text-primary">event_repeat</span></div>
                <div><h4 class="fw-bold mb-0">Nova Rotina Preventiva</h4><span class="text-muted small">Crie um ciclo de revisão com abertura de chamado automático</span></div>
            </div>

            <form method="POST">
                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Equipamento ou Local:</label>
                    <input type="text" name="equipamento" class="form-control m3-input" placeholder="Ex: Bomba D'água, Grupo Gerador, Ar Condicionado" required autofocus>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Setor / Responsável:</label>
                    <input type="text" name="solicitante" class="form-control m3-input" placeholder="Ex: Manutenção Predial, Casa de Máquinas" required>
                </div>

                <div class="row g-3 mb-3">
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Periodicidade (em dias):</label>
                        <input type="number" id="inputPeriodicidade" name="periodicidade_dias" class="form-control m3-input" value="30" min="1" required>
                        <div class="d-flex flex-wrap gap-1 mt-2">
                            <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="setDias(7)">7d</button>
                            <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="setDias(15)">15d</button>
                            <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="setDias(30)">30d</button>
                            <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="setDias(90)">90d</button>
                            <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="setDias(180)">180d</button>
                            <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="setDias(365)">1 ano</button>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Data da 1ª Execução:</label>
                        <input type="date" name="proxima_data" class="form-control m3-input" value="{{ hoje_iso }}" required>
                        <small class="text-muted d-block mt-1">Data em que a OS será aberta no sistema.</small>
                    </div>
                </div>

                <div class="mb-4">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Checklist / Instruções da Revisão:</label>
                    <textarea name="descricao" rows="4" class="form-control m3-input" placeholder="Ex: 1. Limpeza de filtros; 2. Verificação de ruído e temperatura dos rolamentos..." required></textarea>
                </div>

                <div class="d-flex justify-content-between align-items-center pt-2">
                    <a href="/preventivas" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled"><span class="material-symbols-rounded">save</span> Gravar Rotina</button>
                </div>
            </form>
        </div>
    </div>
</div>

<script>
function setDias(n) {
    document.getElementById('inputPeriodicidade').value = n;
}
</script>
"""

EDITAR_PREVENTIVA_BODY = """
<div class="row justify-content-center">
    <div class="col-12 col-md-8 col-lg-7">
        <div class="m3-card p-4 p-md-5">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-secondary-container);"><span class="material-symbols-rounded fs-2 text-primary">edit_calendar</span></div>
                <div><h4 class="fw-bold mb-0">Editar Rotina Preventiva</h4><span class="text-muted small">Altere o intervalo de dias ou checklist</span></div>
            </div>

            <form method="POST">
                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Equipamento ou Local:</label>
                    <input type="text" name="equipamento" class="form-control m3-input" value="{{ p['equipamento'] }}" required>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Setor / Responsável:</label>
                    <input type="text" name="solicitante" class="form-control m3-input" value="{{ p['solicitante'] }}" required>
                </div>

                <div class="row g-3 mb-3">
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Periodicidade (em dias):</label>
                        <input type="number" id="inputPeriodicidade" name="periodicidade_dias" class="form-control m3-input" value="{{ p['periodicidade_dias'] }}" min="1" required>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Data da Próxima Revisão:</label>
                        <input type="date" name="proxima_data" class="form-control m3-input" value="{{ p['proxima_data'] }}" required>
                    </div>
                </div>

                <div class="mb-4">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Checklist / Instruções:</label>
                    <textarea name="descricao" rows="4" class="form-control m3-input" required>{{ p['descricao'] }}</textarea>
                </div>

                <div class="d-flex justify-content-between align-items-center pt-2">
                    <a href="/preventivas" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled"><span class="material-symbols-rounded">save</span> Atualizar Rotina</button>
                </div>
            </form>
        </div>
    </div>
</div>
"""

CONFIGURACOES_BODY = """
<div class="row justify-content-center">
    <div class="col-12 col-md-8 col-lg-7">
        <div class="m3-card p-4 p-md-5 mb-4">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-secondary-container);"><span class="material-symbols-rounded fs-2 text-primary">settings</span></div>
                <div><h4 class="fw-bold mb-0">Configurações do Aplicativo</h4><span class="text-muted small">Personalize a identidade da empresa e logotipo</span></div>
            </div>

            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="logo_base64_hidden" id="logo_base64_hidden" value="">

                <div class="mb-3"><label class="form-label small fw-bold text-uppercase text-secondary">Nome da Empresa / Condomínio:</label><input type="text" name="nome_empresa" class="form-control m3-input" value="{{ cfg['nome_empresa'] }}" required></div>
                <div class="mb-3"><label class="form-label small fw-bold text-uppercase text-secondary">Subtítulo / Ramo de Atuação:</label><input type="text" name="subtitulo" class="form-control m3-input" value="{{ cfg['subtitulo'] }}" placeholder="Ex: Gestão de Manutenção Predial"></div>
                <div class="mb-3"><label class="form-label small fw-bold text-uppercase text-secondary">Telefone / E-mail / Contato:</label><input type="text" name="contato" class="form-control m3-input" value="{{ cfg['contato'] }}" placeholder="Ex: Tel: (21) 99999-9999 | contato@empresa.com"></div>

                <div class="mb-4 p-3 bg-light rounded-3 border">
                    <label class="form-label small fw-bold text-uppercase text-secondary d-block">Logotipo da Empresa:</label>
                    <div class="mb-3 text-center">
                        <img id="previewLogo" src="{{ cfg['logo_base64'] or '' }}" style="max-height: 70px; max-width: 160px; object-fit: contain; {% if not cfg['logo_base64'] %}display:none;{% endif %} background:#fff; padding:6px; border:1px solid #cbd5e1; border-radius:8px;">
                        {% if cfg['logo_base64'] %}
                            <div class="mt-2"><label class="text-muted small"><input type="checkbox" name="remover_logo" value="1"> Remover logotipo atual</label></div>
                        {% endif %}
                    </div>

                    <label class="m3-btn-filled w-100 mb-2 text-center" style="cursor: pointer;">
                        <span class="material-symbols-rounded fs-5 align-middle">photo_library</span> 
                        <span class="align-middle">Escolher Imagem do Logo</span>
                        <input type="file" accept="image/*" style="display: none;" onchange="processarLogo(this)">
                    </label>

                    <label class="form-label small fw-semibold text-secondary d-block mt-3">Ou cole a URL da Imagem:</label>
                    <input type="url" name="logo_url" class="form-control m3-input" placeholder="https://exemplo.com/minha-logo.png">
                </div>

                <div class="d-flex justify-content-between align-items-center pt-2">
                    <a href="/" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled"><span class="material-symbols-rounded">save</span> Salvar Configurações</button>
                </div>
            </form>
        </div>

        <div class="m3-card p-4 border" style="background: var(--md-sys-color-surface-container-low); border-radius: var(--md-shape-lg);">
            <div class="d-flex align-items-center gap-3 mb-3">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-primary-container);"><span class="material-symbols-rounded fs-3 text-primary">terminal</span></div>
                <div><span class="text-muted small fw-bold text-uppercase" style="letter-spacing: 0.5px;">Desenvolvido por</span><h5 class="fw-bold mb-0 text-dark">Robson Cadete</h5></div>
            </div>
            <div class="d-flex flex-column gap-2 pt-1 border-top">
                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 pt-2">
                    <div class="d-flex align-items-center gap-2"><span class="material-symbols-rounded text-primary fs-5">call</span><a href="tel:21974623033" class="text-decoration-none fw-bold text-dark">(21) 97462-3033</a></div>
                    <a href="https://wa.me/5521974623033" target="_blank" class="m3-btn-tonal py-1 px-3" style="background: #25d366; color: #ffffff; font-size: 0.78rem;"><span class="material-symbols-rounded fs-6">chat</span> WhatsApp</a>
                </div>
                <div class="d-flex align-items-center gap-2 pt-1"><span class="material-symbols-rounded text-primary fs-5">mail</span><a href="mailto:robson.cadete@gmail.com" class="text-decoration-none fw-semibold text-dark">robson.cadete@gmail.com</a></div>
            </div>
        </div>
    </div>
</div>

<script>
function processarLogo(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const reader = new FileReader();
        reader.onload = function(e) {
            const prev = document.getElementById('previewLogo');
            if (prev) { prev.src = e.target.result; prev.style.display = 'inline-block'; }
            document.getElementById('logo_base64_hidden').value = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}
</script>
"""

USUARIOS_BODY = """
<div class="row justify-content-center">
    <div class="col-12 col-lg-10">
        <div class="m3-card p-4 p-md-5 mb-4">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-primary-container);"><span class="material-symbols-rounded fs-2 text-primary">person_add</span></div>
                <div><h4 class="fw-bold mb-0">Cadastrar Administrador</h4><span class="text-muted small">Adicione um novo usuário com foto 3x4 de identificação</span></div>
            </div>

            {% if msg_sucesso %}<div class="alert alert-success py-2 px-3 small rounded-3 mb-3 border-0 d-flex align-items-center gap-2"><span class="material-symbols-rounded fs-5">check_circle</span><span>{{ msg_sucesso }}</span></div>{% endif %}
            {% if msg_erro %}<div class="alert alert-danger py-2 px-3 small rounded-3 mb-3 border-0 d-flex align-items-center gap-2"><span class="material-symbols-rounded fs-5">error</span><span>{{ msg_erro }}</span></div>{% endif %}

            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="foto_base64_capturada" id="foto_base64_user" value="">

                <div class="row g-4 align-items-center mb-3">
                    <div class="col-12 col-md-4 text-center">
                        <label class="form-label small fw-bold text-uppercase text-secondary d-block">Foto 3x4:</label>
                        <div style="width: 105px; height: 140px; border: 2px dashed #c3c7d0; border-radius: 14px; margin: 0 auto; display: flex; align-items: center; justify-content: center; overflow: hidden; background: #f2f3f9;">
                            <img id="previewUser" src="" style="width: 100%; height: 100%; object-fit: cover; display: none;">
                            <div id="placeholderUser" class="text-secondary text-center">
                                <span class="material-symbols-rounded fs-1 d-block mb-1">add_a_photo</span>
                                <span style="font-size: 0.65rem; font-weight: 700;">3 x 4</span>
                            </div>
                        </div>

                        <div class="d-flex gap-2 mt-2">
                            <label class="m3-btn-filled flex-fill py-2 text-center" style="cursor: pointer; margin-bottom: 0;">
                                <span class="material-symbols-rounded fs-5 align-middle">photo_camera</span> Foto
                                <input type="file" accept="image/*" capture="user" style="display: none;" onchange="processarFotoUser(this)">
                            </label>
                            <label class="m3-btn-tonal flex-fill py-2 text-center" style="cursor: pointer; margin-bottom: 0;">
                                <span class="material-symbols-rounded fs-5 align-middle">photo_library</span> Galeria
                                <input type="file" accept="image/*" style="display: none;" onchange="processarFotoUser(this)">
                            </label>
                        </div>
                    </div>

                    <div class="col-12 col-md-8">
                        <div class="mb-3"><label class="form-label small fw-bold text-uppercase text-secondary">Nome Completo:</label><input type="text" name="nome" class="form-control m3-input" placeholder="Ex: Robson Cadete" required></div>
                        <div class="mb-3"><label class="form-label small fw-bold text-uppercase text-secondary">Login de Acesso:</label><input type="text" name="usuario" class="form-control m3-input" placeholder="Ex: robson.cadete" required></div>
                        <div class="mb-2"><label class="form-label small fw-bold text-uppercase text-secondary">Senha de Acesso:</label><input type="password" name="senha" class="form-control m3-input" placeholder="Digite uma senha segura" required></div>
                    </div>
                </div>

                <div class="d-flex justify-content-between align-items-center pt-3 border-top">
                    <a href="/" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled"><span class="material-symbols-rounded">how_to_reg</span> Gravar Administrador</button>
                </div>
            </form>
        </div>

        <div class="m3-card overflow-hidden">
            <div class="p-3 bg-light border-bottom"><h6 class="fw-bold mb-0 text-dark"><span class="material-symbols-rounded fs-5 align-middle">group</span> Administradores Ativos</h6></div>
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead style="background: var(--md-sys-color-surface-container-low);">
                        <tr class="small text-uppercase fw-bold text-secondary">
                            <th class="ps-4 py-3" style="width: 70px;">Foto</th>
                            <th>Nome</th>
                            <th>Login</th>
                            <th>Nível</th>
                            <th class="text-end pe-4">Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for u in lista_usuarios %}
                        <tr>
                            <td class="ps-4 py-2">
                                {% if u['foto_base64'] %}
                                    <img src="{{ u['foto_base64'] }}" style="width: 36px; height: 48px; object-fit: cover; border-radius: 6px; border: 1px solid #cbd5e1;">
                                {% else %}
                                    <div style="width: 36px; height: 48px; background: #e2e8f0; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span class="material-symbols-rounded text-secondary fs-5">person</span></div>
                                {% endif %}
                            </td>
                            <td class="fw-bold text-dark">{{ u['nome'] }}</td>
                            <td><code>{{ u['usuario'] }}</code></td>
                            <td><span class="badge bg-secondary">Administrador</span></td>
                            <td class="text-end pe-4">
                                <div class="d-inline-flex align-items-center gap-1">
                                    <a href="/editar-usuario/{{ u['id'] }}" class="m3-btn-tonal py-1 px-3" title="Editar dados e foto">
                                        <span class="material-symbols-rounded fs-6">edit</span> Editar
                                    </a>

                                    {% if u['usuario'] != 'admin' and u['usuario'] != usuario_logado %}
                                        <a href="/excluir-usuario/{{ u['id'] }}" class="m3-btn-danger" onclick="return confirm('Deseja excluir o usuário {{ u['usuario'] }}?');" title="Remover usuário">
                                            <span class="material-symbols-rounded fs-6">delete</span>
                                        </a>
                                    {% endif %}
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
function processarFotoUser(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const reader = new FileReader();
        reader.onload = function(e) {
            const prev = document.getElementById('previewUser');
            const plc = document.getElementById('placeholderUser');
            if (prev) { prev.src = e.target.result; prev.style.display = 'block'; }
            if (plc) { plc.style.display = 'none'; }
            document.getElementById('foto_base64_user').value = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}
</script>
"""

EDITAR_USUARIO_BODY = """
<div class="row justify-content-center">
    <div class="col-12 col-md-9 col-lg-8">
        <div class="m3-card p-4 p-md-5 mb-4">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-secondary-container);"><span class="material-symbols-rounded fs-2 text-primary">edit_square</span></div>
                <div><h4 class="fw-bold mb-0">Editar Usuário</h4><span class="text-muted small">Atualize o nome, senha ou foto 3x4</span></div>
            </div>

            {% if msg_erro %}<div class="alert alert-danger py-2 px-3 small rounded-3 mb-3 border-0 d-flex align-items-center gap-2"><span class="material-symbols-rounded fs-5">error</span><span>{{ msg_erro }}</span></div>{% endif %}

            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="foto_base64_capturada" id="foto_base64_edit" value="">

                <div class="row g-4 align-items-center mb-3">
                    <div class="col-12 col-md-4 text-center">
                        <label class="form-label small fw-bold text-uppercase text-secondary d-block">Foto 3x4:</label>
                        <div style="width: 105px; height: 140px; border: 2px dashed #c3c7d0; border-radius: 14px; margin: 0 auto; display: flex; align-items: center; justify-content: center; overflow: hidden; background: #f2f3f9;">
                            <img id="previewEdit" src="{{ u['foto_base64'] or '' }}" style="width: 100%; height: 100%; object-fit: cover; {% if not u['foto_base64'] %}display:none;{% endif %}">
                            <div id="placeholderEdit" class="text-secondary text-center" {% if u['foto_base64'] %}style="display:none;"{% endif %}>
                                <span class="material-symbols-rounded fs-1 d-block mb-1">person</span>
                                <span style="font-size: 0.65rem; font-weight: 700;">Sem Foto</span>
                            </div>
                        </div>

                        {% if u['foto_base64'] %}
                            <div class="mt-2"><label class="text-muted small"><input type="checkbox" name="remover_foto" value="1"> Remover foto</label></div>
                        {% endif %}

                        <div class="d-flex gap-2 mt-2">
                            <label class="m3-btn-filled flex-fill py-2 text-center" style="cursor: pointer; margin-bottom: 0;">
                                <span class="material-symbols-rounded fs-5 align-middle">photo_camera</span> Foto
                                <input type="file" accept="image/*" capture="user" style="display: none;" onchange="processarFotoEdit(this)">
                            </label>
                            <label class="m3-btn-tonal flex-fill py-2 text-center" style="cursor: pointer; margin-bottom: 0;">
                                <span class="material-symbols-rounded fs-5 align-middle">photo_library</span> Galeria
                                <input type="file" accept="image/*" style="display: none;" onchange="processarFotoEdit(this)">
                            </label>
                        </div>
                    </div>

                    <div class="col-12 col-md-8">
                        <div class="mb-3">
                            <label class="form-label small fw-bold text-uppercase text-secondary">Nome Completo:</label>
                            <input type="text" name="nome" class="form-control m3-input" value="{{ u['nome'] }}" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label small fw-bold text-uppercase text-secondary">Login de Acesso:</label>
                            <input type="text" name="usuario" class="form-control m3-input" value="{{ u['usuario'] }}" required>
                        </div>
                        <div class="mb-2">
                            <label class="form-label small fw-bold text-uppercase text-secondary">Nova Senha (Opcional):</label>
                            <input type="password" name="senha" class="form-control m3-input" placeholder="Deixe em branco para manter a atual">
                        </div>
                    </div>
                </div>

                <div class="d-flex justify-content-between align-items-center pt-3 border-top">
                    <a href="/usuarios" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled"><span class="material-symbols-rounded">save</span> Salvar Alterações</button>
                </div>
            </form>
        </div>
    </div>
</div>

<script>
function processarFotoEdit(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const reader = new FileReader();
        reader.onload = function(e) {
            const prev = document.getElementById('previewEdit');
            const plc = document.getElementById('placeholderEdit');
            if (prev) { prev.src = e.target.result; prev.style.display = 'block'; }
            if (plc) { plc.style.display = 'none'; }
            document.getElementById('foto_base64_edit').value = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}
</script>
"""

RECIBO_A4_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Recibo OS #{{ "%05d" % os['id'] }} - {{ cfg['nome_empresa'] }}</title>
<style>
  @page { size: A4; margin: 8mm 10mm; background-color: #ffffff; }
  *, *::before, *::after { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #0f172a; margin: 0; padding: 0; font-size: 8.5pt; line-height: 1.25; }
  .receipt-via { height: 134mm; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px 14px; background: #ffffff; }
  .header-table { width: 100%; border-bottom: 2px solid #0f172a; padding-bottom: 4px; margin-bottom: 6px; }
  .header-title { font-size: 11pt; font-weight: 800; color: #0f172a; text-transform: uppercase; }
  .badge-via { display: inline-block; background-color: #0f172a; color: #ffffff; font-size: 7.5pt; font-weight: 700; padding: 2px 8px; border-radius: 3px; text-transform: uppercase; }
  .badge-via.operador { background-color: #0284c7; }
  .os-number { font-size: 11.5pt; font-weight: 800; color: #0f172a; text-align: right; }
  .info-table { width: 100%; border-collapse: collapse; margin-bottom: 6px; }
  .info-table td { padding: 3px 4px; vertical-align: top; }
  .label { font-size: 7pt; font-weight: 700; color: #64748b; text-transform: uppercase; }
  .value { font-size: 8.5pt; color: #0f172a; }
  .box-section { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px 8px; margin-bottom: 6px; }
  .box-title { font-size: 7pt; font-weight: 700; text-transform: uppercase; color: #475569; margin-bottom: 2px; }
  .box-content { font-size: 8pt; color: #1e293b; white-space: pre-line; }
  .signatures { width: 100%; margin-top: 15px; }
  .sig-line { border-top: 1px solid #64748b; width: 80%; margin: 0 auto; padding-top: 3px; font-size: 7pt; color: #475569; text-align: center; }
  .cut-divider { height: 10mm; text-align: center; position: relative; margin: 1mm 0; }
  .cut-line { border-top: 1.5px dashed #94a3b8; position: absolute; top: 50%; width: 100%; }
  .cut-text { position: relative; background: #ffffff; display: inline-block; padding: 0 10px; font-size: 7.5pt; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }
  @media print { .no-print { display: none !important; } }
</style>
</head>
<body>

<div class="no-print" style="background:#e0f2fe; padding:12px; margin-bottom:15px; border-radius:12px; text-align:center; display:flex; align-items:center; justify-content:center; flex-wrap:wrap; gap:10px;">
    <button type="button" onclick="window.print()" style="padding:10px 22px; font-weight:bold; background:#00639b; color:#fff; border:none; border-radius:30px; font-size:10pt; cursor:pointer; display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 6px rgba(0,99,155,0.3);">
        🖨️ Imprimir / Salvar PDF
    </button>
    <a href="/compartilhar-whatsapp/{{ os['id'] }}" style="padding:10px 20px; font-weight:bold; background:#25d366; color:#fff; border-radius:30px; font-size:10pt; text-decoration:none; display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 6px rgba(37,211,102,0.35);">
        💬 Enviar no WhatsApp
    </a>
    <a href="/" style="padding:10px 16px; font-size:9pt; color:#475569; text-decoration:none; font-weight:600;">
        ⬅ Voltar ao Painel
    </a>
</div>

{% macro render_via(tipo, badge_class) %}
<div class="receipt-via">
  <table class="header-table">
    <tr>
      <td style="width: 15%; vertical-align: middle;">
        {% if cfg['logo_base64'] %}
          <img src="{{ cfg['logo_base64'] }}" style="max-height: 40px; max-width: 90px; object-fit: contain;">
        {% endif %}
      </td>
      <td style="width: 55%; vertical-align: middle;">
        <span class="badge-via {{ badge_class }}">{{ tipo }}</span>
        <div class="header-title">{{ cfg['nome_empresa'] }}</div>
        {% if cfg['contato'] %}<div style="font-size: 7pt; color: #64748b;">{{ cfg['contato'] }}</div>{% endif %}
      </td>
      <td style="width: 30%; text-align: right; vertical-align: middle;">
        <div class="os-number">OS Nº {{ "%05d" % os['id'] }}</div>
        <div style="font-size: 7.5pt; color: #64748b;">Status: <strong>{{ os['status'] }}</strong></div>
      </td>
    </tr>
  </table>

  <table class="info-table">
    <tr>
      <td style="width: 50%;"><span class="label">Equipamento / Local:</span><br><span class="value"><strong>{{ os['equipamento'] }}</strong></span></td>
      <td style="width: 25%;"><span class="label">Data Abertura:</span><br><span class="value">{{ os['data_abertura'] }}</span></td>
      <td style="width: 25%;"><span class="label">Data Conclusão:</span><br><span class="value">{{ os['data_finalizacao'] or '-' }}</span></td>
    </tr>
    <tr>
      <td><span class="label">Solicitante:</span><br><span class="value">{{ os['solicitante'] }}</span></td>
      <td colspan="2"><span class="label">Operador Técnico Responsável:</span><br><span class="value"><strong>{{ os['operador'] or 'Não atribuído' }}</strong></span></td>
    </tr>
  </table>

  <div class="box-section">
    <table style="width: 100%;">
        <tr>
            <td style="vertical-align: top;">
                <div class="box-title">Defeito Reclamado / Requisição:</div>
                <div class="box-content">{{ os['problema'] }}</div>
            </td>
            {% if os['foto_problema'] %}
            <td style="width: 75px; text-align: right; vertical-align: top;">
                <img src="{{ os['foto_problema'] }}" style="width: 65px; height: 50px; object-fit: cover; border-radius: 4px; border: 1px solid #cbd5e1;">
            </td>
            {% endif %}
        </tr>
    </table>
  </div>

  <div class="box-section"><div class="box-title">Serviço Técnico Realizado:</div><div class="box-content">{{ os['servico_executado'] or 'Em andamento' }}</div></div>
  <div class="box-section"><div class="box-title">Peças & Materiais Utilizados:</div><div class="box-content">{{ os['pecas'] or 'Nenhum material/peça extra cadastrado' }}</div></div>

  <table class="signatures">
    <tr>
      <td style="width: 50%; text-align: center;"><div class="sig-line">Assinatura do Solicitante / Visto da Empresa</div></td>
      <td style="width: 50%; text-align: center;"><div class="sig-line">{{ os['operador'] or 'Operador Técnico' }}</div></td>
    </tr>
  </table>
</div>
{% endmacro %}

{{ render_via('1ª VIA - CONTROLE DA EMPRESA', '') }}
<div class="cut-divider"><div class="cut-line"></div><span class="cut-text">✂ DESTAQUE AQUI &mdash; 1ª VIA EMPRESA / 2ª VIA OPERADOR ✂</span></div>
{{ render_via('2ª VIA - COMPROVANTE DO OPERADOR', 'operador') }}

</body>
</html>
"""

INDEX_HTML = BASE_HTML.replace("<!-- CORPO_DA_PAGINA -->", INDEX_BODY)
NOVA_OS_HTML = BASE_HTML.replace("<!-- CORPO_DA_PAGINA -->", NOVA_BODY)
FINALIZAR_OS_HTML = BASE_HTML.replace("<!-- CORPO_DA_PAGINA -->", FINALIZAR_BODY)
CONFIGURACOES_HTML = BASE_HTML.replace(
    "<!-- CORPO_DA_PAGINA -->", CONFIGURACOES_BODY
)
USUARIOS_HTML = BASE_HTML.replace("<!-- CORPO_DA_PAGINA -->", USUARIOS_BODY)
EDITAR_USUARIO_HTML = BASE_HTML.replace(
    "<!-- CORPO_DA_PAGINA -->", EDITAR_USUARIO_BODY
)
PREVENTIVAS_HTML = BASE_HTML.replace("<!-- CORPO_DA_PAGINA -->", PREVENTIVAS_BODY)
NOVA_PREVENTIVA_HTML = BASE_HTML.replace(
    "<!-- CORPO_DA_PAGINA -->", NOVA_PREVENTIVA_BODY
)
EDITAR_PREVENTIVA_HTML = BASE_HTML.replace(
    "<!-- CORPO_DA_PAGINA -->", EDITAR_PREVENTIVA_BODY
)


# ================= ROTAS DE CONTROLE & DASHBOARD =================
@app.route("/login", methods=["GET", "POST"])
def login():
  cfg = obter_configuracoes()
  erro = None
  if request.method == "POST":
    usuario = request.form["usuario"].strip()
    senha = request.form["senha"].strip()
    with get_db() as db:
      user_row = db.execute(
          "SELECT * FROM usuarios WHERE usuario = ?", (usuario,)
      ).fetchone()
    if user_row and check_password_hash(user_row["senha"], senha):
      session["usuario"] = user_row["usuario"]
      session["nome"] = user_row["nome"]
      return redirect(url_for("index"))
    else:
      erro = "Usuário ou senha inválidos. Tente novamente."
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
    ordens = db.execute(
        "SELECT * FROM ordens_servico ORDER BY id DESC"
    ).fetchall()
    total_os = len(ordens)
    os_abertas = sum(1 for o in ordens if o["status"] == "ABERTA")
    os_concluidas = sum(1 for o in ordens if o["status"] == "CONCLUÍDA")
    total_prev = db.execute(
        "SELECT COUNT(*) FROM preventivas WHERE ativo = 1"
    ).fetchone()[0]

  return render_template_string(
      INDEX_HTML,
      cfg=cfg,
      ordens=ordens,
      total_os=total_os,
      os_abertas=os_abertas,
      os_concluidas=os_concluidas,
      total_preventivas=total_prev,
  )


@app.route("/nova-os", methods=["GET", "POST"])
def nova_os():
  cfg = obter_configuracoes()
  if request.method == "POST":
    equipamento = request.form["equipamento"].strip()
    solicitante = request.form["solicitante"].strip()
    problema = request.form["problema"].strip()
    foto_problema = request.form.get("foto_problema", "").strip()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    with get_db() as db:
      db.execute(
          """
                INSERT INTO ordens_servico 
                (equipamento, solicitante, problema, data_abertura, status, foto_problema)
                VALUES (?, ?, ?, ?, 'ABERTA', ?)
            """,
          (equipamento, solicitante, problema, agora, foto_problema),
      )
    return redirect(url_for("index"))
  return render_template_string(NOVA_OS_HTML, cfg=cfg)


@app.route("/finalizar/<int:os_id>", methods=["GET", "POST"])
def finalizar(os_id):
  cfg = obter_configuracoes()
  with get_db() as db:
    os_item = db.execute(
        "SELECT * FROM ordens_servico WHERE id = ?", (os_id,)
    ).fetchone()
  if not os_item:
    return "Ordem de Serviço não encontrada", 404

  if request.method == "POST":
    operador = request.form["operador"].strip()
    data_finalizacao = request.form["data_finalizacao"].strip()
    servico_executado = request.form["servico_executado"].strip()
    pecas = request.form.get("pecas", "").strip()

    with get_db() as db:
      db.execute(
          """
                UPDATE ordens_servico 
                SET operador = ?, data_finalizacao = ?, servico_executado = ?,
                    pecas = ?, status = 'CONCLUÍDA'
                WHERE id = ?
            """,
          (operador, data_finalizacao, servico_executado, pecas, os_id),
      )
    return redirect(url_for("recibo", os_id=os_id))

  agora = datetime.now().strftime("%d/%m/%Y %H:%M")
  return render_template_string(
      FINALIZAR_OS_HTML, cfg=cfg, os=os_item, agora=agora
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
    os_item = db.execute(
        "SELECT * FROM ordens_servico WHERE id = ?", (os_id,)
    ).fetchone()
  if not os_item:
    return "Ordem de Serviço não encontrada", 404
  return render_template_string(RECIBO_A4_HTML, cfg=cfg, os=os_item)


@app.route("/recibo/<int:os_id>/pdf")
def baixar_pdf(os_id):
  return redirect(url_for("recibo", os_id=os_id))


@app.route("/assumir-os/<int:os_id>")
def assumir_os(os_id):
  nome_operador = session.get("nome", "Técnico")
  with get_db() as db:
    db.execute(
        "UPDATE ordens_servico SET operador = ? WHERE id = ? AND status ="
        " 'ABERTA'",
        (nome_operador, os_id),
    )
  return redirect(url_for("index"))


# ================= ROTAS DE PREVENTIVAS RECORRENTES =================
@app.route("/preventivas")
def preventivas():
  verificar_gerar_preventivas()
  cfg = obter_configuracoes()
  hoje_iso = datetime.now().strftime("%Y-%m-%d")

  with get_db() as db:
    rows = db.execute(
        "SELECT * FROM preventivas WHERE ativo = 1 ORDER BY proxima_data ASC"
    ).fetchall()

  rotinas_formatadas = []
  for r in rows:
    item = dict(r)
    try:
      dt = datetime.strptime(item["proxima_data"], "%Y-%m-%d")
      item["proxima_data_formatada"] = dt.strftime("%d/%m/%Y")
    except Exception:
      item["proxima_data_formatada"] = item["proxima_data"]
    rotinas_formatadas.append(item)

  return render_template_string(
      PREVENTIVAS_HTML,
      cfg=cfg,
      rotinas=rotinas_formatadas,
      hoje_iso=hoje_iso,
      msg_sucesso=request.args.get("msg"),
  )


@app.route("/nova-preventiva", methods=["GET", "POST"])
def nova_preventiva():
  cfg = obter_configuracoes()
  hoje_iso = datetime.now().strftime("%Y-%m-%d")

  if request.method == "POST":
    equipamento = request.form["equipamento"].strip()
    solicitante = request.form["solicitante"].strip()
    periodicidade = int(request.form.get("periodicidade_dias", 30))
    proxima_data = request.form.get("proxima_data", hoje_iso).strip()
    descricao = request.form["descricao"].strip()

    with get_db() as db:
      db.execute(
          """
                INSERT INTO preventivas (equipamento, solicitante, periodicidade_dias, proxima_data, descricao, ativo)
                VALUES (?, ?, ?, ?, ?, 1)
            """,
          (equipamento, solicitante, periodicidade, proxima_data, descricao),
      )

    verificar_gerar_preventivas()
    return redirect(
        url_for("preventivas", msg="Rotina preventiva criada com sucesso!")
    )

  return render_template_string(
      NOVA_PREVENTIVA_HTML, cfg=cfg, hoje_iso=hoje_iso
  )


@app.route("/editar-preventiva/<int:prev_id>", methods=["GET", "POST"])
def editar_preventiva(prev_id):
  cfg = obter_configuracoes()
  with get_db() as db:
    p = db.execute(
        "SELECT * FROM preventivas WHERE id = ?", (prev_id,)
    ).fetchone()

  if not p:
    return "Rotina preventiva não encontrada", 404

  if request.method == "POST":
    equipamento = request.form["equipamento"].strip()
    solicitante = request.form["solicitante"].strip()
    periodicidade = int(request.form.get("periodicidade_dias", 30))
    proxima_data = request.form["proxima_data"].strip()
    descricao = request.form["descricao"].strip()

    with get_db() as db:
      db.execute(
          """
                UPDATE preventivas 
                SET equipamento = ?, solicitante = ?, periodicidade_dias = ?, proxima_data = ?, descricao = ?
                WHERE id = ?
            """,
          (
              equipamento,
              solicitante,
              periodicidade,
              proxima_data,
              descricao,
              prev_id,
          ),
      )

    verificar_gerar_preventivas()
    return redirect(
        url_for("preventivas", msg="Rotina preventiva atualizada com sucesso!")
    )

  return render_template_string(EDITAR_PREVENTIVA_HTML, cfg=cfg, p=p)


@app.route("/excluir-preventiva/<int:prev_id>")
def excluir_preventiva(prev_id):
  with get_db() as db:
    db.execute("DELETE FROM preventivas WHERE id = ?", (prev_id,))
  return redirect(
      url_for("preventivas", msg="Rotina preventiva removida do cronograma.")
  )


@app.route("/gerar-preventiva-agora/<int:prev_id>")
def gerar_preventiva_agora(prev_id):
  with get_db() as db:
    p = db.execute(
        "SELECT * FROM preventivas WHERE id = ?", (prev_id,)
    ).fetchone()
    if p:
      agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
      hoje_iso = datetime.now().strftime("%Y-%m-%d")
      desc_os = (
          f"[REVISÃO PREVENTIVA ANTECIPADA - A CADA {p['periodicidade_dias']}"
          f" DIAS]\n{p['descricao']}"
      )
      solic = f"Preventiva ({p['solicitante']})"

      db.execute(
          """
                INSERT INTO ordens_servico (equipamento, solicitante, problema, data_abertura, status, foto_problema)
                VALUES (?, ?, ?, ?, 'ABERTA', '')
            """,
          (p["equipamento"], solic, desc_os, agora_str),
      )

      dt_prox = datetime.now() + timedelta(days=int(p["periodicidade_dias"]))
      db.execute(
          """
                UPDATE preventivas 
                SET proxima_data = ?, ultima_geracao = ? 
                WHERE id = ?
            """,
          (dt_prox.strftime("%Y-%m-%d"), hoje_iso, prev_id),
      )

  return redirect(
      url_for("index", msg="Chamado preventivo disparado e aberto com sucesso!")
  )


# ================= GESTÃO DE USUÁRIOS & CONFIGURAÇÕES =================
@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
  cfg = obter_configuracoes()
  msg_sucesso = None
  msg_erro = None

  if request.method == "POST":
    nome = request.form["nome"].strip()
    novo_usuario = request.form["usuario"].strip().lower()
    senha = request.form["senha"].strip()
    foto_capturada = request.form.get("foto_base64_capturada", "")

    if not nome or not novo_usuario or not senha:
      msg_erro = "Preencha todos os campos obrigatórios."
    else:
      with get_db() as db:
        existe = db.execute(
            "SELECT id FROM usuarios WHERE usuario = ?", (novo_usuario,)
        ).fetchone()
        if existe:
          msg_erro = f"O usuário '{novo_usuario}' já existe no sistema."
        else:
          db.execute(
              """
                        INSERT INTO usuarios (usuario, senha, nome, nivel, foto_base64)
                        VALUES (?, ?, ?, 'admin', ?)
                    """,
              (
                  novo_usuario,
                  generate_password_hash(senha),
                  nome,
                  foto_capturada,
              ),
          )
          msg_sucesso = f"Usuário '{nome}' cadastrado com sucesso!"

  with get_db() as db:
    lista_usuarios = db.execute(
        "SELECT id, usuario, nome, nivel, foto_base64 FROM usuarios ORDER BY id"
        " ASC"
    ).fetchall()

  return render_template_string(
      USUARIOS_HTML,
      cfg=cfg,
      lista_usuarios=lista_usuarios,
      usuario_logado=session.get("usuario"),
      msg_sucesso=msg_sucesso,
      msg_erro=msg_erro,
  )


@app.route("/editar-usuario/<int:user_id>", methods=["GET", "POST"])
def editar_usuario(user_id):
  cfg = obter_configuracoes()
  with get_db() as db:
    usuario_alvo = db.execute(
        "SELECT * FROM usuarios WHERE id = ?", (user_id,)
    ).fetchone()

  if not usuario_alvo:
    return "Usuário não encontrado", 404

  msg_erro = None

  if request.method == "POST":
    nome = request.form["nome"].strip()
    login_usuario = request.form["usuario"].strip().lower()
    nova_senha = request.form.get("senha", "").strip()
    remover_foto = request.form.get("remover_foto") == "1"
    foto_capturada = request.form.get("foto_base64_capturada", "")

    foto_base64 = "" if remover_foto else (usuario_alvo["foto_base64"] or "")
    if foto_capturada:
      foto_base64 = foto_capturada

    if not nome or not login_usuario:
      msg_erro = "Nome e Login são obrigatórios."
    else:
      with get_db() as db:
        existe = db.execute(
            "SELECT id FROM usuarios WHERE usuario = ? AND id != ?",
            (login_usuario, user_id),
        ).fetchone()
        if existe:
          msg_erro = f"O login '{login_usuario}' já pertence a outro usuário."
        else:
          if nova_senha:
            senha_hash = generate_password_hash(nova_senha)
            db.execute(
                """
                            UPDATE usuarios 
                            SET nome = ?, usuario = ?, senha = ?, foto_base64 = ?
                            WHERE id = ?
                        """,
                (nome, login_usuario, senha_hash, foto_base64, user_id),
            )
          else:
            db.execute(
                """
                            UPDATE usuarios 
                            SET nome = ?, usuario = ?, foto_base64 = ?
                            WHERE id = ?
                        """,
                (nome, login_usuario, foto_base64, user_id),
            )

          if session.get("usuario") == usuario_alvo["usuario"]:
            session["usuario"] = login_usuario
            session["nome"] = nome

          return redirect(url_for("usuarios"))

  return render_template_string(
      EDITAR_USUARIO_HTML, cfg=cfg, u=usuario_alvo, msg_erro=msg_erro
  )


@app.route("/excluir-usuario/<int:user_id>")
def excluir_usuario(user_id):
  with get_db() as db:
    user = db.execute(
        "SELECT usuario FROM usuarios WHERE id = ?", (user_id,)
    ).fetchone()
    if user and user["usuario"] != "admin" and user["usuario"] != session.get("usuario"):
      db.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
  return redirect(url_for("usuarios"))


@app.route("/configuracoes", methods=["GET", "POST"])
def configuracoes():
  cfg = obter_configuracoes()
  if request.method == "POST":
    nome_empresa = request.form["nome_empresa"].strip()
    subtitulo = request.form.get("subtitulo", "").strip()
    contato = request.form.get("contato", "").strip()
    remover_logo = request.form.get("remover_logo") == "1"
    logo_url = request.form.get("logo_url", "").strip()
    logo_base64_hidden = request.form.get("logo_base64_hidden", "")

    logo_base64 = "" if remover_logo else cfg["logo_base64"]
    if logo_base64_hidden:
      logo_base64 = logo_base64_hidden
    elif logo_url:
      logo_base64 = logo_url

    with get_db() as db:
      db.execute(
          """
                UPDATE configuracoes 
                SET nome_empresa = ?, subtitulo = ?, contato = ?, logo_base64 = ?
                WHERE id = 1
            """,
          (nome_empresa, subtitulo, contato, logo_base64),
      )
    return redirect(url_for("index"))
  return render_template_string(CONFIGURACOES_HTML, cfg=cfg)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
