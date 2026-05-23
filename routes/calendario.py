from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, session)
from flask_login import login_required, current_user
from routes.auth import is_admin
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
    if not is_admin():
        flash("Acesso restrito ao administrador.", "danger")
        return redirect(url_for("calendario.index"))
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
            import traceback
            erro = str(e)
            detalhe = traceback.format_exc()
            current_app.logger.error(f"Erro importar calendário: {detalhe}")
            if "403" in erro or "API_KEY" in erro or "GEMINI_API_KEY" in erro:
                flash("Erro de autenticação com o Gemini (403). Verifique a variável GEMINI_API_KEY no Railway.", "danger")
            elif "404" in erro:
                flash(f"Modelo Gemini não encontrado (404): {erro}", "danger")
            elif "429" in erro:
                flash("Limite de requisições do Gemini atingido (429). Aguarde alguns minutos e tente novamente.", "danger")
            elif "JSONDecodeError" in detalhe or "json" in detalhe.lower():
                flash("O Gemini retornou uma resposta inválida. Tente novamente ou use um PDF diferente.", "danger")
            else:
                flash(f"Erro: {erro}", "danger")
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
    if not is_admin():
        flash("Acesso restrito ao administrador.", "danger")
        return redirect(url_for("calendario.index"))
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


# ── Gemini extrai os eventos do PDF ──────────────────────────────────────────

