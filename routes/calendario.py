from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, session)
from flask_login import login_required, current_user
from app import db
from models.models import EventoCalendario
from datetime import datetime, date
import base64, json, io

cal_bp = Blueprint("calendario", __name__, url_prefix="/calendario")

# ── Cores por tipo ────────────────────────────────────────────────────────────
CORES_TIPO = {
    "feriado":      "#e05c5c",
    "recesso":      "#9ca3af",
    "reuniao":      "#3B82F6",
    "prova":        "#f59e0b",
    "evento":       "#4d7c5f",
    "aula":         "#1a3a5c",
    "comemorativo": "#8b5cf6",
    "outro":        "#6b7280",
}


# ── index ─────────────────────────────────────────────────────────────────────

@cal_bp.route("/")
@login_required
def index():
    eventos = (EventoCalendario.query
               .filter_by(professor_id=current_user.id)
               .order_by(EventoCalendario.data_inicio)
               .all())
    return render_template("calendario/index.html", eventos=eventos, hoje=date.today())


@cal_bp.route("/api/eventos")
@login_required
def api_eventos():
    eventos = EventoCalendario.query.filter_by(professor_id=current_user.id).all()
    return jsonify([{
        "id":    e.id,
        "title": e.titulo,
        "start": e.data_inicio.isoformat(),
        "end":   e.data_fim.isoformat() if e.data_fim else e.data_inicio.isoformat(),
        "color": e.cor,
        "extendedProps": {"tipo": e.tipo, "descricao": e.descricao}
    } for e in eventos])


# ── CRUD manual ───────────────────────────────────────────────────────────────

@cal_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if request.method == "POST":
        _salvar_evento_form(request.form)
        flash("Evento adicionado!", "success")
        return redirect(url_for("calendario.index"))
    return render_template("calendario/form.html", evento=None, cores=CORES_TIPO)


@cal_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    ev = EventoCalendario.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    if request.method == "POST":
        ev.titulo      = request.form["titulo"]
        ev.data_inicio = datetime.strptime(request.form["data_inicio"], "%Y-%m-%d").date()
        ev.data_fim    = (datetime.strptime(request.form["data_fim"], "%Y-%m-%d").date()
                         if request.form.get("data_fim") else None)
        ev.tipo        = request.form.get("tipo", "evento")
        ev.descricao   = request.form.get("descricao", "")
        ev.cor         = CORES_TIPO.get(ev.tipo, "#6b7280")
        db.session.commit()
        flash("Evento atualizado!", "success")
        return redirect(url_for("calendario.index"))
    return render_template("calendario/form.html", evento=ev, cores=CORES_TIPO)


@cal_bp.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    ev = EventoCalendario.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    db.session.delete(ev)
    db.session.commit()
    flash("Evento removido.", "info")
    return redirect(url_for("calendario.index"))


def _salvar_evento_form(form):
    tipo = form.get("tipo", "evento")
    ev   = EventoCalendario(
        titulo      = form["titulo"],
        data_inicio = datetime.strptime(form["data_inicio"], "%Y-%m-%d").date(),
        data_fim    = (datetime.strptime(form["data_fim"], "%Y-%m-%d").date()
                      if form.get("data_fim") else None),
        tipo        = tipo,
        descricao   = form.get("descricao", ""),
        cor         = CORES_TIPO.get(tipo, "#6b7280"),
        professor_id = current_user.id,
    )
    db.session.add(ev)
    db.session.commit()
    return ev


# ── Upload do calendário escolar ──────────────────────────────────────────────

@cal_bp.route("/importar", methods=["GET", "POST"])
@login_required
def importar():
    """Tela de upload: professor envia o PDF do calendário escolar."""
    if request.method == "POST":
        pdf_file = request.files.get("pdf_calendario")
        if not pdf_file or not pdf_file.filename.endswith(".pdf"):
            flash("Por favor, envie um arquivo PDF.", "danger")
            return redirect(url_for("calendario.importar"))

        pdf_bytes  = pdf_file.read()
        pdf_b64    = base64.b64encode(pdf_bytes).decode()
        ano_letivo = request.form.get("ano_letivo", str(date.today().year))

        # Chama Claude para extrair os eventos
        try:
            eventos_extraidos = _extrair_eventos_com_claude(pdf_b64, ano_letivo)
        except Exception as e:
            flash(f"Erro ao processar PDF: {e}", "danger")
            return redirect(url_for("calendario.importar"))

        # Guarda na sessão para confirmação
        session["eventos_importar"] = eventos_extraidos
        session["ano_importar"]     = ano_letivo
        return redirect(url_for("calendario.confirmar_importacao"))

    return render_template("calendario/importar.html", ano_atual=date.today().year)


