from datetime import datetime
import io
import os
import sqlite3
from flask import Flask, redirect, render_template_string, request, send_file, url_for

try:
  import weasyprint

  TEM_WEASYPRINT = True
except ImportError:
  TEM_WEASYPRINT = False

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "manutencao.db")


def get_db():
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  with get_db() as conn:
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
                custo_pecas REAL DEFAULT 0.0,
                horas_trabalhadas REAL DEFAULT 0.0,
                valor_hora REAL DEFAULT 0.0,
                custo_total REAL DEFAULT 0.0,
                status TEXT NOT NULL
            )
        """)
    conn.commit()


init_db()

# ================= DESIGN SYSTEM MATERIAL 3 EXPRESSIVE =================
BASE_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Manutenção &bull; Material 3 Expressive</title>
    <!-- Google Fonts & Material Symbols -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            /* Tokens de Cor M3 Expressive (Tonal Palettes) */
            --md-sys-color-primary: #00639b;
            --md-sys-color-on-primary: #ffffff;
            --md-sys-color-primary-container: #cee5ff;
            --md-sys-color-on-primary-container: #001d33;

            --md-sys-color-secondary-container: #d9e3f8;
            --md-sys-color-on-secondary-container: #121c2b;

            --md-sys-color-tertiary-container: #f7d8ff;
            --md-sys-color-on-tertiary-container: #2b0042;

            --md-sys-color-surface: #f8f9ff;
            --md-sys-color-surface-container-low: #f2f3f9;
            --md-sys-color-surface-container: #eceef4;
            --md-sys-color-surface-container-high: #e6e8ee;
            --md-sys-color-on-surface: #191c20;
            --md-sys-color-on-surface-variant: #43474e;
            --md-sys-color-outline: #73777f;
            --md-sys-color-outline-variant: #c3c7d0;

            --md-sys-color-warning-container: #ffe08b;
            --md-sys-color-on-warning-container: #241a00;

            --md-sys-color-success-container: #b4f3b7;
            --md-sys-color-on-success-container: #002107;

            /* Expressive Shapes */
            --md-shape-xs: 8px;
            --md-shape-sm: 12px;
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
            padding-bottom: 90px;
        }

        .material-symbols-rounded {
            font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24;
            vertical-align: middle;
            line-height: 1;
        }

        /* M3 Top App Bar */
        .m3-top-app-bar {
            background: var(--md-sys-color-surface-container-low);
            padding: 14px 20px;
            position: sticky;
            top: 0;
            z-index: 1000;
            border-bottom: 1px solid var(--md-sys-color-outline-variant);
        }

        /* M3 Cards & Containers */
        .m3-card {
            background: #ffffff;
            border-radius: var(--md-shape-lg);
            border: 1px solid var(--md-sys-color-outline-variant);
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            transition: transform 0.2s cubic-bezier(0.2, 0, 0, 1), box-shadow 0.2s cubic-bezier(0.2, 0, 0, 1);
        }

        .m3-card-tonal {
            background: var(--md-sys-color-surface-container);
            border-radius: var(--md-shape-lg);
            border: none;
        }

        /* M3 Tonal Stat Cards */
        .m3-stat-box {
            border-radius: var(--md-shape-lg);
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .m3-stat-primary {
            background: var(--md-sys-color-primary-container);
            color: var(--md-sys-color-on-primary-container);
        }
        .m3-stat-warning {
            background: var(--md-sys-color-warning-container);
            color: var(--md-sys-color-on-warning-container);
        }
        .m3-stat-success {
            background: var(--md-sys-color-success-container);
            color: var(--md-sys-color-on-success-container);
        }
        .m3-stat-tertiary {
            background: var(--md-sys-color-tertiary-container);
            color: var(--md-sys-color-on-tertiary-container);
        }

        .m3-icon-badge {
            width: 48px;
            height: 48px;
            border-radius: var(--md-shape-md);
            background: rgba(255, 255, 255, 0.45);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* M3 Badges */
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

        /* M3 Inputs */
        .m3-input {
            background: var(--md-sys-color-surface-container-low);
            border: 1px solid var(--md-sys-color-outline-variant);
            border-radius: var(--md-shape-md);
            padding: 12px 16px;
            color: var(--md-sys-color-on-surface);
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .m3-input:focus {
            background: #ffffff;
            border-color: var(--md-sys-color-primary);
            box-shadow: 0 0 0 3px rgba(0, 99, 155, 0.15);
            outline: none;
        }

        /* M3 Extended FAB (Floating Action Button) */
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
            gap: 12px;
            box-shadow: 0 6px 16px rgba(0,0,0,0.14);
            text-decoration: none;
            z-index: 1050;
            transition: all 0.2s cubic-bezier(0.2, 0, 0, 1);
        }
        .m3-fab:hover {
            transform: scale(1.04);
            box-shadow: 0 8px 24px rgba(0,0,0,0.2);
            color: var(--md-sys-color-on-primary-container);
        }

        /* Botões M3 */
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
            transition: opacity 0.2s;
        }
        .m3-btn-filled:hover {
            opacity: 0.92;
            color: #ffffff;
        }

        .m3-btn-tonal {
            background-color: var(--md-sys-color-secondary-container);
            color: var(--md-sys-color-on-secondary-container);
            border: none;
            border-radius: var(--md-shape-full);
            padding: 8px 18px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            text-decoration: none;
        }
        .m3-btn-tonal:hover {
            filter: brightness(0.96);
            color: var(--md-sys-color-on-secondary-container);
        }
    </style>
</head>
<body>
    <!-- Top Bar -->
    <header class="m3-top-app-bar mb-4">
        <div class="container d-flex justify-content-between align-items-center">
            <a href="/" class="text-decoration-none d-flex align-items-center gap-2">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-primary-container); width: 42px; height: 42px;">
                    <span class="material-symbols-rounded text-primary">handyman</span>
                </div>
                <div>
                    <h5 class="fw-bold mb-0 text-dark">Manutenção</h5>
                    <span class="text-muted" style="font-size: 0.72rem; letter-spacing: 0.5px;">MATERIAL 3 EXPRESSIVE</span>
                </div>
            </a>
            <div class="d-none d-md-flex align-items-center gap-2">
                <a href="/" class="m3-btn-tonal">
                    <span class="material-symbols-rounded">dashboard</span> Painel
                </a>
            </div>
        </div>
    </header>

    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <!-- Extended FAB para Abertura Rápida -->
    <a href="/nova-os" class="m3-fab">
        <span class="material-symbols-rounded">add</span>
        <span>Nova Requisição</span>
    </a>
</body>
</html>
"""

