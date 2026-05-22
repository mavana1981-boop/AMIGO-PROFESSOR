from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from routes.pdf_header import cabecalho_pdf
from app import db
from models.models import Turma, Aluno, Frequencia
from datetime import date, datetime, timedelta
from collections import defaultdict
import calendar, io

freq_bp = Blueprint("frequencia", __name__, url_prefix="/frequencia")

BIMESTRES   = {1:(1,3), 2:(4,6), 3:(7,9), 4:(10,12)}
SEMESTRES   = {1:(1,6), 2:(7,12)}
MESES_NOMES = ['','Janeiro','Fevereiro','Março','Abril','Maio','Junho',
               'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
DIAS_SEMANA = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']


# ── helpers ───────────────────────────────────────────────────────────────────

def _aplicar_filtro(query, filtro, valor, ano, data_ini=None, data_fim=None):
    if filtro == "custom" and data_ini and data_fim:
        query = query.filter(Frequencia.data >= data_ini, Frequencia.data <= data_fim)
        return query
    query = query.filter(db.extract("year", Frequencia.data) == ano)
    if filtro == "mes":
        query = query.filter(db.extract("month", Frequencia.data) == valor)
    elif filtro == "bimestre":
        m1, m2 = BIMESTRES.get(valor, (1, 3))
        query  = query.filter(db.extract("month", Frequencia.data) >= m1,
                              db.extract("month", Frequencia.data) <= m2)
    elif filtro == "semestre":
        m1, m2 = SEMESTRES.get(valor, (1, 6))
        query  = query.filter(db.extract("month", Frequencia.data) >= m1,
                              db.extract("month", Frequencia.data) <= m2)
    return query


def calcular_stats_aluno(aluno_id, filtro, valor, ano, data_ini=None, data_fim=None):
    q         = Frequencia.query.filter_by(aluno_id=aluno_id)
    q         = _aplicar_filtro(q, filtro, valor, ano, data_ini, data_fim)
    registros = q.all()
    total     = len(registros)
    presentes = sum(1 for r in registros if r.status == "presente")
    faltas    = total - presentes
    pct       = round(presentes / total * 100, 1) if total > 0 else None
    return total, presentes, faltas, pct


def calcular_stats_turma(turma_id, filtro, valor, ano, data_ini=None, data_fim=None):
    alunos = Aluno.query.filter_by(turma_id=turma_id).all()
    return {a.id: calcular_stats_aluno(a.id, filtro, valor, ano, data_ini, data_fim) for a in alunos}


def _get_filtros():
    hoje     = date.today()
    filtro   = request.args.get("filtro", "mes")
    ano      = request.args.get("ano",      hoje.year,  type=int)
    mes      = request.args.get("mes",      hoje.month, type=int)
    bimestre = request.args.get("bimestre", 1,          type=int)
    semestre = request.args.get("semestre", 1,          type=int)
    valor    = {"mes": mes, "bimestre": bimestre, "semestre": semestre, "ano": ano}.get(filtro, mes)
    data_ini_str = request.args.get("data_ini", "")
    data_fim_str = request.args.get("data_fim", "")
    try:    data_ini = datetime.strptime(data_ini_str, "%Y-%m-%d").date() if data_ini_str else None
    except: data_ini = None
    try:    data_fim = datetime.strptime(data_fim_str, "%Y-%m-%d").date() if data_fim_str else None
    except: data_fim = None
    return filtro, ano, mes, bimestre, semestre, valor, data_ini, data_fim, data_ini_str, data_fim_str


def _periodo_label(filtro, ano, mes, bimestre, semestre, data_ini_str="", data_fim_str=""):
    if filtro == "mes":      return f"{MESES_NOMES[mes]}/{ano}"
    if filtro == "bimestre": return f"{bimestre}º Bimestre/{ano}"
    if filtro == "semestre": return f"{semestre}º Semestre/{ano}"
    if filtro == "custom" and data_ini_str and data_fim_str:
        return f"{data_ini_str} a {data_fim_str}"
    return f"Ano {ano}"


def _meses_do_periodo(filtro, valor, ano, mes):
    """Retorna lista de (ano, mes) a serem exibidos no calendário."""
    if filtro == "mes":
        return [(ano, mes)]
    elif filtro == "bimestre":
        m1, m2 = BIMESTRES.get(valor, (1, 3))
        return [(ano, m) for m in range(m1, m2 + 1)]
    elif filtro == "semestre":
        m1, m2 = SEMESTRES.get(valor, (1, 6))
        return [(ano, m) for m in range(m1, m2 + 1)]
    else:  # ano
        return [(ano, m) for m in range(1, 13)]


# ── rotas ─────────────────────────────────────────────────────────────────────

@freq_bp.route("/")
@login_required
def index():
    hoje   = date.today()
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    turmas_json = [{
        "id": t.id, "nome": t.nome,
        "alunos": [{"id": a.id, "nome": a.nome} for a in sorted(t.alunos, key=lambda x: x.nome)]
    } for t in turmas]
    return render_template("frequencia/index.html",
        turmas=turmas, turmas_json=turmas_json, hoje=hoje)


@freq_bp.route("/registrar/<int:turma_id>", methods=["GET", "POST"])
@login_required
def registrar(turma_id):
    turma  = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()
    hoje   = date.today()
    if request.method == "POST":
        data_str  = request.form.get("data")
        try:    data_aula = datetime.strptime(data_str, "%Y-%m-%d").date()
        except: data_aula = hoje
        for aluno in alunos:
            status = request.form.get(f"status_{aluno.id}", "presente")
            obs    = request.form.get(f"obs_{aluno.id}", "")
            freq   = Frequencia.query.filter_by(aluno_id=aluno.id, data=data_aula).first()
            if freq:
                freq.status = status; freq.observacao = obs
            else:
                db.session.add(Frequencia(
                    data=data_aula, status=status, observacao=obs,
                    aluno_id=aluno.id, turma_id=turma_id, professor_id=current_user.id))
        db.session.commit()
        flash("Frequência registrada!", "success")
        return redirect(url_for("frequencia.registrar", turma_id=turma_id))
    freq_hoje = {f.aluno_id: f for f in Frequencia.query.filter_by(turma_id=turma_id, data=hoje).all()}
    return render_template("frequencia/registrar.html",
        turma=turma, alunos=alunos, hoje=hoje, freq_hoje=freq_hoje)


@freq_bp.route("/historico/<int:turma_id>")
@login_required
def historico(turma_id):
    turma  = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()
    filtro, ano, mes, bimestre, semestre, valor, data_ini, data_fim, data_ini_str, data_fim_str = _get_filtros()
    stats       = calcular_stats_turma(turma_id, filtro, valor, ano, data_ini, data_fim)
    q           = Frequencia.query.filter_by(turma_id=turma_id)
    frequencias = _aplicar_filtro(q, filtro, valor, ano, data_ini, data_fim).order_by(Frequencia.data.desc()).all()
    return render_template("frequencia/historico.html",
        turma=turma, alunos=alunos, stats=stats,
        filtro=filtro, ano=ano, mes=mes, bimestre=bimestre, semestre=semestre,
        data_ini=data_ini_str, data_fim=data_fim_str)


@freq_bp.route("/relatorio/<int:turma_id>")
@login_required
def relatorio(turma_id):
    turma  = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()
    filtro, ano, mes, bimestre, semestre, valor, data_ini, data_fim, data_ini_str, data_fim_str = _get_filtros()
    aluno_id   = request.args.get("aluno_id", type=int)
    alunos_rel = [a for a in alunos if a.id == aluno_id] if aluno_id else alunos
    stats      = {a.id: calcular_stats_aluno(a.id, filtro, valor, ano, data_ini, data_fim) for a in alunos_rel}
    q          = Frequencia.query.filter_by(turma_id=turma_id)
    q          = _aplicar_filtro(q, filtro, valor, ano, data_ini, data_fim)
    if aluno_id:
        q = q.filter_by(aluno_id=aluno_id)
    freq_por_aluno = defaultdict(list)
    for f in q.order_by(Frequencia.data).all():
        freq_por_aluno[f.aluno_id].append(f)
    label = _periodo_label(filtro, ano, mes, bimestre, semestre)
    if filtro == "custom":
        label = f"{data_ini_str} a {data_fim_str}" if data_ini_str and data_fim_str else label
    return render_template("frequencia/relatorio.html",
        turma=turma, alunos=alunos_rel, alunos_todos=alunos,
        stats=stats, freq_por_aluno=freq_por_aluno,
        periodo_label=label, aluno_id=aluno_id,
        filtro=filtro, ano=ano, mes=mes, bimestre=bimestre, semestre=semestre,
        data_ini=data_ini_str, data_fim=data_fim_str)


# ── PDF resumo (barras) ───────────────────────────────────────────────────────

@freq_bp.route("/relatorio/<int:turma_id>/pdf")
@login_required
def relatorio_pdf(turma_id):
    turma  = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()
    filtro, ano, mes, bimestre, semestre, valor, data_ini, data_fim, data_ini_str, data_fim_str = _get_filtros()
    aluno_id   = request.args.get("aluno_id", type=int)
    alunos_rel = [a for a in alunos if a.id == aluno_id] if aluno_id else alunos
    stats      = {a.id: calcular_stats_aluno(a.id, filtro, valor, ano, data_ini, data_fim) for a in alunos_rel}
    q          = Frequencia.query.filter_by(turma_id=turma_id)
    q          = _aplicar_filtro(q, filtro, valor, ano, data_ini, data_fim)
    if aluno_id:
        q = q.filter_by(aluno_id=aluno_id)
    freq_por_aluno = defaultdict(list)
    for f in q.order_by(Frequencia.data).all():
        freq_por_aluno[f.aluno_id].append(f)
    label  = _periodo_label(filtro, ano, mes, bimestre, semestre)
    buf    = _pdf_resumo(turma, alunos_rel, stats, freq_por_aluno, label, current_user.nome, current_user.escola or "")
    nome   = f"Frequencia_{turma.nome.replace(' ','_')}_{label.replace('/','_')}.pdf"
    return send_file(buf, as_attachment=True, download_name=nome, mimetype="application/pdf")


# ── PDF calendário (por aluno) ────────────────────────────────────────────────

@freq_bp.route("/relatorio/<int:turma_id>/calendario")
@login_required
def relatorio_calendario(turma_id):
    turma  = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()
    filtro, ano, mes, bimestre, semestre, valor, data_ini, data_fim, data_ini_str, data_fim_str = _get_filtros()
    aluno_id   = request.args.get("aluno_id", type=int)
    alunos_rel = [a for a in alunos if a.id == aluno_id] if aluno_id else alunos

    # Buscar todos os registros do período
    q = Frequencia.query.filter_by(turma_id=turma_id)
    q = _aplicar_filtro(q, filtro, valor, ano, data_ini, data_fim)
    if aluno_id:
        q = q.filter_by(aluno_id=aluno_id)
    freq_por_aluno = defaultdict(dict)   # {aluno_id: {date: status}}
    for f in q.all():
        freq_por_aluno[f.aluno_id][f.data] = f.status

    stats  = {a.id: calcular_stats_aluno(a.id, filtro, valor, ano, data_ini, data_fim) for a in alunos_rel}
    meses  = _meses_do_periodo(filtro, valor, ano, mes)
    label  = _periodo_label(filtro, ano, mes, bimestre, semestre)

    buf  = _pdf_calendario(alunos_rel, freq_por_aluno, stats, meses, label, turma, current_user.nome, current_user.escola or "")
    nome = f"Calendario_Freq_{turma.nome.replace(' ','_')}_{label.replace('/','_')}.pdf"
    return send_file(buf, as_attachment=True, download_name=nome, mimetype="application/pdf")


# ── PDF resumo com barras ─────────────────────────────────────────────────────

def _pdf_resumo(turma, alunos, stats, freq_por_aluno, periodo_label, prof_nome="", escola=""):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, HRFlowable)
    from reportlab.graphics.shapes import Drawing, Rect, String as RLString
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    NAVY  = colors.HexColor("#1a3a5c")
    SAGE  = colors.HexColor("#4d7c5f")
    ROSE  = colors.HexColor("#e05c5c")
    AMBER = colors.HexColor("#f59e0b")
    LIGHT = colors.HexColor("#f3f4f6")
    CINZA = colors.HexColor("#6b7280")
    SS    = getSampleStyleSheet()

    T_h1  = ParagraphStyle("h1", parent=SS["Title"], fontSize=14, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2)
    T_sub = ParagraphStyle("sub", parent=SS["Normal"], fontSize=9, textColor=CINZA, alignment=TA_CENTER, spaceAfter=8)
    T_bold= ParagraphStyle("bold", parent=SS["Normal"], fontSize=9, fontName="Helvetica-Bold")
    T_body= ParagraphStyle("body", parent=SS["Normal"], fontSize=8, leading=11)

    story = []
    cabecalho_pdf(story, prof_nome, escola, "Relatório de Frequência")
    story.append(Paragraph("Resumo de Frequência", T_h1))
    story.append(Paragraph(f"{turma.nome}  ·  Período: {periodo_label}", T_sub))
    story.append(Spacer(1, 4))

    # ── Tabela com mini-barras ────────────────────────────────────────────────
    BAR_W = 100  # pontos
    header = ["Aluno", "Pres.", "Falt.", "% Frequência"]
    rows   = [header]
    bar_data = []

    for a in alunos:
        total, presentes, faltas, pct = stats.get(a.id, (0,0,0,None))
        bar_data.append((a.nome, presentes, faltas, pct, total))
        pct_txt = f"{pct}%" if pct is not None else "—"
        rows.append([a.nome, str(presentes), str(faltas), pct_txt])

    # Coluna de barras (Drawing inline)
    # Vamos usar uma tabela de 5 cols onde a última é a barra visual
    header2 = ["Aluno", "Reg.", "Pres.", "Falt.", "Frequência (barra)"]
    rows2   = [header2]
    for nm, pres, falt, pct, tot in bar_data:
        rows2.append([nm, str(tot), str(pres), str(falt),
                      _make_bar(pct, BAR_W)])

    tbl = Table(rows2, colWidths=[7.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 6.5*cm], repeatRows=1)
    ts  = TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ALIGN",         (1,0), (3,-1), "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, LIGHT]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#e5e7eb")),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ])
    for i, (nm, pres, falt, pct, tot) in enumerate(bar_data, 1):
        if pct is not None:
            cor = SAGE if pct >= 75 else (AMBER if pct >= 50 else ROSE)
            ts.add("TEXTCOLOR", (0,i),(0,i), NAVY)
    tbl.setStyle(ts)
    story.append(tbl)
    story.append(Spacer(1, 16))

    # ── Detalhe por aluno ─────────────────────────────────────────────────────
    for a in alunos:
        registros = freq_por_aluno.get(a.id, [])
        if not registros:
            continue
        total, presentes, faltas, pct = stats.get(a.id, (0,0,0,None))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
        story.append(Spacer(1,4))
        story.append(Paragraph(
            f"<b>{a.nome}</b>  —  {presentes}/{total} dias  ({pct or '—'}%)", T_bold))
        story.append(Spacer(1,4))
        det = [["Data","Status","Observação"]]
        for f in sorted(registros, key=lambda x: x.data):
            lbl = {"presente":"Presente","ausente":"Ausente","atestado":"Atestado",
                   "afastamento":"Afastamento"}.get(f.status, f.status)
            det.append([f.data.strftime("%d/%m/%Y"), lbl, f.observacao or ""])
        dt = Table(det, colWidths=[3*cm, 3.5*cm, 12.5*cm], repeatRows=1)
        ds = TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), colors.HexColor("#f0f6ff")),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 8),
            ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#e5e7eb")),
            ("ALIGN",         (0,0),(1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 3),
            ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ])
        for i, f in enumerate(sorted(registros, key=lambda x: x.data), 1):
            cor = ROSE if f.status=="ausente" else (AMBER if f.status in ("atestado","afastamento") else SAGE)
            ds.add("TEXTCOLOR",(1,i),(1,i), cor)
            ds.add("FONTNAME", (1,i),(1,i),"Helvetica-Bold")
        dt.setStyle(ds)
        story.append(dt)
        story.append(Spacer(1,10))

    doc.build(story)
    buf.seek(0)
    return buf