@cal_bp.route("/importar/confirmar", methods=["GET", "POST"])
@login_required
def confirmar_importacao():
    """Exibe os eventos extraídos para o professor revisar e confirmar."""
    eventos_raw = session.get("eventos_importar", [])
    ano         = session.get("ano_importar", str(date.today().year))

    if not eventos_raw:
        flash("Nenhum dado de importação encontrado. Faça o upload novamente.", "warning")
        return redirect(url_for("calendario.importar"))

    if request.method == "POST":
        # Coleta os eventos marcados pelo professor
        salvos = 0
        for i, ev in enumerate(eventos_raw):
            if request.form.get(f"incluir_{i}"):
                # Permite edição inline dos campos
                titulo      = request.form.get(f"titulo_{i}", ev.get("titulo",""))
                data_inicio = request.form.get(f"data_inicio_{i}", ev.get("data_inicio",""))
                data_fim    = request.form.get(f"data_fim_{i}",    ev.get("data_fim",""))
                tipo        = request.form.get(f"tipo_{i}",        ev.get("tipo","evento"))
                descricao   = request.form.get(f"descricao_{i}",   ev.get("descricao",""))
                try:
                    di = datetime.strptime(data_inicio, "%Y-%m-%d").date()
                    df = datetime.strptime(data_fim, "%Y-%m-%d").date() if data_fim else None
                    evento = EventoCalendario(
                        titulo       = titulo,
                        data_inicio  = di,
                        data_fim     = df,
                        tipo         = tipo,
                        descricao    = descricao,
                        cor          = CORES_TIPO.get(tipo, "#6b7280"),
                        professor_id = current_user.id,
                    )
                    db.session.add(evento)
                    salvos += 1
                except Exception:
                    pass  # data inválida — pula

        db.session.commit()
        session.pop("eventos_importar", None)
        session.pop("ano_importar", None)
        flash(f"{salvos} evento(s) importado(s) com sucesso!", "success")
        return redirect(url_for("calendario.index"))

    return render_template("calendario/confirmar_importacao.html",
                           eventos=eventos_raw, ano=ano, cores=CORES_TIPO)


# ── Claude extrai os eventos do PDF ──────────────────────────────────────────

def _extrair_eventos_com_claude(pdf_b64: str, ano_letivo: str) -> list[dict]:
    """Envia o PDF para a API do Claude e retorna lista de eventos JSON."""
    import urllib.request, json as _json

    prompt = f"""Você está analisando o calendário escolar letivo de {ano_letivo} da SEEDF (Secretaria de Estado de Educação do Distrito Federal) ou de outra escola brasileira.

Extraia TODOS os eventos, feriados, recessos, reuniões, provas, comemorações e dias especiais que encontrar.

Retorne SOMENTE um array JSON válido, sem texto extra, sem markdown, sem explicações.

Cada objeto deve ter exatamente estes campos:
{{
  "titulo": "nome do evento",
  "data_inicio": "YYYY-MM-DD",
  "data_fim": "YYYY-MM-DD ou vazio se evento de 1 dia",
  "tipo": "feriado|recesso|reuniao|prova|evento|aula|comemorativo|outro",
  "descricao": "descrição breve ou vazio"
}}

Regras:
- Se um evento ocupa vários dias, use data_fim diferente de data_inicio
- Se for 1 dia, deixe data_fim vazio ou igual a data_inicio
- tipo deve ser EXATAMENTE uma das opções listadas
- Datas no formato YYYY-MM-DD obrigatoriamente
- Se o ano não estiver explícito, use {ano_letivo}
- Inclua TODOS os eventos visíveis no PDF, não pule nenhum
- Priorize: feriados nacionais, recessos, semanas pedagógicas, Conselhos de Classe, dia do professor, comemorações cívicas"""

    payload = _json.dumps({
        "model":      "claude-sonnet-4-20250514",
        "max_tokens": 4000,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type":   "document",
                    "source": {
                        "type":       "base64",
                        "media_type": "application/pdf",
                        "data":       pdf_b64,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    }).encode()

    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data    = payload,
        headers = {
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
        method = "POST",
    )

    with urllib.request.urlopen(req, timeout=90) as resp:
        data = _json.loads(resp.read())

    raw = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            raw += block["text"]

    # Limpa e faz parse do JSON
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    eventos = _json.loads(raw)
    # Normaliza data_fim vazio
    for ev in eventos:
        if not ev.get("data_fim"):
            ev["data_fim"] = ev.get("data_inicio", "")
    return eventos
