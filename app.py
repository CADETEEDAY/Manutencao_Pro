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

# ================= TEMPLATE BASE MODERNO =================
BASE_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Manutenção - Gestão Operacional</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --surface: #ffffff;
            --background: #f8fafc;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }
        body {
            background-color: var(--background);
            color: var(--text-main);
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }
        .navbar-custom {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
        }
        .card-custom {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }
        .stat-card {
            border-radius: 12px;
            padding: 16px;
            border-left: 4px solid;
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .stat-total { border-left-color: #2563eb; }
        .stat-aberta { border-left-color: #f59e0b; }
        .stat-concluida { border-left-color: #10b981; }
        .stat-financeiro { border-left-color: #6366f1; }
        .badge-pill-aberta {
            background-color: #fef3c7;
            color: #b45309;
            font-weight: 700;
            padding: 6px 12px;
            border-radius: 50px;
        }
        .badge-pill-concluida {
            background-color: #d1fae5;
            color: #047857;
            font-weight: 700;
            padding: 6px 12px;
            border-radius: 50px;
        }
        .btn-action {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            min-height: 38px;
            border-radius: 8px;
            font-weight: 600;
        }
        .form-control, .form-select {
            border-radius: 8px;
            border: 1px solid #cbd5e1;
            padding: 10px 14px;
        }
        .form-control:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark navbar-custom sticky-top mb-4">
        <div class="container">
            <a class="navbar-brand d-flex align-items-center gap-2 fw-bold" href="/">
                <i class="bi bi-tools text-primary fs-4"></i>
                <span>Manutenção</span>
            </a>
            <div class="d-flex gap-2">
                <a class="btn btn-primary btn-action px-3" href="/nova-os">
                    <i class="bi bi-plus-lg"></i>
                    <span>Nova OS</span>
                </a>
            </div>
        </div>
    </nav>
    <div class="container pb-5">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# ================= TELA PRINCIPAL (DASHBOARD) =================
INDEX_HTML = (
    BASE_HTML
    + """
{% block content %}
<!-- CARDS DE ESTATÍSTICAS -->
<div class="row g-3 mb-4">
    <div class="col-6 col-lg-3">
        <div class="stat-card stat-total">
            <div class="text-muted small text-uppercase fw-bold">Total de OS</div>
            <div class="fs-3 fw-bold text-dark mt-1">{{ total_os }}</div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="stat-card stat-aberta">
            <div class="text-muted small text-uppercase fw-bold">Chamados Abertos</div>
            <div class="fs-3 fw-bold text-warning mt-1">{{ os_abertas }}</div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="stat-card stat-concluida">
            <div class="text-muted small text-uppercase fw-bold">Concluídas</div>
            <div class="fs-3 fw-bold text-success mt-1">{{ os_concluidas }}</div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="stat-card stat-financeiro">
            <div class="text-muted small text-uppercase fw-bold">Total em Serviços</div>
            <div class="fs-3 fw-bold text-primary mt-1">R$ {{ "%.2f" % faturamento_total }}</div>
        </div>
    </div>
</div>

<!-- BARRA DE PESQUISA -->
<div class="card-custom p-3 mb-4">
    <div class="row align-items-center g-3">
        <div class="col-12 col-md-6">
            <div class="input-group">
                <span class="input-group-text bg-white border-end-0"><i class="bi bi-search text-muted"></i></span>
                <input type="text" id="filtroTabela" class="form-control border-start-0" placeholder="Filtrar por equipamento, operador ou solicitante..." onkeyup="filtrarOrdens()">
            </div>
        </div>
        <div class="col-12 col-md-6 text-md-end text-muted small">
            <i class="bi bi-clock-history me-1"></i> Listando ordens cadastradas
        </div>
    </div>
</div>

<!-- TABELA DE ORDENS -->
<div class="card-custom overflow-hidden">
    <div class="table-responsive">
        <table class="table table-hover align-middle mb-0" id="tabelaOS">
            <thead class="table-light">
                <tr>
                    <th class="ps-3">Nº OS</th>
                    <th>Equipamento / Local</th>
                    <th>Solicitante</th>
                    <th>Operador Técnico</th>
                    <th>Abertura</th>
                    <th>Valor Total</th>
                    <th>Status</th>
                    <th class="text-end pe-3">Ações</th>
                </tr>
            </thead>
            <tbody>
                {% for os in ordens %}
                <tr>
                    <td class="ps-3 fw-bold text-primary">#{{ "%05d" % os['id'] }}</td>
                    <td class="fw-semibold">{{ os['equipamento'] }}</td>
                    <td>{{ os['solicitante'] }}</td>
                    <td>
                        {% if os['operador'] %}
                            <span class="fw-semibold">{{ os['operador'] }}</span>
                        {% else %}
                            <span class="text-muted fst-italic">Não atribuído</span>
                        {% endif %}
                    </td>
                    <td class="small text-muted">{{ os['data_abertura'] }}</td>
                    <td class="fw-bold text-dark">
                        {% if os['custo_total'] %}
                            R$ {{ "%.2f" % os['custo_total'] }}
                        {% else %}
                            <span class="text-muted">-</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if os['status'] == 'ABERTA' %}
                            <span class="badge-pill-aberta"><i class="bi bi-hourglass-split me-1"></i>ABERTA</span>
                        {% else %}
                            <span class="badge-pill-concluida"><i class="bi bi-check-circle-fill me-1"></i>CONCLUÍDA</span>
                        {% endif %}
                    </td>
                    <td class="text-end pe-3">
                        {% if os['status'] == 'ABERTA' %}
                            <a href="/finalizar/{{ os['id'] }}" class="btn btn-sm btn-warning btn-action text-dark">
                                <i class="bi bi-tools"></i> Finalizar
                            </a>
                        {% else %}
                            <a href="/recibo/{{ os['id'] }}" class="btn btn-sm btn-outline-primary btn-action" title="Abrir Recibo">
                                <i class="bi bi-receipt"></i> Recibo
                            </a>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="8" class="text-center py-5 text-muted">
                        <i class="bi bi-inbox fs-1 d-block mb-2 text-secondary"></i>
                        Nenhuma ordem de serviço cadastrada até o momento.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<script>
function filtrarOrdens() {
    let input = document.getElementById("filtroTabela");
    let filter = input.value.toLowerCase();
    let tr = document.getElementById("tabelaOS").getElementsByTagName("tr");

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

# ================= NOVA OS =================
NOVA_OS_HTML = (
    BASE_HTML
    + """
{% block content %}
<div class="row justify-content-center">
    <div class="col-12 col-md-8 col-lg-7">
        <div class="card-custom p-4">
            <div class="d-flex align-items-center gap-3 mb-3">
                <div class="bg-primary text-white p-3 rounded-circle d-flex align-items-center justify-content-center" style="width: 48px; height: 48px;">
                    <i class="bi bi-file-earmark-plus fs-4"></i>
                </div>
                <div>
                    <h4 class="fw-bold mb-0">Nova Ordem de Serviço</h4>
                    <span class="text-muted small">Abertura de chamado técnico corretivo ou preventivo</span>
                </div>
            </div>
            <hr class="text-muted mb-4">
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label fw-bold small text-uppercase">Equipamento / Máquina / Local:</label>
                    <input type="text" name="equipamento" class="form-control" placeholder="Ex: Torno CNC, Gerador, Ar Condicionado" required autofocus>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold small text-uppercase">Solicitante (Setor ou Responsável):</label>
                    <input type="text" name="solicitante" class="form-control" placeholder="Ex: Coordenação de Manutenção" required>
                </div>
                <div class="mb-4">
                    <label class="form-label fw-bold small text-uppercase">Descrição da Ocorrência / Defeito:</label>
                    <textarea name="problema" rows="4" class="form-control" placeholder="Descreva os ruídos, paradas, códigos de erro ou inspeções necessárias..." required></textarea>
                </div>
                <div class="d-flex gap-2 justify-content-between pt-2">
                    <a href="/" class="btn btn-outline-secondary btn-action px-4">Voltar</a>
                    <button type="submit" class="btn btn-primary btn-action px-4">
                        <i class="bi bi-save2"></i> Gravar Chamado
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""
)

# ================= FINALIZAR OS =================
FINALIZAR_OS_HTML = (
    BASE_HTML
    + """
{% block content %}
<div class="row justify-content-center">
    <div class="col-12 col-lg-8">
        <div class="card-custom p-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div>
                    <h4 class="fw-bold text-success mb-0"><i class="bi bi-check2-circle me-2"></i>Conclusão de Serviço</h4>
                    <span class="text-muted small">Fechamento técnico da OS #{{ "%05d" % os['id'] }}</span>
                </div>
                <span class="badge bg-light text-dark border p-2 small">Aberta em: {{ os['data_abertura'] }}</span>
            </div>

            <div class="p-3 bg-light rounded-3 border mb-4">
                <div class="row">
                    <div class="col-12 col-md-6 mb-2 mb-md-0">
                        <span class="text-muted small text-uppercase d-block fw-bold">Equipamento:</span>
                        <strong class="text-dark">{{ os['equipamento'] }}</strong>
                    </div>
                    <div class="col-12 col-md-6">
                        <span class="text-muted small text-uppercase d-block fw-bold">Solicitante:</span>
                        <strong class="text-dark">{{ os['solicitante'] }}</strong>
                    </div>
                    <div class="col-12 mt-2 pt-2 border-top">
                        <span class="text-muted small text-uppercase d-block fw-bold">Defeito Informado:</span>
                        <span class="text-secondary">{{ os['problema'] }}</span>
                    </div>
                </div>
            </div>

            <form method="POST">
                <div class="row g-3 mb-3">
                    <div class="col-12 col-md-6">
                        <label class="form-label fw-bold small text-uppercase">Operador Técnico:</label>
                        <input type="text" name="operador" class="form-control" placeholder="Nome completo do executor" required autofocus>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label fw-bold small text-uppercase">Data e Hora de Conclusão:</label>
                        <input type="text" name="data_finalizacao" class="form-control" value="{{ agora }}" required>
                    </div>
                </div>

                <div class="mb-4">
                    <label class="form-label fw-bold small text-uppercase">Serviço Executado e Ajustes Realizados:</label>
                    <textarea name="servico_executado" rows="3" class="form-control" placeholder="Descreva os procedimentos executados, calibragens e testes finais..." required></textarea>
                </div>

                <div class="card bg-white border p-3 mb-4 rounded-3 shadow-sm">
                    <h6 class="fw-bold text-primary mb-3"><i class="bi bi-calculator me-1"></i> Peças, Mão de Obra e Fechamento</h6>
                    <div class="mb-3">
                        <label class="form-label small text-muted fw-bold text-uppercase">Relação de Peças / Insumos Usados:</label>
                        <input type="text" name="pecas" class="form-control" placeholder="Ex: 2x Rolamentos, 1L Lubrificante, Vedações">
                    </div>
                    <div class="row g-3">
                        <div class="col-12 col-md-4">
                            <label class="form-label small text-muted fw-bold">CUSTO PEÇAS (R$):</label>
                            <input type="number" step="0.01" min="0" name="custo_pecas" id="custo_pecas" class="form-control fw-bold" value="0.00" oninput="calcularTotal()">
                        </div>
                        <div class="col-6 col-md-4">
                            <label class="form-label small text-muted fw-bold">HORAS TÉCNICAS (h):</label>
                            <input type="number" step="0.1" min="0" name="horas_trabalhadas" id="horas_trabalhadas" class="form-control fw-bold" value="1.0" oninput="calcularTotal()">
                        </div>
                        <div class="col-6 col-md-4">
                            <label class="form-label small text-muted fw-bold">VALOR / HORA (R$):</label>
                            <input type="number" step="0.01" min="0" name="valor_hora" id="valor_hora" class="form-control fw-bold" value="80.00" oninput="calcularTotal()">
                        </div>
                    </div>
                    <div class="d-flex justify-content-between align-items-center mt-3 pt-3 border-top">
                        <span class="text-muted">Mão de Obra: <strong id="lbl_subtotal_mo" class="text-dark">R$ 80,00</strong></span>
                        <span class="fs-5 text-primary">Custo Total: <strong id="lbl_total" class="fs-4">R$ 80,00</strong></span>
                    </div>
                </div>

                <div class="d-flex justify-content-between pt-2">
                    <a href="/" class="btn btn-outline-secondary btn-action px-4">Voltar</a>
                    <button type="submit" class="btn btn-success btn-action px-4">
                        <i class="bi bi-printer"></i> Finalizar & Emitir Recibo
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

# ================= TEMPLATE DE RECIBO A4 (2 VIAS) =================
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
    <button onclick="window.print()" style="padding:8px 20px; font-weight:bold; cursor:pointer; background:#0284c7; color:#fff; border:none; border-radius:6px; font-size:10pt;">
        🖨️ Imprimir Recibo / Salvar PDF
    </button>
    <a href="/" style="margin-left:15px; font-size:9pt; color:#475569; text-decoration:none; font-weight:600;">⬅ Voltar ao Painel</a>
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

    # Cálculo dos indicadores para os cards do topo
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
