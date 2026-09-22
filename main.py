from datetime import datetime
import io
import os
import sqlite3
from flask import Flask, redirect, render_template_string, request, send_file, url_for

# Suporte opcional a PDF via WeasyPrint quando rodar em servidores Linux/Desktop
try:
  import weasyprint

  TEM_WEASYPRINT = True
except ImportError:
  TEM_WEASYPRINT = False

app = Flask(__name__)

# Define o caminho do banco de dados no diretório do app
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

# ================= TEMPLATES HTML =================
BASE_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manutenção</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        body { background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .navbar-brand { font-weight: 700; letter-spacing: 0.5px; }
        .card { border: none; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07); }
        .badge-aberta { background-color: #ea580c; color: white; }
        .badge-concluida { background-color: #16a34a; color: white; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4 shadow-sm">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="bi bi-tools me-2"></i>Manutenção</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link text-white" href="/"><i class="bi bi-list-check me-1"></i>Painel Geral</a>
                <a class="nav-link btn btn-primary text-white ms-2 px-3" href="/nova-os"><i class="bi bi-plus-circle me-1"></i>Nova Requisição</a>
            </div>
        </div>
    </nav>
    <div class="container pb-5">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

INDEX_HTML = (
    BASE_HTML
    + """
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h3 class="fw-bold text-secondary mb-0">Ordens de Serviço</h3>
    <a href="/nova-os" class="btn btn-primary"><i class="bi bi-plus-lg me-1"></i>Abrir Chamado</a>
</div>

<div class="card p-3">
    <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
                <tr>
                    <th>Nº OS</th>
                    <th>Equipamento / Local</th>
                    <th>Solicitante</th>
                    <th>Operador</th>
                    <th>Abertura</th>
                    <th>Total</th>
                    <th>Status</th>
                    <th class="text-end">Ações</th>
                </tr>
            </thead>
            <tbody>
                {% for os in ordens %}
                <tr>
                    <td class="fw-bold">#{{ "%05d" % os['id'] }}</td>
                    <td>{{ os['equipamento'] }}</td>
                    <td>{{ os['solicitante'] }}</td>
                    <td>{{ os['operador'] or '<span class="text-muted">Aguardando</span>' }}</td>
                    <td>{{ os['data_abertura'] }}</td>
                    <td class="fw-bold text-success">
                        {% if os['custo_total'] %}
                            R$ {{ "%.2f" % os['custo_total'] }}
                        {% else %}
                            -
                        {% endif %}
                    </td>
                    <td>
                        {% if os['status'] == 'ABERTA' %}
                            <span class="badge badge-aberta">ABERTA</span>
                        {% else %}
                            <span class="badge badge-concluida">CONCLUÍDA</span>
                        {% endif %}
                    </td>
                    <td class="text-end">
                        {% if os['status'] == 'ABERTA' %}
                            <a href="/finalizar/{{ os['id'] }}" class="btn btn-sm btn-outline-warning"><i class="bi bi-check2-circle me-1"></i>Finalizar</a>
                        {% else %}
                            <a href="/recibo/{{ os['id'] }}" class="btn btn-sm btn-outline-info" title="Visualizar Recibo"><i class="bi bi-receipt"></i> Recibo</a>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="8" class="text-center py-4 text-muted">Nenhuma ordem de serviço cadastrada.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""
)

NOVA_OS_HTML = (
    BASE_HTML
    + """
{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-8">
        <div class="card p-4">
            <h4 class="fw-bold mb-3 text-primary"><i class="bi bi-file-earmark-plus me-2"></i>Nova Requisição de Manutenção</h4>
            <p class="text-muted small">Preencha os dados do equipamento e a descrição do problema identificado.</p>
            <hr>
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label fw-semibold">Equipamento / Máquina / Local:</label>
                    <input type="text" name="equipamento" class="form-control" placeholder="Ex: Torno CNC, Bomba D'água, Quadro Elétrico" required>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-semibold">Solicitante (Nome / Setor):</label>
                    <input type="text" name="solicitante" class="form-control" placeholder="Ex: Coordenação de Operações" required>
                </div>
                <div class="mb-4">
                    <label class="form-label fw-semibold">Descrição do Problema / Sintoma:</label>
                    <textarea name="problema" rows="4" class="form-control" placeholder="Relate o defeito, ruídos ou inspeção necessária..." required></textarea>
                </div>
                <div class="d-flex justify-content-between">
                    <a href="/" class="btn btn-outline-secondary">Voltar</a>
                    <button type="submit" class="btn btn-primary px-4"><i class="bi bi-check-lg me-1"></i>Salvar Chamado</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""
)

FINALIZAR_OS_HTML = (
    BASE_HTML
    + """
{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-9">
        <div class="card p-4">
            <div class="d-flex justify-content-between align-items-center">
                <h4 class="fw-bold text-success mb-0"><i class="bi bi-clipboard-check me-2"></i>Finalizar OS #{{ "%05d" % os['id'] }}</h4>
                <span class="badge bg-warning text-dark">Aberta em: {{ os['data_abertura'] }}</span>
            </div>
            <div class="alert alert-light border my-3">
                <strong>Equipamento:</strong> {{ os['equipamento'] }} | <strong>Solicitante:</strong> {{ os['solicitante'] }}<br>
                <strong>Problema Constatado:</strong> {{ os['problema'] }}
            </div>
            <form method="POST">
                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Operador Técnico Responsável:</label>
                        <input type="text" name="operador" class="form-control" placeholder="Nome do operador técnico" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Data / Hora de Término:</label>
                        <input type="text" name="data_finalizacao" class="form-control" value="{{ agora }}" required>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label fw-semibold">Descrição do Serviço Executado:</label>
                    <textarea name="servico_executado" rows="3" class="form-control" placeholder="Relate as manutenções, ajustes e trocas efetuadas..." required></textarea>
                </div>

                <h5 class="fw-bold text-secondary mt-4 mb-2"><i class="bi bi-cash-stack me-2"></i>Peças, Insumos e Custos Operacionais</h5>
                <div class="mb-3">
                    <label class="form-label fw-semibold">Relação de Peças / Insumos Aplicados:</label>
                    <input type="text" name="pecas" class="form-control" placeholder="Ex: Rolamento, Óleo lubrificante, Conectores">
                </div>

                <div class="row g-3 p-3 bg-light rounded border mb-4">
                    <div class="col-md-4">
                        <label class="form-label fw-semibold">Custo de Peças (R$):</label>
                        <input type="number" step="0.01" min="0" name="custo_pecas" id="custo_pecas" class="form-control" value="0.00" oninput="calcularTotal()">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-semibold">Horas Trabalhadas (h):</label>
                        <input type="number" step="0.1" min="0" name="horas_trabalhadas" id="horas_trabalhadas" class="form-control" value="1.0" oninput="calcularTotal()">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-semibold">Valor da Hora Técnica (R$):</label>
                        <input type="number" step="0.01" min="0" name="valor_hora" id="valor_hora" class="form-control" value="80.00" oninput="calcularTotal()">
                    </div>
                    <div class="col-12 text-end pt-2">
                        <span class="fs-5 me-2">Mão de Obra: <strong id="lbl_subtotal_mo">R$ 80,00</strong></span> | 
                        <span class="fs-4 ms-2 text-primary">Total: <strong id="lbl_total">R$ 80,00</strong></span>
                    </div>
                </div>

                <div class="d-flex justify-content-between">
                    <a href="/" class="btn btn-outline-secondary">Voltar</a>
                    <button type="submit" class="btn btn-success px-4"><i class="bi bi-printer me-1"></i>Concluir e Emitir Recibo</button>
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
    color: #1e293b;
    margin: 0;
    padding: 0;
    font-size: 8.5pt;
    line-height: 1.25;
  }
  .receipt-via {
    height: 134mm;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 8px 12px;
    background: #ffffff;
  }
  .header-table {
    width: 100%;
    border-bottom: 1.5px solid #0f172a;
    padding-bottom: 4px;
    margin-bottom: 6px;
  }
  .header-title {
    font-size: 11pt;
    font-weight: 700;
    color: #0f172a;
    text-transform: uppercase;
  }
  .badge-via {
    display: inline-block;
    background-color: #0f172a;
    color: #ffffff;
    font-size: 7.5pt;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 3px;
    text-transform: uppercase;
  }
  .badge-via.operador {
    background-color: #0369a1;
  }
  .os-number {
    font-size: 11pt;
    font-weight: 700;
    color: #0f172a;
    text-align: right;
  }
  .info-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 6px;
  }
  .info-table td {
    padding: 2px 4px;
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
    border-radius: 3px;
    padding: 4px 6px;
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
    padding: 3px 5px;
    font-size: 7pt;
    text-transform: uppercase;
    border-bottom: 1px solid #cbd5e1;
  }
  .finance-table td {
    padding: 3px 5px;
    border-bottom: 1px solid #e2e8f0;
  }
  .finance-table tr.total-row td {
    border-top: 1.5px solid #0f172a;
    font-weight: 700;
    font-size: 8.5pt;
    color: #0f172a;
    background: #f8fafc;
  }
  .signatures {
    width: 100%;
    margin-top: 8px;
  }
  .sig-line {
    border-top: 1px solid #64748b;
    width: 80%;
    margin: 0 auto;
    padding-top: 2px;
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
    font-weight: 600;
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

<div class="no-print" style="background:#e0f2fe; padding:12px; margin-bottom:15px; border-radius:6px; text-align:center;">
    <button onclick="window.print()" style="padding:7px 18px; font-weight:bold; cursor:pointer; background:#0284c7; color:#fff; border:none; border-radius:4px; font-size:10pt;">
        🖨️ Imprimir Recibo / Salvar PDF
    </button>
    <a href="/" style="margin-left:15px; font-size:9pt; color:#475569; text-decoration:none;">⬅ Voltar ao Painel</a>
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
        <span class="label">Operador Técnico:</span><br>
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
  return render_template_string(INDEX_HTML, ordens=ordens)


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
    # No celular/Android, renderiza com botão nativo de impressão
    return render_template_string(RECIBO_A4_HTML, os=os_item)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