# ================= DASHBOARD M3 =================
INDEX_HTML = (
    BASE_HTML
    + """
{% block content %}
<!-- INDICADORES TONAL CARDS M3 -->
<div class="row g-3 mb-4">
    <div class="col-6 col-lg-3">
        <div class="m3-stat-box m3-stat-primary">
            <div class="m3-icon-badge">
                <span class="material-symbols-rounded fs-3">assignment</span>
            </div>
            <div>
                <div class="small fw-semibold text-uppercase" style="letter-spacing: 0.5px; opacity: 0.85;">Total OS</div>
                <div class="fs-3 fw-bold">{{ total_os }}</div>
            </div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="m3-stat-box m3-stat-warning">
            <div class="m3-icon-badge">
                <span class="material-symbols-rounded fs-3">pending_actions</span>
            </div>
            <div>
                <div class="small fw-semibold text-uppercase" style="letter-spacing: 0.5px; opacity: 0.85;">Abertas</div>
                <div class="fs-3 fw-bold">{{ os_abertas }}</div>
            </div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="m3-stat-box m3-stat-success">
            <div class="m3-icon-badge">
                <span class="material-symbols-rounded fs-3">task_alt</span>
            </div>
            <div>
                <div class="small fw-semibold text-uppercase" style="letter-spacing: 0.5px; opacity: 0.85;">Concluídas</div>
                <div class="fs-3 fw-bold">{{ os_concluidas }}</div>
            </div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="m3-stat-box m3-stat-tertiary">
            <div class="m3-icon-badge">
                <span class="material-symbols-rounded fs-3">payments</span>
            </div>
            <div>
                <div class="small fw-semibold text-uppercase" style="letter-spacing: 0.5px; opacity: 0.85;">Faturamento</div>
                <div class="fs-4 fw-bold">R$ {{ "%.2f" % faturamento_total }}</div>
            </div>
        </div>
    </div>
</div>

<!-- BARRA DE PESQUISA COM M3 SEARCH FIELD -->
<div class="m3-card p-3 mb-4">
    <div class="row align-items-center g-3">
        <div class="col-12 col-md-6">
            <div class="d-flex align-items-center gap-2 bg-light px-3 rounded-pill border">
                <span class="material-symbols-rounded text-secondary">search</span>
                <input type="text" id="filtroM3" class="form-control border-0 bg-transparent py-2" placeholder="Buscar por máquina, operador ou solicitante..." onkeyup="filtrarOrdens()">
            </div>
        </div>
        <div class="col-12 col-md-6 text-md-end text-muted small fw-semibold">
            <span class="material-symbols-rounded fs-6 align-middle">tune</span> Filtro dinâmico em tempo real
        </div>
    </div>
</div>

<!-- LISTAGEM DE ORDENS EM CARDS / TABELA EXPRESSIVA -->
<div class="m3-card overflow-hidden">
    <div class="table-responsive">
        <table class="table table-hover align-middle mb-0" id="tabelaM3">
            <thead style="background: var(--md-sys-color-surface-container-low);">
                <tr class="small text-uppercase fw-bold text-secondary">
                    <th class="ps-4 py-3">Código</th>
                    <th>Equipamento / Área</th>
                    <th>Solicitante</th>
                    <th>Operador</th>
                    <th>Abertura</th>
                    <th>Custo Total</th>
                    <th>Status</th>
                    <th class="text-end pe-4">Ação</th>
                </tr>
            </thead>
            <tbody>
                {% for os in ordens %}
                <tr>
                    <td class="ps-4 fw-bold text-primary">#{{ "%05d" % os['id'] }}</td>
                    <td class="fw-bold">{{ os['equipamento'] }}</td>
                    <td>{{ os['solicitante'] }}</td>
                    <td>
                        {% if os['operador'] %}
                            <span class="fw-semibold">{{ os['operador'] }}</span>
                        {% else %}
                            <span class="text-muted fst-italic">Aguardando</span>
                        {% endif %}
                    </td>
                    <td class="small text-muted">{{ os['data_abertura'] }}</td>
                    <td class="fw-bold">
                        {% if os['custo_total'] %}
                            R$ {{ "%.2f" % os['custo_total'] }}
                        {% else %}
                            <span class="text-muted">-</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if os['status'] == 'ABERTA' %}
                            <span class="m3-badge-aberta">
                                <span class="material-symbols-rounded fs-6">schedule</span> ABERTA
                            </span>
                        {% else %}
                            <span class="m3-badge-concluida">
                                <span class="material-symbols-rounded fs-6">check</span> CONCLUÍDA
                            </span>
                        {% endif %}
                    </td>
                    <td class="text-end pe-4">
                        {% if os['status'] == 'ABERTA' %}
                            <a href="/finalizar/{{ os['id'] }}" class="m3-btn-tonal py-1 px-3">
                                <span class="material-symbols-rounded fs-6">build</span> Fechar
                            </a>
                        {% else %}
                            <a href="/recibo/{{ os['id'] }}" class="m3-btn-filled py-1 px-3" style="background: var(--md-sys-color-secondary-container); color: var(--md-sys-color-on-secondary-container);" title="Visualizar Recibo">
                                <span class="material-symbols-rounded fs-6">receipt_long</span> Recibo
                            </a>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="8" class="text-center py-5 text-muted">
                        <span class="material-symbols-rounded fs-1 d-block mb-2 text-secondary">inbox</span>
                        Nenhum registro encontrado no sistema.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<script>
function filtrarOrdens() {
    let input = document.getElementById("filtroM3");
    let filter = input.value.toLowerCase();
    let tr = document.getElementById("tabelaM3").getElementsByTagName("tr");

    for (let i = 1; i < tr.length; i++) {
        let textoLinha = tr[i].textContent || tr[i].innerText;
        if (textoLinha.toLowerCase().indexOf(filter) > -1) {
            tr[i].style.display = "";
        } else {
            tr[i].style.display = "none";
        }
    }
}
</script>
{% endblock %}
"""
)

