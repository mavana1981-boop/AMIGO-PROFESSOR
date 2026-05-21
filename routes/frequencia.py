from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db
from models.models import Turma, Aluno, Frequencia
from datetime import date, datetime
from collections import defaultdict
import io

freq_bp = Blueprint("frequencia", __name__, url_prefix="/frequencia")

# ── Helpers ───────────────────────────────────────────────────────────────────

BIMESTRES = {
    1: (1, 3),   # Jan-Mar
    2: (4, 6),   # Abr-Jun
    3: (7, 9),   # Jul-Set
    4: (10, 12), # Out-Dez
}

SEMESTRES = {
    1: (1, 6),
    2: (7, 12),
}


def calcular_stats_aluno(aluno_id, filtro, valor, ano):
    """Retorna (total, presentes, percentual) para um aluno no período."""
    query = Frequencia.query.filter_by(aluno_id=aluno_id)
    query = query.filter(db.extract("year", Frequencia.data) == ano)

    if filtro == "mes":
        query = query.filter(db.extract("month", Frequencia.data) == valor)
    elif filtro == "bimestre":
        m_ini, m_fim = BIMESTRES.get(valor, (1, 3))
        query = query.filter(
            db.extract("month", Frequencia.data) >= m_ini,
            db.extract("month", Frequencia.data) <= m_fim,
        )
    elif filtro == "semestre":
        m_ini, m_fim = SEMESTRES.get(valor, (1, 6))
        query = query.filter(
            db.extract("month", Frequencia.data) >= m_ini,
            db.extract("month", Frequencia.data) <= m_fim,
        )
    # "ano" = sem filtro de mês

    registros = query.all()
    total    = len(registros)
    presentes = sum(1 for r in registros if r.status == "presente")
    pct = round((presentes / total * 100), 1) if total > 0 else None
    faltas = total - presentes
    return total, presentes, faltas, pct


def calcular_stats_turma(turma_id, filtro, valor, ano):
    """Retorna dict {aluno_id: (total, presentes, faltas, pct)} para toda a turma."""
    alunos = Aluno.query.filter_by(turma_id=turma_id).all()
    result = {}
    for a in alunos:
        result[a.id] = calcular_stats_aluno(a.id, filtro, valor, ano)
    return result


# ── Rotas ─────────────────────────────────────────────────────────────────────

@freq_bp.route("/")
@login_required
def index():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    return render_template("frequencia/index.html", turmas=turmas)


