import base64
from datetime import datetime
import io
import os
import sqlite3
import traceback
from flask import (
    Flask,
    flash,
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
# Chave fixa para manter o usuário logado mesmo se o app reiniciar no celular
app.secret_key = "chave_mestra_manutencao_predial_segura_2026"


# ================= CONFIGURAÇÃO DO BANCO NO ANDROID =================
def get_db_path():
  if "ANDROID_PRIVATE" in os.environ:
    base = os.environ["ANDROID_PRIVATE"]
  elif "HOME" in os.environ:
    base = os.environ["HOME"]
  else:
    base = os.path.dirname(os.path.abspath(__file__))
  os.makedirs(base, exist_ok=True)
  return os.path.join(base, "manutencao.db")


DB_PATH = get_db_path()


def get_db():
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  with get_db() as conn:
    # Tabela de ordens de serviço
    conn.execute("""
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
                status TEXT NOT NULL
            )
        """)
    # Tabela de configurações da empresa
    conn.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                id INTEGER PRIMARY KEY,
                nome_empresa TEXT,
                subtitulo TEXT,
                contato TEXT,
                logo_base64 TEXT
            )
        """)
    conn.execute("""
            INSERT OR IGNORE INTO configuracoes (id, nome_empresa, subtitulo, contato, logo_base64)
            VALUES (1, 'Manutenção Predial', 'Gestão Operacional de Serviços', '', '')
        """)

    # Tabela de usuários administradores
    conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                nome TEXT NOT NULL,
                nivel TEXT DEFAULT 'admin'
            )
        """)

    # Criação do usuário padrão caso não exista
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE usuario = 'admin'")
    if not cursor.fetchone():
      senha_hash = generate_password_hash("12345")
      conn.execute(
          """
                INSERT INTO usuarios (usuario, senha, nome, nivel)
                VALUES ('admin', ?, 'Administrador Principal', 'admin')
            """,
          (senha_hash,),
      )
    conn.commit()


init_db()


def obter_configuracoes():
  with get_db() as conn:
    cfg = conn.execute(
        "SELECT * FROM configuracoes WHERE id = 1"
    ).fetchone()
  return cfg


# ================= PROTEÇÃO DE ROTAS (LOGIN OBRIGATÓRIO) =================
@app.before_request
def checar_autenticacao():
  rotas_livres = ["login", "static"]
  if request.endpoint not in rotas_livres and "usuario" not in session:
    return redirect(url_for("login"))


@app.errorhandler(Exception)
def tratar_erro(e):
  erro_detalhado = traceback.format_exc()
  return (
      f"<div style='padding:16px; font-family:sans-serif; color:#991b1b;'>"
      f"<h3>Ocorreu um erro no aplicativo:</h3>"
      f"<pre"
      f" style='background:#fee2e2;border:1px solid"
      f" #ef4444;padding:12px;border-radius:8px;font-size:11px;overflow-x:auto;'>{erro_detalhado}</pre>"
      f"<br><a href='/' style='padding:10px"
      f" 20px;background:#00639b;color:#fff;text-decoration:none;border-radius:24px;font-weight:bold;'>Voltar"
      f" ao Início</a></div>",
      500,
  )