# ================= NOVA OS (MATERIAL 3) =================
NOVA_OS_HTML = (
    BASE_HTML
    + """
{% block content %}
<div class="row justify-content-center">
    <div class="col-12 col-md-8 col-lg-7">
        <div class="m3-card p-4 p-md-5">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="m3-icon-badge" style="background: var(--md-sys-color-primary-container);">
                    <span class="material-symbols-rounded fs-2 text-primary">add_circle</span>
                </div>
                <div>
                    <h4 class="fw-bold mb-0">Nova Requisição</h4>
                    <span class="text-muted small">Abertura de chamado técnico de manutenção</span>
                </div>
            </div>

            <form method="POST">
                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Equipamento ou Local:</label>
                    <input type="text" name="equipamento" class="form-control m3-input" placeholder="Ex: Torno CNC, Gerador Diesel, Split Sala 03" required autofocus>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Solicitante:</label>
                    <input type="text" name="solicitante" class="form-control m3-input" placeholder="Ex: Robson Cadete (Operações)" required>
                </div>

                <div class="mb-4">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Sintoma / Descrição da Falha:</label>
                    <textarea name="problema" rows="4" class="form-control m3-input" placeholder="Descreva os ruídos, códigos de alarme ou motivo da intervenção preventiva..." required></textarea>
                </div>

                <div class="d-flex justify-content-between align-items-center pt-2">
                    <a href="/" class="m3-btn-tonal">Voltar</a>
                    <button type="submit" class="m3-btn-filled">
                        <span class="material-symbols-rounded">send</span> Gravar Chamado
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""
)

# ================= FINALIZAR OS (MATERIAL 3) =================
FINALIZAR_OS_HTML = (
    BASE_HTML
    + """
{% block content %}
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

            <!-- Resumo da Requisição -->
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
                        <span class="text-secondary small fw-bold text-uppercase">Problema Relatado:</span>
                        <div class="text-dark">{{ os['problema'] }}</div>
                    </div>
                </div>
            </div>

            <form method="POST">
                <div class="row g-3 mb-3">
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Técnico / Operador Responsável:</label>
                        <input type="text" name="operador" class="form-control m3-input" placeholder="Nome completo do executor" required autofocus>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label small fw-bold text-uppercase text-secondary">Data e Hora de Conclusão:</label>
                        <input type="text" name="data_finalizacao" class="form-control m3-input" value="{{ agora }}" required>
                    </div>
                </div>

                <div class="mb-4">
                    <label class="form-label small fw-bold text-uppercase text-secondary">Ações Executadas & Testes Finais:</label>
                    <textarea name="servico_executado" rows="3" class="form-control m3-input" placeholder="Detalhes dos reparos, peças trocadas e resultados dos testes operacionais..." required></textarea>
                </div>

                <!-- Tonal Box de Custos -->
                <div class="m3-card p-4 mb-4 border">
                    <h6 class="fw-bold mb-3 d-flex align-items-center gap-2" style="color: var(--md-sys-color-primary);">
                        <span class="material-symbols-rounded">calculate</span> Apontamento Financeiro
                    </h6>
                    <div class="mb-3">
                        <label class="form-label small fw-semibold text-secondary">PEÇAS / INSUMOS APLICADOS:</label>
                        <input type="text" name="pecas" class="form-control m3-input" placeholder="Ex: 2x Rolamentos blindados, Fluido lubrificante">
                    </div>
                    <div class="row g-3">
                        <div class="col-12 col-md-4">
                            <label class="form-label small fw-semibold text-secondary">CUSTO PEÇAS (R$):</label>
                            <input type="number" step="0.01" min="0" name="custo_pecas" id="custo_pecas" class="form-control m3-input fw-bold" value="0.00" oninput="calcularTotal()">
                        </div>
                        <div class="col-6 col-md-4">
                            <label class="form-label small fw-semibold text-secondary">HORAS TRABALHADAS (h):</label>
                            <input type="number" step="0.1" min="0" name="horas_trabalhadas" id="horas_trabalhadas" class="form-control m3-input fw-bold" value="1.0" oninput="calcularTotal()">
                        </div>
                        <div class="col-6 col-md-4">
                            <label class="form-label small fw-semibold text-secondary">VALOR DA HORA (R$):</label>
                            <input type="number" step="0.01" min="0" name="valor_hora" id="valor_hora" class="form-control m3-input fw-bold" value="80.00" oninput="calcularTotal()">
                        </div>
                    </div>

                    <div class="d-flex justify-content-between align-items-center mt-3 pt-3 border-top">
                        <span class="text-secondary small fw-bold">MÃO DE OBRA: <strong id="lbl_subtotal_mo" class="text-dark">R$ 80,00</strong></span>
                        <span class="fs-5 fw-bold" style="color: var(--md-sys-color-primary);">VALOR TOTAL: <strong id="lbl_total" class="fs-4">R$ 80,00</strong></span>
                    </div>
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

<script>
function calcularTotal() {
    const pecas = parseFloat(document.getElementById('custo_pecas').value) || 0;
    const horas = parseFloat(document.getElementById('horas_trabalhadas').value) || 0;
    const valorHora = parseFloat(document.getElementById('valor_hora').value) || 0;

    const mo = horas * valorHora;
    const total = pecas + mo;

    document.getElementById('lbl_subtotal_mo').innerText = 'R$ ' + mo.toFixed(2);
    document.getElementById('lbl_total').innerText = 'R$ ' + total.toFixed(2);
}
</script>
{% endblock %}
"""
)

# ================= RECIBO A4 (2 VIAS) =================
RECIBO_A4_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Recibo OS #{{ "%05d" % os['id'] }} - Manutenção</title>
<style>
  @page {
    size: A4;
    margin: 8mm 10mm;
    background-color: #ffffff;
  }
  *, *::before, *::after {
    box-sizing: border-box;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #0f172a;
    margin: 0;
    padding: 0;
    font-size: 8.5pt;
    line-height: 1.25;
  }
  .receipt-via {
    height: 134mm;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 10px 14px;
    background: #ffffff;
  }
  .header-table {
    width: 100%;
    border-bottom: 2px solid #0f172a;
    padding-bottom: 4px;
    margin-bottom: 6px;
  }
  .header-title {
    font-size: 11pt;
    font-weight: 800;
    color: #0f172a;
    text-transform: uppercase;
  }
  .badge-via {
    display: inline-block;
    background-color: #0f172a;
    color: #ffffff;
    font-size: 7.5pt;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 3px;
    text-transform: uppercase;
  }
  .badge-via.operador {
    background-color: #0284c7;
  }
  .os-number {
    font-size: 11.5pt;
    font-weight: 800;
    color: #0f172a;
    text-align: right;
  }
  .info-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 6px;
  }
  .info-table td {
    padding: 3px 4px;
    vertical-align: top;
  }
  .label {
    font-size: 7pt;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
  }
  .value {
    font-size: 8.5pt;
    color: #0f172a;
  }
  .box-section {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 5px 8px;
    margin-bottom: 5px;
  }
  .box-title {
    font-size: 7pt;
    font-weight: 700;
    text-transform: uppercase;
    color: #475569;
    margin-bottom: 2px;
  }
  .box-content {
    font-size: 8pt;
    color: #1e293b;
    white-space: pre-line;
  }
  .finance-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 4px;
    margin-bottom: 6px;
    font-size: 8pt;
  }
  .finance-table th {
    background: #f1f5f9;
    color: #334155;
    text-align: left;
    padding: 4px 6px;
    font-size: 7pt;
    text-transform: uppercase;
    border-bottom: 1.5px solid #cbd5e1;
  }
  .finance-table td {
    padding: 3px 6px;
    border-bottom: 1px solid #e2e8f0;
  }
  .finance-table tr.total-row td {
    border-top: 2px solid #0f172a;
    font-weight: 800;
    font-size: 8.5pt;
    color: #0f172a;
    background: #f8fafc;
  }
  .signatures {
    width: 100%;
    margin-top: 10px;
  }
  .sig-line {
    border-top: 1px solid #64748b;
    width: 80%;
    margin: 0 auto;
    padding-top: 3px;
    font-size: 7pt;
    color: #475569;
    text-align: center;
  }
  .cut-divider {
    height: 10mm;
    text-align: center;
    position: relative;
    margin: 1mm 0;
  }
  .cut-line {
    border-top: 1.5px dashed #94a3b8;
    position: absolute;
    top: 50%;
    width: 100%;
  }
  .cut-text {
    position: relative;
    background: #ffffff;
    display: inline-block;
    padding: 0 10px;
    font-size: 7.5pt;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  @media print {
    .no-print { display: none !important; }
  }
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
      <td style="width: 70%;">
        <span class="badge-via {{ badge_class }}">{{ tipo }}</span>
        <div class="header-title">Ordem de Serviço - Manutenção</div>
      </td>
      <td style="width: 30%; text-align: right;">
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
    <div class="box-title">Descrição do Problema / Requisição:</div>
    <div class="box-content">{{ os['problema'] }}</div>
  </div>

  <div class="box-section">
    <div class="box-title">Serviço Executado:</div>
    <div class="box-content">{{ os['servico_executado'] or 'Em andamento' }}</div>
  </div>

  <table class="finance-table">
    <thead>
      <tr>
        <th>Descrição de Custos & Insumos</th>
        <th style="width: 80px; text-align: center;">Qtd / Horas</th>
        <th style="width: 90px; text-align: right;">Valor Unit.</th>
        <th style="width: 90px; text-align: right;">Subtotal</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Peças: {{ os['pecas'] or 'Nenhum insumo extra lançado' }}</td>
        <td style="text-align: center;">-</td>
        <td style="text-align: right;">-</td>
        <td style="text-align: right;">R$ {{ "%.2f" % (os['custo_pecas'] or 0.0) }}</td>
      </tr>
      <tr>
        <td>Mão de Obra Técnica Especializada</td>
        <td style="text-align: center;">{{ "%.1f" % (os['horas_trabalhadas'] or 0.0) }} h</td>
        <td style="text-align: right;">R$ {{ "%.2f" % (os['valor_hora'] or 0.0) }}</td>
        <td style="text-align: right;">R$ {{ "%.2f" % ((os['horas_trabalhadas'] or 0.0) * (os['valor_hora'] or 0.0)) }}</td>
      </tr>
      <tr class="total-row">
        <td colspan="3" style="text-align: right;">VALOR TOTAL DA ORDEM DE SERVIÇO:</td>
        <td style="text-align: right;">R$ {{ "%.2f" % (os['custo_total'] or 0.0) }}</td>
      </tr>
    </tbody>
  </table>

  <table class="signatures">
    <tr>
      <td style="width: 50%; text-align: center;">
        <div class="sig-line">Assinatura do Solicitante / Empresa</div>
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


# ================= ROTAS =================
@app.route("/")
def index():
  with get_db() as conn:
    ordens = conn.execute(
        "SELECT * FROM ordens_servico ORDER BY id DESC"
    ).fetchall()

    total_os = len(ordens)
    os_abertas = sum(1 for o in ordens if o["status"] == "ABERTA")
    os_concluidas = sum(1 for o in ordens if o["status"] == "CONCLUÍDA")
    faturamento_total = sum(
        (o["custo_total"] or 0.0) for o in ordens if o["status"] == "CONCLUÍDA"
    )

  return render_template_string(
      INDEX_HTML,
      ordens=ordens,
      total_os=total_os,
      os_abertas=os_abertas,
      os_concluidas=os_concluidas,
      faturamento_total=faturamento_total,
  )


@app.route("/nova-os", methods=["GET", "POST"])
def nova_os():
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

  return render_template_string(NOVA_OS_HTML)


@app.route("/finalizar/<int:os_id>", methods=["GET", "POST"])
def finalizar(os_id):
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

    custo_pecas = float(request.form.get("custo_pecas", 0) or 0)
    horas_trabalhadas = float(request.form.get("horas_trabalhadas", 0) or 0)
    valor_hora = float(request.form.get("valor_hora", 0) or 0)
    custo_total = custo_pecas + (horas_trabalhadas * valor_hora)

    with get_db() as conn:
      conn.execute(
          """
                UPDATE ordens_servico
                SET operador = ?, data_finalizacao = ?, servico_executado = ?,
                    pecas = ?, custo_pecas = ?, horas_trabalhadas = ?,
                    valor_hora = ?, custo_total = ?, status = 'CONCLUÍDA'
                WHERE id = ?
            """,
          (
              operador,
              data_finalizacao,
              servico_executado,
              pecas,
              custo_pecas,
              horas_trabalhadas,
              valor_hora,
              custo_total,
              os_id,
          ),
      )
      conn.commit()
    return redirect(url_for("recibo", os_id=os_id))

  agora = datetime.now().strftime("%d/%m/%Y %H:%M")
  return render_template_string(FINALIZAR_OS_HTML, os=os_item, agora=agora)


@app.route("/recibo/<int:os_id>")
def recibo(os_id):
  with get_db() as conn:
    os_item = conn.execute(
        "SELECT * FROM ordens_servico WHERE id = ?", (os_id,)
    ).fetchone()

  if not os_item:
    return "Ordem de Serviço não encontrada", 404

  return render_template_string(RECIBO_A4_HTML, os=os_item)


@app.route("/recibo/<int:os_id>/pdf")
def baixar_pdf(os_id):
  with get_db() as conn:
    os_item = conn.execute(
        "SELECT * FROM ordens_servico WHERE id = ?", (os_id,)
    ).fetchone()

  if not os_item:
    return "Ordem de Serviço não encontrada", 404

  html_renderizado = render_template_string(RECIBO_A4_HTML, os=os_item)

  if TEM_WEASYPRINT:
    pdf_bytes = weasyprint.HTML(string=html_renderizado).write_pdf()
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Recibo_OS_{os_id:05d}.pdf",
    )
  else:
    return render_template_string(RECIBO_A4_HTML, os=os_item)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