@freq_bp.route("/registrar/<int:turma_id>", methods=["GET", "POST"])
@login_required
def registrar(turma_id):
    turma  = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()
    hoje   = date.today()

    if request.method == "POST":
        data_str = request.form.get("data")
        try:
            data_aula = datetime.strptime(data_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            data_aula = hoje

        for aluno in alunos:
            status = request.form.get(f"status_{aluno.id}", "presente")
            obs    = request.form.get(f"obs_{aluno.id}", "")
            freq_existente = Frequencia.query.filter_by(aluno_id=aluno.id, data=data_aula).first()
            if freq_existente:
                freq_existente.status = status
                freq_existente.observacao = obs
            else:
                db.session.add(Frequencia(
                    data=data_aula, status=status, observacao=obs,
                    aluno_id=aluno.id, turma_id=turma_id, professor_id=current_user.id,
                ))
        db.session.commit()
        flash("Frequência registrada com sucesso!", "success")
        return redirect(url_for("frequencia.registrar", turma_id=turma_id))

    freq_hoje = {f.aluno_id: f for f in Frequencia.query.filter_by(turma_id=turma_id, data=hoje).all()}
    return render_template("frequencia/registrar.html", turma=turma, alunos=alunos, hoje=hoje, freq_hoje=freq_hoje)


@freq_bp.route("/historico/<int:turma_id>")
@login_required
def historico(turma_id):
    turma  = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()
    hoje   = date.today()

    # Filtros
    filtro   = request.args.get("filtro", "mes")
    ano      = request.args.get("ano", hoje.year, type=int)
    mes      = request.args.get("mes", hoje.month, type=int)
    bimestre = request.args.get("bimestre", 1, type=int)
    semestre = request.args.get("semestre", 1, type=int)

    valor = {"mes": mes, "bimestre": bimestre, "semestre": semestre, "ano": ano}.get(filtro, mes)

    # Stats por aluno
    stats = calcular_stats_turma(turma_id, filtro, valor, ano)

    # Registros detalhados para tabela
    query = Frequencia.query.filter_by(turma_id=turma_id)
    query = query.filter(db.extract("year", Frequencia.data) == ano)
    if filtro == "mes":
        query = query.filter(db.extract("month", Frequencia.data) == mes)
    elif filtro == "bimestre":
        m_ini, m_fim = BIMESTRES.get(bimestre, (1, 3))
        query = query.filter(db.extract("month", Frequencia.data) >= m_ini,
                             db.extract("month", Frequencia.data) <= m_fim)
    elif filtro == "semestre":
        m_ini, m_fim = SEMESTRES.get(semestre, (1, 6))
        query = query.filter(db.extract("month", Frequencia.data) >= m_ini,
                             db.extract("month", Frequencia.data) <= m_fim)
    frequencias = query.order_by(Frequencia.data.desc()).all()

    return render_template("frequencia/historico.html",
        turma=turma, alunos=alunos, frequencias=frequencias, stats=stats,
        filtro=filtro, ano=ano, mes=mes, bimestre=bimestre, semestre=semestre,
        hoje=hoje,
    )


@freq_bp.route("/relatorio/<int:turma_id>")
@login_required
def relatorio(turma_id):
    turma  = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()
    hoje   = date.today()

    filtro    = request.args.get("filtro", "mes")
    ano       = request.args.get("ano", hoje.year, type=int)
    mes       = request.args.get("mes", hoje.month, type=int)
    bimestre  = request.args.get("bimestre", 1, type=int)
    semestre  = request.args.get("semestre", 1, type=int)
    aluno_id  = request.args.get("aluno_id", type=int)

    valor = {"mes": mes, "bimestre": bimestre, "semestre": semestre, "ano": ano}.get(filtro, mes)

    if aluno_id:
        alunos_rel = [a for a in alunos if a.id == aluno_id]
    else:
        alunos_rel = alunos

    stats = {a.id: calcular_stats_aluno(a.id, filtro, valor, ano) for a in alunos_rel}

    # Registros detalhados
    query = Frequencia.query.filter_by(turma_id=turma_id)
    query = query.filter(db.extract("year", Frequencia.data) == ano)
    if filtro == "mes":
        query = query.filter(db.extract("month", Frequencia.data) == mes)
    elif filtro == "bimestre":
        m_ini, m_fim = BIMESTRES.get(bimestre, (1, 3))
        query = query.filter(db.extract("month", Frequencia.data) >= m_ini,
                             db.extract("month", Frequencia.data) <= m_fim)
    elif filtro == "semestre":
        m_ini, m_fim = SEMESTRES.get(semestre, (1, 6))
        query = query.filter(db.extract("month", Frequencia.data) >= m_ini,
                             db.extract("month", Frequencia.data) <= m_fim)
    if aluno_id:
        query = query.filter_by(aluno_id=aluno_id)

    frequencias = query.order_by(Frequencia.data).all()

    # Agrupa por aluno
    freq_por_aluno = defaultdict(list)
    for f in frequencias:
        freq_por_aluno[f.aluno_id].append(f)

    # Labels de período
    meses_nomes = ['','Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                   'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    if filtro == "mes":
        periodo_label = f"{meses_nomes[mes]}/{ano}"
    elif filtro == "bimestre":
        periodo_label = f"{bimestre}º Bimestre/{ano}"
    elif filtro == "semestre":
        periodo_label = f"{semestre}º Semestre/{ano}"
    else:
        periodo_label = f"Ano {ano}"

    return render_template("frequencia/relatorio.html",
        turma=turma, alunos=alunos_rel, stats=stats,
        freq_por_aluno=freq_por_aluno, periodo_label=periodo_label,
        filtro=filtro, ano=ano, mes=mes, bimestre=bimestre, semestre=semestre,
        aluno_id=aluno_id, alunos_todos=alunos,
        hoje=hoje,
    )


@freq_bp.route("/relatorio/<int:turma_id>/pdf")
@login_required
def relatorio_pdf(turma_id):
    turma  = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()
    hoje   = date.today()

    filtro   = request.args.get("filtro", "mes")
    ano      = request.args.get("ano", hoje.year, type=int)
    mes      = request.args.get("mes", hoje.month, type=int)
    bimestre = request.args.get("bimestre", 1, type=int)
    semestre = request.args.get("semestre", 1, type=int)
    aluno_id = request.args.get("aluno_id", type=int)

    valor = {"mes": mes, "bimestre": bimestre, "semestre": semestre, "ano": ano}.get(filtro, mes)

    if aluno_id:
        alunos_rel = [a for a in alunos if a.id == aluno_id]
    else:
        alunos_rel = alunos

    stats = {a.id: calcular_stats_aluno(a.id, filtro, valor, ano) for a in alunos_rel}

    query = Frequencia.query.filter_by(turma_id=turma_id)
    query = query.filter(db.extract("year", Frequencia.data) == ano)
    if filtro == "mes":
        query = query.filter(db.extract("month", Frequencia.data) == mes)
    elif filtro == "bimestre":
        m_ini, m_fim = BIMESTRES.get(bimestre, (1, 3))
        query = query.filter(db.extract("month", Frequencia.data) >= m_ini,
                             db.extract("month", Frequencia.data) <= m_fim)
    elif filtro == "semestre":
        m_ini, m_fim = SEMESTRES.get(semestre, (1, 6))
        query = query.filter(db.extract("month", Frequencia.data) >= m_ini,
                             db.extract("month", Frequencia.data) <= m_fim)
    if aluno_id:
        query = query.filter_by(aluno_id=aluno_id)

    frequencias = query.order_by(Frequencia.data).all()
    freq_por_aluno = defaultdict(list)
    for f in frequencias:
        freq_por_aluno[f.aluno_id].append(f)

    meses_nomes = ['','Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                   'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    if filtro == "mes":
        periodo_label = f"{meses_nomes[mes]}/{ano}"
    elif filtro == "bimestre":
        periodo_label = f"{bimestre}º Bimestre/{ano}"
    elif filtro == "semestre":
        periodo_label = f"{semestre}º Semestre/{ano}"
    else:
        periodo_label = f"Ano {ano}"

    buf = gerar_pdf_relatorio(turma, alunos_rel, stats, freq_por_aluno, periodo_label)
    nome = f"Frequencia_{turma.nome.replace(' ','_')}_{periodo_label.replace('/','_')}.pdf"
    return send_file(buf, as_attachment=True, download_name=nome, mimetype="application/pdf")


def gerar_pdf_relatorio(turma, alunos, stats, freq_por_aluno, periodo_label):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    NAVY  = colors.HexColor("#1a3a5c")
    AMBER = colors.HexColor("#f59e0b")
    SAGE  = colors.HexColor("#4d7c5f")
    ROSE  = colors.HexColor("#e05c5c")
    CINZA = colors.HexColor("#6b7280")
    LIGHT = colors.HexColor("#f3f4f6")

    SS = getSampleStyleSheet()
    T_titulo = ParagraphStyle("titulo", parent=SS["Title"], fontSize=14,
                               textColor=NAVY, alignment=TA_CENTER, spaceAfter=4)
    T_sub = ParagraphStyle("sub", parent=SS["Normal"], fontSize=10,
                            textColor=CINZA, alignment=TA_CENTER, spaceAfter=12)
    T_normal = ParagraphStyle("normal", parent=SS["Normal"], fontSize=9,
                               textColor=colors.black, leading=13)
    T_bold = ParagraphStyle("bold", parent=SS["Normal"], fontSize=9,
                             fontName="Helvetica-Bold", leading=13)

    story = []
    story.append(Paragraph("Relatório de Frequência", T_titulo))
    story.append(Paragraph(f"{turma.nome}  ·  Período: {periodo_label}  ·  Gerado em {date.today().strftime('%d/%m/%Y')}", T_sub))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY))
    story.append(Spacer(1, 10))

    # ── Tabela resumo ─────────────────────────────────────────────────────────
    resumo_data = [["Aluno", "Total dias", "Presentes", "Faltas/Atestados", "% Frequência"]]
    for aluno in alunos:
        total, presentes, faltas, pct = stats.get(aluno.id, (0, 0, 0, None))
        pct_txt = f"{pct}%" if pct is not None else "—"
        resumo_data.append([
            aluno.nome,
            str(total),
            str(presentes),
            str(faltas),
            pct_txt,
        ])

    col_w = [9*cm, 2*cm, 2.5*cm, 3.5*cm, 3*cm]
    tbl = Table(resumo_data, colWidths=col_w, repeatRows=1)
    tbl_style = TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 9),
        ("ALIGN",        (1,0), (-1,-1), "CENTER"),
        ("ALIGN",        (0,0), (0,-1), "LEFT"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, LIGHT]),
        ("GRID",         (0,0), (-1,-1), 0.4, colors.HexColor("#e5e7eb")),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
    ])
    # Colorir % por faixa
    for i, aluno in enumerate(alunos, start=1):
        _, _, _, pct = stats.get(aluno.id, (0,0,0,None))
        if pct is not None:
            cor = SAGE if pct >= 75 else ROSE
            tbl_style.add("TEXTCOLOR", (4, i), (4, i), cor)
            tbl_style.add("FONTNAME",  (4, i), (4, i), "Helvetica-Bold")
    tbl.setStyle(tbl_style)
    story.append(tbl)
    story.append(Spacer(1, 16))

    # ── Detalhe por aluno ─────────────────────────────────────────────────────
    for aluno in alunos:
        registros = freq_por_aluno.get(aluno.id, [])
        if not registros:
            continue
        total, presentes, faltas, pct = stats.get(aluno.id, (0,0,0,None))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>{aluno.nome}</b>  —  {presentes}/{total} dias presentes  ({pct or '—'}%)", T_bold))
        story.append(Spacer(1, 4))

        det_data = [["Data", "Status", "Observação"]]
        for f in sorted(registros, key=lambda x: x.data):
            status_txt = {"presente":"Presente","ausente":"Ausente","atestado":"Atestado","afastamento":"Afastamento"}.get(f.status, f.status)
            det_data.append([f.data.strftime("%d/%m/%Y"), status_txt, f.observacao or ""])

        det_tbl = Table(det_data, colWidths=[3*cm, 3.5*cm, 13.5*cm], repeatRows=1)
        det_style = TableStyle([
            ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#f0f6ff")),
            ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",     (0,0), (-1,-1), 8),
            ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#e5e7eb")),
            ("ALIGN",        (0,0), (1,-1), "CENTER"),
            ("TOPPADDING",   (0,0), (-1,-1), 3),
            ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ])
        for i, f in enumerate(registros, start=1):
            if f.status == "ausente":
                det_style.add("TEXTCOLOR", (1,i), (1,i), ROSE)
            elif f.status in ("atestado","afastamento"):
                det_style.add("TEXTCOLOR", (1,i), (1,i), AMBER)
        det_tbl.setStyle(det_style)
        story.append(det_tbl)
        story.append(Spacer(1, 10))

    doc.build(story)
    buf.seek(0)
    return buf