def _extrair_eventos_com_claude(pdf_b64: str, ano_letivo: str) -> list[dict]:
    """Envia o PDF para a API do Gemini e retorna lista de eventos JSON."""
    import urllib.request, urllib.error, json as _json, os

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não configurada. Adicione a variável no Railway → Settings → Variables.")

    prompt = (
        f"Analise este calendário escolar letivo de {ano_letivo} da SEEDF ou escola brasileira. "
        "Extraia TODOS os eventos: feriados, recessos, reuniões, comemorações, dias especiais. "
        "Responda APENAS com um array JSON puro, sem markdown, sem texto antes ou depois. "
        "Cada item deve ter: titulo (string), data_inicio (YYYY-MM-DD), data_fim (YYYY-MM-DD ou igual a data_inicio), "
        f"tipo (feriado|recesso|reuniao|prova|evento|comemorativo|outro), descricao (string). "
        f"Se o ano não estiver explícito use {ano_letivo}. Não omita nenhum evento visível."
    )

    def _post(url, body):
        req = urllib.request.Request(
            url, data=_json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return _json.loads(resp.read())

    def _url(model):
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    modelos = ["gemini-2.5-flash", "gemini-2.0-flash"]
    data       = None
    ultimo_erro = ""

    for modelo in modelos:
        body = {
            "contents": [{"parts": [
                {"inline_data": {"mime_type": "application/pdf", "data": pdf_b64}},
                {"text": prompt},
            ]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 8192},
        }
        try:
            data = _post(_url(modelo), body)
            if "candidates" in data:
                break
            ultimo_erro = f"Resposta sem candidates no modelo {modelo}: {str(data)[:200]}"
            data = None
        except urllib.error.HTTPError as e:
            corpo = e.read().decode("utf-8", errors="replace")[:300]
            ultimo_erro = f"HTTP {e.code} no modelo {modelo}: {corpo}"
            data = None
        except Exception as e:
            ultimo_erro = f"Erro no modelo {modelo}: {e}"
            data = None

    if data is None:
        raise RuntimeError(ultimo_erro or "Falha ao chamar a API do Gemini.")

    # Extrai o texto da resposta
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Resposta inesperada do Gemini: {str(data)[:300]}")

    # Limpa possíveis blocos de código markdown
    raw = raw.strip()
    for prefix in ["```json", "```"]:
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    raw = raw.rstrip("`").strip()

    # Parse JSON com mensagem clara em caso de falha
    try:
        eventos = _json.loads(raw)
    except _json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini retornou resposta não-JSON: {raw[:200]}")

    if not isinstance(eventos, list):
        raise RuntimeError(f"Gemini retornou formato inesperado (esperava lista): {str(eventos)[:200]}")

    # Normaliza campos
    tipos_validos = {"feriado","recesso","reuniao","prova","evento","aula","comemorativo","outro"}
    resultado = []
    for ev in eventos:
        if not isinstance(ev, dict):
            continue
        di = ev.get("data_inicio", "")
        df = ev.get("data_fim", "") or di
        tipo = ev.get("tipo", "outro")
        if tipo not in tipos_validos:
            tipo = "outro"
        resultado.append({
            "titulo":      str(ev.get("titulo", "Evento")).strip(),
            "data_inicio": di,
            "data_fim":    df,
            "tipo":        tipo,
            "descricao":   str(ev.get("descricao", "") or "").strip(),
        })
    return resultado


# ── API: eventos do mês ───────────────────────────────────────────────────────

@cal_bp.route("/api/mes")
@login_required
def api_mes():
    """Retorna eventos do mês para o calendário dinâmico."""
    hoje = date.today()
    ano  = request.args.get("ano",  hoje.year,  type=int)
    mes  = request.args.get("mes",  hoje.month, type=int)
    from calendar import monthrange
    ultimo = monthrange(ano, mes)[1]
    di = date(ano, mes, 1)
    df = date(ano, mes, ultimo)
    evs = EventoCalendario.query.filter(
        EventoCalendario.professor_id == current_user.id,
        EventoCalendario.data_inicio  <= df,
        db.or_(
            EventoCalendario.data_fim   >= di,
            EventoCalendario.data_fim.is_(None),
        )
    ).all()
    return jsonify([{
        "id":          e.id,
        "titulo":      e.titulo,
        "tipo":        e.tipo or "outro",
        "cor":         e.cor or "#6b7280",
        "descricao":   e.descricao or "",
        "data_inicio": e.data_inicio.isoformat(),
        "data_fim":    e.data_fim.isoformat() if e.data_fim else e.data_inicio.isoformat(),
    } for e in evs])


# ── API: salvar evento (criar ou editar) via JSON ─────────────────────────────

@cal_bp.route("/api/salvar", methods=["POST"])
@cal_bp.route("/api/salvar/<int:id>", methods=["POST"])
@login_required
def api_salvar(id=None):
    dados = request.get_json()
    try:
        di = datetime.strptime(dados["data_inicio"], "%Y-%m-%d").date()
        df = datetime.strptime(dados["data_fim"],    "%Y-%m-%d").date() if dados.get("data_fim") else di
    except (ValueError, KeyError):
        return jsonify({"ok": False, "erro": "Data inválida"}), 400

    if id:
        ev = EventoCalendario.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    else:
        ev = EventoCalendario(professor_id=current_user.id)
        db.session.add(ev)

    ev.titulo      = dados.get("titulo", "Evento").strip()
    ev.tipo        = dados.get("tipo", "outro")
    ev.cor         = dados.get("cor", "#6b7280")
    ev.descricao   = dados.get("descricao", "") or None
    ev.data_inicio = di
    ev.data_fim    = df

    db.session.commit()

    # ── Sincronizar com frequência ────────────────────────────────────────────
    # Para feriados e recessos, marca afastamento em todas as turmas do professor
    tipos_sem_aula = {"feriado", "recesso"}
    if ev.tipo in tipos_sem_aula:
        _sincronizar_frequencia(ev)

    return jsonify({"ok": True, "id": ev.id})


def _sincronizar_frequencia(ev):
    """Cria registros de 'afastamento' na frequência para todos os dias do evento."""
    from models.models import Turma, Aluno, Frequencia
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    if not turmas:
        return

    d = ev.data_inicio
    fim = ev.data_fim or ev.data_inicio
    while d <= fim:
        for turma in turmas:
            for aluno in turma.alunos:
                existe = Frequencia.query.filter_by(
                    aluno_id=aluno.id,
                    professor_id=current_user.id,
                    data=d,
                ).first()
                if not existe:
                    db.session.add(Frequencia(
                        aluno_id=aluno.id,
                        turma_id=turma.id,
                        professor_id=current_user.id,
                        data=d,
                        status="afastamento",
                        observacao=f"Evento: {ev.titulo}",
                    ))
        d = date(d.year, d.month, d.day)
        from datetime import timedelta
        d += timedelta(days=1)
    db.session.commit()