def _make_bar(pct, width):
    """Retorna um Drawing com barra de progresso para usar em célula de tabela."""
    from reportlab.graphics.shapes import Drawing, Rect, String as S
    from reportlab.lib import colors
    SAGE  = colors.HexColor("#4d7c5f")
    AMBER = colors.HexColor("#f59e0b")
    ROSE  = colors.HexColor("#e05c5c")
    GRAY  = colors.HexColor("#e5e7eb")

    h = 12
    d = Drawing(width + 45, h + 2)
    # fundo
    d.add(Rect(0, 1, width, h, fillColor=GRAY, strokeColor=None))
    if pct is not None:
        cor = SAGE if pct >= 75 else (AMBER if pct >= 50 else ROSE)
        fill_w = max(2, width * pct / 100)
        d.add(Rect(0, 1, fill_w, h, fillColor=cor, strokeColor=None))
        # texto percentual
        txt = f"{pct}%"
        d.add(S(width + 4, 2, txt, fontSize=8,
                fillColor=cor, fontName="Helvetica-Bold"))
    else:
        d.add(S(width + 4, 2, "—", fontSize=8,
                fillColor=GRAY, fontName="Helvetica"))
    return d


# ── PDF calendário visual por aluno ──────────────────────────────────────────

def _pdf_calendario(alunos, freq_por_aluno, stats, meses, periodo_label, turma, prof_nome="", escola=""):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, PageBreak, HRFlowable)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.2*cm, rightMargin=1.2*cm,
                            topMargin=1.2*cm, bottomMargin=1.2*cm)

    NAVY  = colors.HexColor("#1a3a5c")
    SAGE  = colors.HexColor("#4d7c5f")
    SAGE_L= colors.HexColor("#d1fae5")
    ROSE  = colors.HexColor("#e05c5c")
    ROSE_L= colors.HexColor("#fee2e2")
    AMBER = colors.HexColor("#f59e0b")
    AMB_L = colors.HexColor("#fef3c7")
    BLUE_L= colors.HexColor("#dbeafe")
    CINZA = colors.HexColor("#9ca3af")
    LIGHT = colors.HexColor("#f9fafb")
    WHITE = colors.white
    GRAY  = colors.HexColor("#e5e7eb")

    SS   = getSampleStyleSheet()
    T_h1 = ParagraphStyle("h1", parent=SS["Title"], fontSize=13, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2)
    T_sub= ParagraphStyle("sub", parent=SS["Normal"], fontSize=8, textColor=CINZA, alignment=TA_CENTER, spaceAfter=6)
    T_mes= ParagraphStyle("mes", parent=SS["Normal"], fontSize=11, fontName="Helvetica-Bold", textColor=NAVY, alignment=TA_CENTER)
    T_day= ParagraphStyle("day", parent=SS["Normal"], fontSize=7, textColor=CINZA)
    T_leg= ParagraphStyle("leg", parent=SS["Normal"], fontSize=7, textColor=colors.black)

    # Dias da semana em PT (começando segunda-feira)
    CAB   = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    CAB_P = [Paragraph(f"<b>{d}</b>", ParagraphStyle("dc", parent=T_day, alignment=TA_CENTER, textColor=NAVY)) for d in CAB]

    # Legenda de cores
    def legenda():
        leg_data = [["■ Presente","■ Ausente","■ Atestado/Afastamento","□ Sem registro"]]
        lt = Table(leg_data, colWidths=[3.5*cm]*4)
        lt.setStyle(TableStyle([
            ("FONTSIZE",  (0,0),(-1,-1), 7),
            ("TEXTCOLOR", (0,0),(0,0), SAGE),
            ("TEXTCOLOR", (1,0),(1,0), ROSE),
            ("TEXTCOLOR", (2,0),(2,0), AMBER),
            ("TEXTCOLOR", (3,0),(3,0), CINZA),
            ("FONTNAME",  (0,0),(-1,-1), "Helvetica-Bold"),
            ("ALIGN",     (0,0),(-1,-1), "CENTER"),
        ]))
        return lt

    CELL_H = 1.5*cm   # altura de cada linha de semana
    CELL_W = 3.85*cm  # largura de cada coluna de dia (landscape A4 ≈ 27cm útil / 7)

    story = []
    cabecalho_pdf(story, prof_nome, escola, "Calendário de Frequência")

    for aluno in alunos:
        total, presentes, faltas, pct = stats.get(aluno.id, (0, 0, 0, None))
        freq_map = freq_por_aluno.get(aluno.id, {})

        story.append(Paragraph(f"Calendário de Frequência — {aluno.nome}", T_h1))
        story.append(Paragraph(
            f"{turma.nome}  ·  {periodo_label}  ·  "
            f"Presentes: {presentes}  Faltas: {faltas}  "
            f"Frequência: {pct}%" if pct is not None else
            f"{turma.nome}  ·  {periodo_label}", T_sub))
        story.append(legenda())
        story.append(Spacer(1, 8))

        for (ano_c, mes_c) in meses:
            story.append(Paragraph(f"{MESES_NOMES[mes_c]} {ano_c}", T_mes))
            story.append(Spacer(1, 4))

            # Calendário do mês (segunda-feira = 0)
            cal = calendar.monthcalendar(ano_c, mes_c)

            # Cabeçalho dos dias da semana
            cab_row = [CAB_P]
            tbl_data = [CAB_P]

            for semana in cal:
                row = []
                for dia in semana:
                    if dia == 0:
                        row.append(Paragraph("", T_day))
                    else:
                        d = date(ano_c, mes_c, dia)
                        status = freq_map.get(d)
                        num_p = Paragraph(f"<b>{dia}</b>", ParagraphStyle(
                            "dn", parent=T_day, alignment=TA_LEFT,
                            textColor=colors.black if status else CINZA,
                        ))
                        if status:
                            sts_map = {"presente":"✅ Pres.","ausente":"❌ Aus.",
                                       "atestado":"📄 Ates.","afastamento":"🔵 Afas."}
                            sts_p = Paragraph(sts_map.get(status, status),
                                              ParagraphStyle("st", parent=T_day, fontSize=6,
                                                             textColor=colors.black))
                            row.append([num_p, sts_p])
                        else:
                            row.append(num_p)
                tbl_data.append(row)

            tbl = Table(tbl_data,
                        colWidths=[CELL_W]*7,
                        rowHeights=[0.55*cm] + [CELL_H]*len(cal))

            ts = TableStyle([
                # Cabeçalho
                ("BACKGROUND",  (0,0),(6,0), NAVY),
                ("TEXTCOLOR",   (0,0),(6,0), WHITE),
                ("FONTNAME",    (0,0),(6,0), "Helvetica-Bold"),
                ("ALIGN",       (0,0),(6,0), "CENTER"),
                ("VALIGN",      (0,0),(-1,-1), "TOP"),
                ("TOPPADDING",  (0,0),(-1,-1), 3),
                ("LEFTPADDING", (0,0),(-1,-1), 4),
                ("BOTTOMPADDING",(0,0),(-1,-1), 2),
                ("GRID",        (0,0),(-1,-1), 0.5, GRAY),
                ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT]),
            ])

            # Colorir células com status
            for ri, semana in enumerate(cal, 1):
                for ci, dia in enumerate(semana):
                    if dia == 0:
                        ts.add("BACKGROUND", (ci,ri),(ci,ri), LIGHT)
                        continue
                    d = date(ano_c, mes_c, dia)
                    status = freq_map.get(d)
                    if status == "presente":
                        ts.add("BACKGROUND", (ci,ri),(ci,ri), SAGE_L)
                    elif status == "ausente":
                        ts.add("BACKGROUND", (ci,ri),(ci,ri), ROSE_L)
                    elif status in ("atestado","afastamento"):
                        ts.add("BACKGROUND", (ci,ri),(ci,ri), AMB_L)
                    # final de semana (sáb=5, dom=6) cinza claro
                    if ci >= 5 and status is None:
                        ts.add("BACKGROUND", (ci,ri),(ci,ri), colors.HexColor("#f3f4f6"))

            tbl.setStyle(ts)
            story.append(tbl)
            story.append(Spacer(1, 10))

        story.append(HRFlowable(width="100%", thickness=1, color=GRAY))
        story.append(Spacer(1, 6))

        if aluno != alunos[-1]:
            story.append(PageBreak())

    doc.build(story)
    buf.seek(0)
    return buf


