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
                );
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
                );
            """)
      db.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes (
                    id INTEGER PRIMARY KEY,
                    nome_empresa TEXT,
                    subtitulo TEXT,
                    contato TEXT,
                    logo_base64 TEXT
                );
            """)
      db.execute("""
                INSERT INTO configuracoes (id, nome_empresa, subtitulo, contato, logo_base64)
                VALUES (1, 'Manutenção Predial', 'Gestão Operacional de Serviços', '', '')
                ON CONFLICT (id) DO NOTHING;
            """)
      db.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    usuario TEXT UNIQUE NOT NULL,
                    senha TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    nivel TEXT DEFAULT 'comum',
                    foto_base64 TEXT
                );
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
      db.execute(
          "UPDATE usuarios SET nivel = 'comum' WHERE usuario != 'admin';"
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
                );
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
                );
            """)
      db.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes (
                    id INTEGER PRIMARY KEY,
                    nome_empresa TEXT,
                    subtitulo TEXT,
                    contato TEXT,
                    logo_base64 TEXT
                );
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
                    nivel TEXT DEFAULT 'comum',
                    foto_base64 TEXT
                );
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
      db.execute(
          "UPDATE usuarios SET nivel = 'comum' WHERE usuario != 'admin';"
      )


init_db()


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


def montar_texto_whatsapp(os_item, cfg):
  empresa = cfg["nome_empresa"] if cfg else "Manutenção Predial"
  msg = f"""*COMPROVANTE DE MANUTENÇÃO* 🛠️