# ================= TEMPLATE DE LOGIN (MATERIAL 3) =================
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
        body {
            background-color: #f8f9ff;
            font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            margin: 0;
        }
        .login-card {
            background: #ffffff;
            border-radius: 28px;
            border: 1px solid #c3c7d0;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            max-width: 400px;
            width: 100%;
            padding: 36px 30px;
        }
        .m3-input {
            background: #f2f3f9;
            border: 1px solid #c3c7d0;
            border-radius: 16px;
            padding: 14px 18px;
            font-size: 0.95rem;
            color: #191c20;
            font-weight: 500;
        }
        .m3-input:focus {
            background: #ffffff;
            border-color: #00639b;
            box-shadow: 0 0 0 3px rgba(0, 99, 155, 0.15);
            outline: none;
        }
        .btn-entrar {
            background-color: #00639b;
            color: #ffffff;
            border: none;
            border-radius: 9999px;
            padding: 14px 24px;
            font-weight: 700;
            font-size: 1rem;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            box-shadow: 0 4px 12px rgba(0, 99, 155, 0.2);
            transition: opacity 0.2s;
        }
        .btn-entrar:hover { opacity: 0.93; color: #fff; }
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
            <span class="text-muted small">Controle de Acesso & Manutenção</span>
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

# ================= TEMPLATE BASE MATERIAL 3 EXPRESSIVE =================
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
            --md-sys-color-on-tertiary-container: #1d192b;
            --md-sys-color-surface: #f8f9ff;
            --md-sys-color-surface-container-low: #f2f3f9;
            --md-sys-color-surface-container: #eceef4;
            --md-sys-color-on-surface: #191c20;
            --md-sys-color-outline-variant: #c3c7d0;
            --md-sys-color-warning-container: #ffe08b;
            --md-sys-color-on-warning-container: #241a00;
            --md-sys-color-success-container: #b4f3b7;
            --md-sys-color-on-success-container: #002107;
            --md-sys-color-error-container: #ffdad6;
            --md-sys-color-on-error-container: #410002;
            --md-shape-md: 16px;
            --md-shape-lg: 24px;
            --md-shape-xl: 32px;
            --md-shape-full: 9999px;
        }

        body {
            background-color: var(--md-sys-color-surface);
            color: var(--md-sys-color-on-surface);
            font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
            -webkit-tap-highlight-color: transparent;
            margin: 0;
            padding-bottom: 95px;
        }

        .material-symbols-rounded {
            font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24;
            vertical-align: middle;
            line-height: 1;
        }

        .m3-top-app-bar {
            background: var(--md-sys-color-surface-container-low);
            padding: 12px 20px;
            position: sticky;
            top: 0;
            z-index: 1000;
            border-bottom: 1px solid var(--md-sys-color-outline-variant);
        }

        .m3-card {
            background: #ffffff;
            border-radius: var(--md-shape-lg);
            border: 1px solid var(--md-sys-color-outline-variant);
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }

        .m3-card-tonal {
            background: var(--md-sys-color-surface-container);
            border-radius: var(--md-shape-lg);
            border: none;
        }

        .m3-stat-box {
            border-radius: var(--md-shape-lg);
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .m3-stat-primary { background: var(--md-sys-color-primary-container); color: var(--md-sys-color-on-primary-container); }
        .m3-stat-warning { background: var(--md-sys-color-warning-container); color: var(--md-sys-color-on-warning-container); }
        .m3-stat-success { background: var(--md-sys-color-success-container); color: var(--md-sys-color-on-success-container); }
        .m3-stat-tertiary { background: var(--md-sys-color-tertiary-container); color: var(--md-sys-color-on-tertiary-container); }

        .m3-icon-badge {
            width: 44px;
            height: 44px;
            border-radius: var(--md-shape-md);
            background: rgba(255, 255, 255, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .m3-segmented-tabs {
            display: flex;
            background: var(--md-sys-color-surface-container);
            padding: 4px;
            border-radius: var(--md-shape-full);
            gap: 4px;
        }
        .m3-tab-item {
            flex: 1;
            text-align: center;
            padding: 8px 16px;
            border-radius: var(--md-shape-full);
            font-weight: 700;
            font-size: 0.82rem;
            cursor: pointer;
            color: var(--md-sys-color-on-surface);
            transition: all 0.2s cubic-bezier(0.2, 0, 0, 1);
            user-select: none;
        }
        .m3-tab-item.active {
            background: #ffffff;
            color: var(--md-sys-color-primary);
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        }

        .m3-badge-aberta {
            background-color: var(--md-sys-color-warning-container);
            color: var(--md-sys-color-on-warning-container);
            font-weight: 700;
            font-size: 0.75rem;
            padding: 6px 14px;
            border-radius: var(--md-shape-full);
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .m3-badge-concluida {
            background-color: var(--md-sys-color-success-container);
            color: var(--md-sys-color-on-success-container);
            font-weight: 700;
            font-size: 0.75rem;
            padding: 6px 14px;
            border-radius: var(--md-shape-full);
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .m3-input {
            background: var(--md-sys-color-surface-container-low);
            border: 1px solid var(--md-sys-color-outline-variant);
            border-radius: var(--md-shape-md);
            padding: 12px 16px;
            color: var(--md-sys-color-on-surface);
            font-weight: 500;
        }
        .m3-input:focus {
            background: #ffffff;
            border-color: var(--md-sys-color-primary);
            box-shadow: 0 0 0 3px rgba(0, 99, 155, 0.15);
            outline: none;
        }

        .m3-fab {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--md-sys-color-primary-container);
            color: var(--md-sys-color-on-primary-container);
            border: none;
            border-radius: var(--md-shape-xl);
            padding: 16px 24px;
            font-size: 1rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 6px 16px rgba(0,0,0,0.14);
            text-decoration: none;
            z-index: 1050;
        }

        .m3-btn-filled {
            background-color: var(--md-sys-color-primary);
            color: var(--md-sys-color-on-primary);
            border: none;
            border-radius: var(--md-shape-full);
            padding: 10px 24px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            text-decoration: none;
        }
        .m3-btn-tonal {
            background-color: var(--md-sys-color-secondary-container);
            color: var(--md-sys-color-on-secondary-container);
            border: none;
            border-radius: var(--md-shape-full);
            padding: 8px 16px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            text-decoration: none;
        }
        .m3-btn-danger {
            background-color: var(--md-sys-color-error-container);
            color: var(--md-sys-color-on-error-container);
            border: none;
            border-radius: var(--md-shape-full);
            padding: 6px 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <header class="m3-top-app-bar mb-4">
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
                <a href="/usuarios" class="m3-btn-tonal" title="Gerenciar Usuários">
                    <span class="material-symbols-rounded fs-5">manage_accounts</span>
                    <span class="d-none d-sm-inline">Usuários</span>
                </a>
                <a href="/configuracoes" class="m3-btn-tonal" title="Configurações do Aplicativo">
                    <span class="material-symbols-rounded fs-5">settings</span>
                    <span class="d-none d-sm-inline">Ajustes</span>
                </a>
                <a href="/logout" class="m3-btn-danger" title="Encerrar Sessão">
                    <span class="material-symbols-rounded fs-5">logout</span>
                </a>
            </div>
        </div>
    </header>

    <main class="container">
        <!-- CORPO_DA_PAGINA -->
    </main>

    <a href="/nova-os" class="m3-fab">
        <span class="material-symbols-rounded">add</span>
        <span>Nova Requisição</span>
    </a>
</body>
</html>"""

# ================= CORPOS DAS PÁGINAS =================
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
            <div class="m3-icon-badge"><span class="material-symbols-rounded fs-4">trending_up</span></div>
            <div>
                <div class="small fw-semibold text-uppercase" style="opacity: 0.85;">Conclusão</div>
                <div class="fs-4 fw-bold">
                    {% if total_os > 0 %}
                        {{ "%.0f" % ((os_concluidas / total_os) * 100) }}%
                    {% else %}
                        0%
                    {% endif %}
                </div>
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
                <div class="m3-tab-item active" id="tab-todas" onclick="selecionarAba('todas')">
                    Todas ({{ total_os }})
                </div>
                <div class="m3-tab-item" id="tab-abertas" onclick="selecionarAba('aberta')">
                    Abertas ({{ os_abertas }})
                </div>
                <div class="m3-tab-item" id="tab-concluidas" onclick="selecionarAba('concluida')">
                    Concluídas ({{ os_concluidas }})
                </div>
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
                    <td class="fw-bold">{{ os['equipamento'] }}</td>
                    <td>{{ os['solicitante'] }}</td>
                    <td>
                        {% if os['operador'] %}
                            <span class="fw-semibold">{{ os['operador'] }}</span>
                        {% else %}
                            <span class="text-muted fst-italic">Não atribuído</span>
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
                                <a href="/finalizar/{{ os['id'] }}" class="m3-btn-tonal py-1 px-3" title="Finalizar serviço">
                                    <span class="material-symbols-rounded fs-6">build</span> Fechar
                                </a>
                            {% else %}
                                <a href="/recibo/{{ os['id'] }}" class="m3-btn-filled py-1 px-3" style="background: var(--md-sys-color-secondary-container); color: var(--md-sys-color-on-secondary-container);" title="Visualizar Recibo">
                                    <span class="material-symbols-rounded fs-6">receipt_long</span> Recibo
                                </a>
                            {% endif %}
                            <a href="/excluir/{{ os['id'] }}" class="m3-btn-danger" onclick="return confirm('Deseja realmente excluir permanentemente a requisição #{{ '%05d' % os['id'] }}?');" title="Excluir requisição">
                                <span class="material-symbols-rounded fs-6">delete</span>
                            </a>
                        </div>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="7" class="text-center py-5 text-muted">
                        <span class="material-symbols-rounded fs-1 d-block mb-2 text-secondary">inbox</span>
                        Nenhuma ordem de serviço cadastrada.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<script>
let abaAtiva = 'todas';

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

        if (passaAba && passaTexto) {
            linha.style.display = "";
        } else {
            linha.style.display = "none";
        }
    });
}
</script>
"""

NOVA_BODY = """
<div class="row justify-content-center">
    <div class="col-12 col-md-8 col-lg-7">
        <div class="m3-card p-4 p-md-5">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-primary-container);">
                    <span class="material-symbols-rounded fs-2 text-primary">add_circle</span>
                </div>
                <div>
                    <h4 class="fw-bold mb-0">Nova Requisição</h4>
                    <span class="text-muted small">Abertura de chamado de manutenção</span>
                </div>
            </div>

            <form method="POST">
                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Equipamento ou Local:</label>
                    <input type="text" name="equipamento" class="form-control m3-input" placeholder="Ex: Bomba D'água, Elevador 01, Gerador" required autofocus>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Solicitante:</label>
                    <input type="text" name="solicitante" class="form-control m3-input" placeholder="Ex: Portaria, Gerência ou Morador" required>
                </div>

                <div class="mb-4">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Descrição da Ocorrência:</label>
                    <textarea name="problema" rows="4" class="form-control m3-input" placeholder="Descreva os ruídos, defeitos ou inspeção requerida..." required></textarea>
                </div>

                <div class="d-flex justify-content-between align-items-center pt-2">
                    <a href="/" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled">
                        <span class="material-symbols-rounded">send</span> Salvar Chamado
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
"""

FINALIZAR_BODY = """
<div class="row justify-content-center">
    <div class="col-12 col-lg-8">
        <div class="m3-card p-4 p-md-5">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div class="d-flex align-items-center gap-3">
                    <div class="m3-icon-badge" style="background: var(--md-sys-color-success-container);">
                        <span class="material-symbols-rounded fs-2 text-success">verified</span>
                    </div>
                    <div>
                        <h4 class="fw-bold mb-0">Concluir Manutenção</h4>
                        <span class="text-muted small">OS #{{ "%05d" % os['id'] }}</span>
                    </div>
                </div>
                <span class="m3-badge-aberta">Aberta em: {{ os['data_abertura'] }}</span>
            </div>

            <div class="m3-card-tonal p-3 mb-4">
                <div class="row g-2">
                    <div class="col-12 col-md-6">
                        <span class="text-secondary small fw-bold text-uppercase">Equipamento:</span>
                        <div class="fw-bold">{{ os['equipamento'] }}</div>
                    </div>
                    <div class="col-12 col-md-6">
                        <span class="text-secondary small fw-bold text-uppercase">Solicitante:</span>
                        <div>{{ os['solicitante'] }}</div>
                    </div>
                    <div class="col-12 mt-2 pt-2 border-top">
                        <span class="text-secondary small fw-bold text-uppercase">Problema Informado:</span>
                        <div class="text-dark">{{ os['problema'] }}</div>
                    </div>
                </div>
            </div>

            <form method="POST">
                <div class="row g-3 mb-3">
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Técnico / Operador:</label>
                        <input type="text" name="operador" class="form-control m3-input" placeholder="Nome completo do executor" required autofocus>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Data e Hora de Conclusão:</label>
                        <input type="text" name="data_finalizacao" class="form-control m3-input" value="{{ agora }}" required>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Peças & Insumos Aplicados:</label>
                    <input type="text" name="pecas" class="form-control m3-input" placeholder="Ex: 1x Relé térmico, 2x Vedações, 1L Óleo lubrificante">
                </div>

                <div class="mb-4">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Serviço Técnico Executado:</label>
                    <textarea name="servico_executado" rows="4" class="form-control m3-input" placeholder="Descreva os reparos feitos, medições, testes e laudo da manutenção..." required></textarea>
                </div>

                <div class="d-flex justify-content-between align-items-center pt-2">
                    <a href="/" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled" style="background-color: #007a3d;">
                        <span class="material-symbols-rounded">print</span> Finalizar e Emitir Recibo
                    </button>
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
                <div class="m3-icon-badge" style="background: var(--md-sys-color-secondary-container);">
                    <span class="material-symbols-rounded fs-2 text-primary">settings</span>
                </div>
                <div>
                    <h4 class="fw-bold mb-0">Configurações do Aplicativo</h4>
                    <span class="text-muted small">Personalize a identidade da empresa e logotipo</span>
                </div>
            </div>

            <form method="POST" enctype="multipart/form-data">
                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Nome da Empresa / Condomínio:</label>
                    <input type="text" name="nome_empresa" class="form-control m3-input" value="{{ cfg['nome_empresa'] }}" required>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Subtítulo / Ramo de Atuação:</label>
                    <input type="text" name="subtitulo" class="form-control m3-input" value="{{ cfg['subtitulo'] }}" placeholder="Ex: Gestão de Manutenção Predial">
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Telefone / E-mail / Contato:</label>
                    <input type="text" name="contato" class="form-control m3-input" value="{{ cfg['contato'] }}" placeholder="Ex: Tel: (21) 99999-9999 | contato@empresa.com">
                </div>

                <div class="mb-4 p-3 bg-light rounded-3 border">
                    <label class="form-label small fw-bold text-uppercase text-secondary d-block">Logotipo da Empresa:</label>
                    {% if cfg['logo_base64'] %}
                        <div class="mb-2 d-flex align-items-center gap-3">
                            <img src="{{ cfg['logo_base64'] }}" style="max-height: 60px; max-width: 140px; object-fit: contain; background:#fff; padding:4px; border:1px solid #ccc; border-radius:6px;">
                            <label class="text-muted small"><input type="checkbox" name="remover_logo" value="1"> Remover logotipo atual</label>
                        </div>
                    {% endif %}
                    <input type="file" name="logo" class="form-control m3-input" accept="image/png, image/jpeg, image/webp">
                    <small class="text-muted d-block mt-1">A imagem selecionada aparecerá na barra superior e nos recibos impressos de 2 vias.</small>
                </div>

                <div class="d-flex justify-content-between align-items-center pt-2">
                    <a href="/" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled">
                        <span class="material-symbols-rounded">save</span> Salvar Configurações
                    </button>
                </div>
            </form>
        </div>

        <div class="m3-card p-4 border" style="background: var(--md-sys-color-surface-container-low); border-radius: var(--md-shape-lg);">
            <div class="d-flex align-items-center gap-3 mb-3">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-primary-container);">
                    <span class="material-symbols-rounded fs-3 text-primary">terminal</span>
                </div>
                <div>
                    <span class="text-muted small fw-bold text-uppercase" style="letter-spacing: 0.5px;">Desenvolvido por</span>
                    <h5 class="fw-bold mb-0 text-dark">Robson Cadete</h5>
                </div>
            </div>

            <div class="d-flex flex-column gap-2 pt-1 border-top">
                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 pt-2">
                    <div class="d-flex align-items-center gap-2">
                        <span class="material-symbols-rounded text-primary fs-5">call</span>
                        <a href="tel:21974623033" class="text-decoration-none fw-bold text-dark">(21) 97462-3033</a>
                    </div>
                    <a href="https://wa.me/5521974623033" target="_blank" class="m3-btn-tonal py-1 px-3" style="background: #25d366; color: #ffffff; font-size: 0.78rem;">
                        <span class="material-symbols-rounded fs-6">chat</span> WhatsApp
                    </a>
                </div>

                <div class="d-flex align-items-center gap-2 pt-1">
                    <span class="material-symbols-rounded text-primary fs-5">mail</span>
                    <a href="mailto:robson.cadete@gmail.com" class="text-decoration-none fw-semibold text-dark">robson.cadete@gmail.com</a>
                </div>
            </div>
        </div>
    </div>
</div>
"""

# ================= TELA DE GERENCIAMENTO DE USUÁRIOS =================
USUARIOS_BODY = """
<div class="row justify-content-center">
    <div class="col-12 col-md-9 col-lg-8">
        <!-- FORMULÁRIO DE NOVO USUÁRIO -->
        <div class="m3-card p-4 p-md-5 mb-4">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-primary-container);">
                    <span class="material-symbols-rounded fs-2 text-primary">person_add</span>
                </div>
                <div>
                    <h4 class="fw-bold mb-0">Cadastrar Administrador</h4>
                    <span class="text-muted small">Adicione um novo usuário para gerenciar o aplicativo</span>
                </div>
            </div>

            {% if msg_sucesso %}
                <div class="alert alert-success py-2 px-3 small rounded-3 mb-3 border-0 d-flex align-items-center gap-2">
                    <span class="material-symbols-rounded fs-5">check_circle</span>
                    <span>{{ msg_sucesso }}</span>
                </div>
            {% endif %}
            {% if msg_erro %}
                <div class="alert alert-danger py-2 px-3 small rounded-3 mb-3 border-0 d-flex align-items-center gap-2">
                    <span class="material-symbols-rounded fs-5">error</span>
                    <span>{{ msg_erro }}</span>
                </div>
            {% endif %}

            <form method="POST">
                <div class="row g-3 mb-3">
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Nome Completo:</label>
                        <input type="text" name="nome" class="form-control m3-input" placeholder="Ex: Carlos Silva" required>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Login de Acesso (Usuário):</label>
                        <input type="text" name="usuario" class="form-control m3-input" placeholder="Ex: carlossilva" required>
                    </div>
                </div>

                <div class="mb-4">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Senha de Acesso:</label>
                    <input type="password" name="senha" class="form-control m3-input" placeholder="Digite uma senha segura" required>
                </div>

                <div class="d-flex justify-content-between align-items-center pt-2">
                    <a href="/" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled">
                        <span class="material-symbols-rounded">how_to_reg</span> Salvar Administrador
                    </button>
                </div>
            </form>
        </div>

        <!-- LISTA DE USUÁRIOS ATIVOS -->
        <div class="m3-card overflow-hidden">
            <div class="p-3 bg-light border-bottom">
                <h6 class="fw-bold mb-0 text-dark"><span class="material-symbols-rounded fs-5 align-middle">group</span> Administradores Cadastrados</h6>
            </div>
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead style="background: var(--md-sys-color-surface-container-low);">
                        <tr class="small text-uppercase fw-bold text-secondary">
                            <th class="ps-4 py-3">Nome</th>
                            <th>Login</th>
                            <th>Nível</th>
                            <th class="text-end pe-4">Ação</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for u in lista_usuarios %}
                        <tr>
                            <td class="ps-4 fw-bold text-dark">{{ u['nome'] }}</td>
                            <td><code>{{ u['usuario'] }}</code></td>
                            <td><span class="badge bg-secondary">Administrador</span></td>
                            <td class="text-end pe-4">
                                {% if u['usuario'] != 'admin' and u['usuario'] != usuario_logado %}
                                    <a href="/excluir-usuario/{{ u['id'] }}" class="m3-btn-danger" onclick="return confirm('Deseja excluir o usuário {{ u['usuario'] }}?');" title="Remover usuário">
                                        <span class="material-symbols-rounded fs-6">delete</span>
                                    </a>
                                {% else %}
                                    <span class="text-muted small fst-italic">Padrão / Logado</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
"""

INDEX_HTML = BASE_HTML.replace("<!-- CORPO_DA_PAGINA -->", INDEX_BODY)
NOVA_OS_HTML = BASE_HTML.replace("<!-- CORPO_DA_PAGINA -->", NOVA_BODY)
FINALIZAR_OS_HTML = BASE_HTML.replace("<!-- CORPO_DA_PAGINA -->", FINALIZAR_BODY)
CONFIGURACOES_HTML = BASE_HTML.replace(
    "<!-- CORPO_DA_PAGINA -->", CONFIGURACOES_BODY
)
USUARIOS_HTML = BASE_HTML.replace("<!-- CORPO_DA_PAGINA -->", USUARIOS_BODY)

# ================= RECIBO TÉCNICO A4 (2 VIAS) =================
RECIBO_A4_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Recibo OS #{{ "%05d" % os['id'] }} - {{ cfg['nome_empresa'] }}</title>
<style>
  @page { size: A4; margin: 8mm 10mm; background-color: #ffffff; }
  *, *::before, *::after { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #0f172a; margin: 0; padding: 0; font-size: 8.5pt; line-height: 1.25;
  }
  .receipt-via {
    height: 134mm; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px 14px; background: #ffffff;
  }
  .header-table { width: 100%; border-bottom: 2px solid #0f172a; padding-bottom: 4px; margin-bottom: 6px; }
  .header-title { font-size: 11pt; font-weight: 800; color: #0f172a; text-transform: uppercase; }
  .badge-via {
    display: inline-block; background-color: #0f172a; color: #ffffff; font-size: 7.5pt; font-weight: 700;
    padding: 2px 8px; border-radius: 3px; text-transform: uppercase;
  }
  .badge-via.operador { background-color: #0284c7; }
  .os-number { font-size: 11.5pt; font-weight: 800; color: #0f172a; text-align: right; }
  .info-table { width: 100%; border-collapse: collapse; margin-bottom: 6px; }
  .info-table td { padding: 3px 4px; vertical-align: top; }
  .label { font-size: 7pt; font-weight: 700; color: #64748b; text-transform: uppercase; }
  .value { font-size: 8.5pt; color: #0f172a; }
  .box-section {
    background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px 8px; margin-bottom: 6px;
  }
  .box-title { font-size: 7pt; font-weight: 700; text-transform: uppercase; color: #475569; margin-bottom: 2px; }
  .box-content { font-size: 8pt; color: #1e293b; white-space: pre-line; }
  .signatures { width: 100%; margin-top: 15px; }
  .sig-line {
    border-top: 1px solid #64748b; width: 80%; margin: 0 auto; padding-top: 3px; font-size: 7pt;
    color: #475569; text-align: center;
  }
  .cut-divider { height: 10mm; text-align: center; position: relative; margin: 1mm 0; }
  .cut-line { border-top: 1.5px dashed #94a3b8; position: absolute; top: 50%; width: 100%; }
  .cut-text {
    position: relative; background: #ffffff; display: inline-block; padding: 0 10px; font-size: 7.5pt;
    font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 1px;
  }
  @media print { .no-print { display: none !important; } }
</style>
</head>
<body>

<div class="no-print" style="background:#e0f2fe; padding:12px; margin-bottom:15px; border-radius:8px; text-align:center;">
    <button onclick="window.print()" style="padding:8px 20px; font-weight:bold; cursor:pointer; background:#00639b; color:#fff; border:none; border-radius:30px; font-size:10pt;">
        Imprimir Recibo (2 Vias) / Salvar PDF
    </button>
    <a href="/" style="margin-left:15px; font-size:9pt; color:#475569; text-decoration:none; font-weight:600;">Voltar ao Painel</a>
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
      <td style="width: 50%;">
        <span class="label">Equipamento / Local:</span><br>
        <span class="value"><strong>{{ os['equipamento'] }}</strong></span>
      </td>
      <td style="width: 25%;">
        <span class="label">Data Abertura:</span><br>
        <span class="value">{{ os['data_abertura'] }}</span>
      </td>
      <td style="width: 25%;">
        <span class="label">Data Conclusão:</span><br>
        <span class="value">{{ os['data_finalizacao'] or '-' }}</span>
      </td>
    </tr>
    <tr>
      <td>
        <span class="label">Solicitante:</span><br>
        <span class="value">{{ os['solicitante'] }}</span>
      </td>
      <td colspan="2">
        <span class="label">Operador Técnico Responsável:</span><br>
        <span class="value"><strong>{{ os['operador'] or 'Não atribuído' }}</strong></span>
      </td>
    </tr>
  </table>

  <div class="box-section">
    <div class="box-title">Defeito Reclamado / Requisição:</div>
    <div class="box-content">{{ os['problema'] }}</div>
  </div>

  <div class="box-section">
    <div class="box-title">Serviço Técnico Realizado:</div>
    <div class="box-content">{{ os['servico_executado'] or 'Em andamento' }}</div>
  </div>

  <div class="box-section">
    <div class="box-title">Peças & Materiais Utilizados:</div>
    <div class="box-content">{{ os['pecas'] or 'Nenhum material/peça extra cadastrado' }}</div>
  </div>

  <table class="signatures">
    <tr>
      <td style="width: 50%; text-align: center;">
        <div class="sig-line">Assinatura do Solicitante / Visto da Empresa</div>
      </td>
      <td style="width: 50%; text-align: center;">
        <div class="sig-line">{{ os['operador'] or 'Operador Técnico' }}</div>
      </td>
    </tr>
  </table>
</div>
{% endmacro %}

{{ render_via('1ª VIA - CONTROLE DA EMPRESA', '') }}

<div class="cut-divider">
  <div class="cut-line"></div>
  <span class="cut-text">✂ DESTAQUE AQUI &mdash; 1ª VIA EMPRESA / 2ª VIA OPERADOR ✂</span>
</div>

{{ render_via('2ª VIA - COMPROVANTE DO OPERADOR', 'operador') }}

</body>
</html>
"""


# ================= ROTAS DE AUTENTICAÇÃO =================
@app.route("/login", methods=["GET", "POST"])
def login():
  cfg = obter_configuracoes()
  erro = None
  if request.method == "POST":
    usuario = request.form["usuario"].strip()
    senha = request.form["senha"].strip()

    with get_db() as conn:
      user_row = conn.execute(
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


# ================= ROTAS DE USUÁRIOS =================
@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
  cfg = obter_configuracoes()
  msg_sucesso = None
  msg_erro = None

  if request.method == "POST":
    nome = request.form["nome"].strip()
    novo_usuario = request.form["usuario"].strip().lower()
    senha = request.form["senha"].strip()

    if not nome or not novo_usuario or not senha:
      msg_erro = "Preencha todos os campos do novo usuário."
    else:
      with get_db() as conn:
        existe = conn.execute(
            "SELECT id FROM usuarios WHERE usuario = ?", (novo_usuario,)
        ).fetchone()
        if existe:
          msg_erro = f"O usuário '{novo_usuario}' já existe no sistema."
        else:
          conn.execute(
              """
                        INSERT INTO usuarios (usuario, senha, nome, nivel)
                        VALUES (?, ?, ?, 'admin')
                    """,
              (novo_usuario, generate_password_hash(senha), nome),
          )
          conn.commit()
          msg_sucesso = (
              f"Administrador '{nome}' ({novo_usuario}) cadastrado com"
              " sucesso!"
          )

  with get_db() as conn:
    lista_usuarios = conn.execute(
        "SELECT id, usuario, nome, nivel FROM usuarios ORDER BY id ASC"
    ).fetchall()

  return render_template_string(
      USUARIOS_HTML,
      cfg=cfg,
      lista_usuarios=lista_usuarios,
      usuario_logado=session.get("usuario"),
      msg_sucesso=msg_sucesso,
      msg_erro=msg_erro,
  )


@app.route("/excluir-usuario/<int:user_id>")
def excluir_usuario(user_id):
  with get_db() as conn:
    user = conn.execute(
        "SELECT usuario FROM usuarios WHERE id = ?", (user_id,)
    ).fetchone()
    if user and user["usuario"] != "admin" and user["usuario"] != session.get("usuario"):
      conn.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
      conn.commit()
  return redirect(url_for("usuarios"))


# ================= ROTAS PRINCIPAIS =================
@app.route("/")
def index():
  cfg = obter_configuracoes()
  with get_db() as conn:
    ordens = conn.execute(
        "SELECT * FROM ordens_servico ORDER BY id DESC"
    ).fetchall()

    total_os = len(ordens)
    os_abertas = sum(1 for o in ordens if o["status"] == "ABERTA")
    os_concluidas = sum(1 for o in ordens if o["status"] == "CONCLUÍDA")

  return render_template_string(
      INDEX_HTML,
      cfg=cfg,
      ordens=ordens,
      total_os=total_os,
      os_abertas=os_abertas,
      os_concluidas=os_concluidas,
  )


@app.route("/configuracoes", methods=["GET", "POST"])
def configuracoes():
  cfg = obter_configuracoes()
  if request.method == "POST":
    nome_empresa = request.form["nome_empresa"].strip()
    subtitulo = request.form.get("subtitulo", "").strip()
    contato = request.form.get("contato", "").strip()
    remover_logo = request.form.get("remover_logo") == "1"

    logo_base64 = "" if remover_logo else cfg["logo_base64"]

    arquivo_logo = request.files.get("logo")
    if arquivo_logo and arquivo_logo.filename != "":
      bytes_imagem = arquivo_logo.read()
      b64_str = base64.b64encode(bytes_imagem).decode("utf-8")
      mimetype = arquivo_logo.content_type or "image/png"
      logo_base64 = f"data:{mimetype};base64,{b64_str}"

    with get_db() as conn:
      conn.execute(
          """
                UPDATE configuracoes 
                SET nome_empresa = ?, subtitulo = ?, contato = ?, logo_base64 = ?
                WHERE id = 1
            """,
          (nome_empresa, subtitulo, contato, logo_base64),
      )
      conn.commit()
    return redirect(url_for("index"))

  return render_template_string(CONFIGURACOES_HTML, cfg=cfg)


@app.route("/nova-os", methods=["GET", "POST"])
def nova_os():
  cfg = obter_configuracoes()
  if request.method == "POST":
    equipamento = request.form["equipamento"].strip()
    solicitante = request.form["solicitante"].strip()
    problema = request.form["problema"].strip()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    with get_db() as conn:
      conn.execute(
          """
                INSERT INTO ordens_servico 
                (equipamento, solicitante, problema, data_abertura, status)
                VALUES (?, ?, ?, ?, 'ABERTA')
            """,
          (equipamento, solicitante, problema, agora),
      )
      conn.commit()
    return redirect(url_for("index"))

  return render_template_string(NOVA_OS_HTML, cfg=cfg)


@app.route("/finalizar/<int:os_id>", methods=["GET", "POST"])
def finalizar(os_id):
  cfg = obter_configuracoes()
  with get_db() as conn:
    os_item = conn.execute(
        "SELECT * FROM ordens_servico WHERE id = ?", (os_id,)
    ).fetchone()

  if not os_item:
    return "Ordem de Serviço não encontrada", 404

  if request.method == "POST":
    operador = request.form["operador"].strip()
    data_finalizacao = request.form["data_finalizacao"].strip()
    servico_executado = request.form["servico_executado"].strip()
    pecas = request.form.get("pecas", "").strip()

    with get_db() as conn:
      conn.execute(
          """
                UPDATE ordens_servico 
                SET operador = ?, data_finalizacao = ?, servico_executado = ?,
                    pecas = ?, status = 'CONCLUÍDA'
                WHERE id = ?
            """,
          (operador, data_finalizacao, servico_executado, pecas, os_id),
      )
      conn.commit()
    return redirect(url_for("recibo", os_id=os_id))

  agora = datetime.now().strftime("%d/%m/%Y %H:%M")
  return render_template_string(
      FINALIZAR_OS_HTML, cfg=cfg, os=os_item, agora=agora
  )


@app.route("/excluir/<int:os_id>")
def excluir(os_id):
  with get_db() as conn:
    conn.execute("DELETE FROM ordens_servico WHERE id = ?", (os_id,))
    conn.commit()
  return redirect(url_for("index"))


@app.route("/recibo/<int:os_id>")
def recibo(os_id):
  cfg = obter_configuracoes()
  with get_db() as conn:
    os_item = conn.execute(
        "SELECT * FROM ordens_servico WHERE id = ?", (os_id,)
    ).fetchone()

  if not os_item:
    return "Ordem de Serviço não encontrada", 404

  return render_template_string(RECIBO_A4_HTML, cfg=cfg, os=os_item)


@app.route("/recibo/<int:os_id>/pdf")
def baixar_pdf(os_id):
  cfg = obter_configuracoes()
  with get_db() as conn:
    os_item = conn.execute(
        "SELECT * FROM ordens_servico WHERE id = ?", (os_id,)
    ).fetchone()

  if not os_item:
    return "Ordem de Serviço não encontrada", 404

  html_renderizado = render_template_string(RECIBO_A4_HTML, cfg=cfg, os=os_item)

  if TEM_WEASYPRINT:
    pdf_bytes = weasyprint.HTML(string=html_renderizado).write_pdf()
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Recibo_OS_{os_id:05d}.pdf",
    )
  else:
    return render_template_string(RECIBO_A4_HTML, cfg=cfg, os=os_item)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