# ── API: dados do mês para o calendário ───────────────────────────────────────

@freq_bp.route("/api/mes")
@login_required
def api_mes():
    """Retorna registros de frequência do mês como JSON {YYYY-MM-DD: [{aluno_id, aluno_nome, status}]}."""
    hoje     = date.today()
    ano      = request.args.get("ano",  hoje.year,  type=int)
    mes      = request.args.get("mes",  hoje.month, type=int)
    turma_id = request.args.get("turma_id", type=int)

    q = Frequencia.query.join(Aluno).filter(
        Frequencia.professor_id == current_user.id,
        db.extract("year",  Frequencia.data) == ano,
        db.extract("month", Frequencia.data) == mes,
    )
    if turma_id:
        q = q.filter(Aluno.turma_id == turma_id)

    resultado = {}
    for f in q.all():
        k = f.data.strftime("%Y-%m-%d")
        if k not in resultado:
            resultado[k] = []
        resultado[k].append({
            "aluno_id":   f.aluno_id,
            "aluno_nome": f.aluno.nome,
            "status":     f.status,
        })
    return jsonify(resultado)


# ── API: registrar frequência do dia (JSON) ───────────────────────────────────

@freq_bp.route("/api/registrar", methods=["POST"])
@login_required
def api_registrar():
    """Salva ou atualiza frequência de um dia inteiro via JSON."""
    dados    = request.get_json()
    data_str = dados.get("data", "")
    turma_id = dados.get("turma_id")
    registros= dados.get("registros", {})  # {aluno_id: status}

    try:
        data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "erro": "Data inválida"}), 400

    # Remover registros existentes do dia+turma+professor
    alunos_ids = [int(k) for k in registros.keys()]
    Frequencia.query.filter(
        Frequencia.professor_id == current_user.id,
        Frequencia.data         == data_obj,
        Frequencia.aluno_id.in_(alunos_ids),
    ).delete(synchronize_session=False)
    db.session.flush()

    # Inserir novos
    for aluno_id_str, status in registros.items():
        db.session.add(Frequencia(
            aluno_id=int(aluno_id_str), turma_id=turma_id,
            professor_id=current_user.id, data=data_obj, status=status,
        ))
    db.session.commit()
    return jsonify({"ok": True})


# ── Preview relatório de frequência (web, imprimível) ─────────────────────────

@freq_bp.route("/relatorio-preview")
@login_required
def relatorio_preview():
    from datetime import timedelta
    hoje     = date.today()
    tipo     = request.args.get("tipo", "mes")
    turma_id = request.args.get("turma_id", type=int)
    turmas   = Turma.query.filter_by(professor_id=current_user.id).all()
    alunos   = []
    for t in turmas:
        if not turma_id or t.id == turma_id:
            alunos.extend(sorted(t.alunos, key=lambda a: a.nome))

    # Definir range de datas
    if tipo == "mes":
        ano   = request.args.get("ano", hoje.year, type=int)
        meses = [int(m) for m in request.args.get("meses", str(hoje.month)).split(",") if m]
        datas = []
        for m in meses:
            import calendar as cal_mod
            last = cal_mod.monthrange(ano, m)[1]
            datas.append((date(ano, m, 1), date(ano, m, last)))
        label = f"{', '.join([['','Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][m] for m in meses])}/{ano}"
    elif tipo == "ano":
        ano   = request.args.get("ano", hoje.year, type=int)
        datas = [(date(ano, 1, 1), date(ano, 12, 31))]
        label = f"Ano Letivo {ano}"
    else:
        data_ini = datetime.strptime(request.args.get("data_ini", hoje.replace(day=1).isoformat()), "%Y-%m-%d").date()
        data_fim = datetime.strptime(request.args.get("data_fim", hoje.isoformat()), "%Y-%m-%d").date()
        datas = [(data_ini, data_fim)]
        label = f"{data_ini.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"

    # Calcular stats por aluno no período combinado
    stats   = {}
    detalhes= {}
    for aluno in alunos:
        total = presentes = faltas = 0
        regs  = []
        for (di, df) in datas:
            q = Frequencia.query.filter(
                Frequencia.aluno_id == aluno.id,
                Frequencia.data >= di, Frequencia.data <= df,
            ).order_by(Frequencia.data).all()
            regs.extend(q)
            total    += len(q)
            presentes+= sum(1 for r in q if r.status=="presente")
            faltas   += sum(1 for r in q if r.status!="presente")
        pct = round(presentes/total*100, 1) if total else None
        stats[aluno.id]    = (total, presentes, faltas, pct)
        detalhes[aluno.id] = regs

    turma_nome = next((t.nome for t in turmas if t.id==turma_id), "Todas as turmas") if turma_id else "Todas as turmas"

    return render_template("frequencia/relatorio_preview.html",
        alunos=alunos, stats=stats, detalhes=detalhes,
        label=label, turma_nome=turma_nome,
        prof_nome=current_user.nome, escola=current_user.escola or "",
        tipo=tipo, turma_id=turma_id,
        request_args=request.args.to_dict(),
    )
