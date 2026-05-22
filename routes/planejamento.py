from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db
from models.models import PlanoAula, Turma
from datetime import date, datetime, timedelta
import io

plan_bp = Blueprint("planejamento", __name__, url_prefix="/planejamento")

BIMESTRES = {1:(1,3),2:(4,6),3:(7,9),4:(10,12)}
SEMESTRES = {1:(1,6),2:(7,12)}
MESES_NOMES = ['','Janeiro','Fevereiro','Março','Abril','Maio','Junho',
               'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']


def aplicar_filtro_plano(query, filtro, ano, mes, bimestre, semestre):
    hoje = date.today()
    query = query.filter(db.extract("year", PlanoAula.data_aula) == ano)
    if filtro == "semana":
        ini = hoje - timedelta(days=hoje.weekday())
        fim = ini + timedelta(days=6)
        query = query.filter(PlanoAula.data_aula.between(ini, fim))
    elif filtro == "mes":
        query = query.filter(db.extract("month", PlanoAula.data_aula) == mes)
    elif filtro == "bimestre":
        m1, m2 = BIMESTRES.get(bimestre, (1,3))
        query = query.filter(db.extract("month", PlanoAula.data_aula) >= m1,
                             db.extract("month", PlanoAula.data_aula) <= m2)
    elif filtro == "semestre":
        m1, m2 = SEMESTRES.get(semestre, (1,6))
        query = query.filter(db.extract("month", PlanoAula.data_aula) >= m1,
                             db.extract("month", PlanoAula.data_aula) <= m2)
    # "ano" = sem filtro de mês
    return query


def periodo_label(filtro, ano, mes, bimestre, semestre):
    hoje = date.today()
    if filtro == "semana":
        ini = hoje - timedelta(days=hoje.weekday())
        fim = ini + timedelta(days=6)
        return f"Semana {ini.strftime('%d/%m')} a {fim.strftime('%d/%m/%Y')}"
    elif filtro == "mes":
        return f"{MESES_NOMES[mes]}/{ano}"
    elif filtro == "bimestre":
        return f"{bimestre}º Bimestre/{ano}"
    elif filtro == "semestre":
        return f"{semestre}º Semestre/{ano}"
    return f"Ano {ano}"


@plan_bp.route("/")
@login_required
def index():
    hoje     = date.today()
    filtro   = request.args.get("filtro", "semana")
    ano      = request.args.get("ano", hoje.year, type=int)
    mes      = request.args.get("mes", hoje.month, type=int)
    bimestre = request.args.get("bimestre", 1, type=int)
    semestre = request.args.get("semestre", 1, type=int)
    turma_id = request.args.get("turma_id", type=int)

    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    query  = PlanoAula.query.filter_by(professor_id=current_user.id)
    query  = aplicar_filtro_plano(query, filtro, ano, mes, bimestre, semestre)
    if turma_id:
        query = query.filter_by(turma_id=turma_id)
    planos = query.order_by(PlanoAula.data_aula.desc()).all()

    return render_template("planejamento/index.html",
        planos=planos, turmas=turmas, filtro=filtro,
        turma_id=turma_id, ano=ano, mes=mes, bimestre=bimestre, semestre=semestre,
        hoje=hoje,
    )


@plan_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    data_aula_pre = request.args.get("data_aula", "")
    if request.method == "POST":
        try:
            data_aula = datetime.strptime(request.form["data_aula"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            flash("Data da aula inválida.", "danger")
            return render_template("planejamento/form.html", turmas=turmas, plano=None, data_aula_pre=data_aula_pre)
        plano = PlanoAula(
            titulo=request.form.get("titulo", "").strip() or "Sem título",
            data_aula=data_aula,
            bimestre=request.form.get("bimestre", type=int),
            semestre=request.form.get("semestre", type=int),
            conteudo=request.form.get("conteudo"),
            objetivos=request.form.get("objetivos"),
            metodologia=request.form.get("metodologia"),
            recursos=request.form.get("recursos"),
            avaliacao_descricao=request.form.get("avaliacao_descricao"),
            professor_id=current_user.id,
            turma_id=request.form.get("turma_id", type=int) or None,
        )
        db.session.add(plano)
        db.session.commit()
        flash("Plano criado!", "success")
        return redirect(url_for("planejamento.index"))
    return render_template("planejamento/form.html", turmas=turmas, plano=None, data_aula_pre=data_aula_pre)


@plan_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    plano  = PlanoAula.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    if request.method == "POST":
        plano.titulo    = request.form.get("titulo", "").strip() or "Sem título"
        try:
            plano.data_aula = datetime.strptime(request.form["data_aula"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            flash("Data da aula inválida.", "danger")
            return render_template("planejamento/form.html", turmas=turmas, plano=plano)
        plano.bimestre  = request.form.get("bimestre", type=int)
        plano.semestre  = request.form.get("semestre", type=int)
        plano.conteudo  = request.form.get("conteudo")
        plano.objetivos = request.form.get("objetivos")
        plano.metodologia       = request.form.get("metodologia")
        plano.recursos          = request.form.get("recursos")
        plano.avaliacao_descricao = request.form.get("avaliacao_descricao")
        plano.turma_id  = request.form.get("turma_id", type=int) or None
        db.session.commit()
        flash("Plano atualizado!", "success")
        return redirect(url_for("planejamento.index"))
    return render_template("planejamento/form.html", turmas=turmas, plano=plano)


@plan_bp.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    plano = PlanoAula.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    db.session.delete(plano)
    db.session.commit()
    flash("Plano excluído.", "info")
    return redirect(url_for("planejamento.index"))


@plan_bp.route("/relatorio")
@login_required
def relatorio():
    hoje     = date.today()
    filtro   = request.args.get("filtro", "mes")
    ano      = request.args.get("ano", hoje.year, type=int)
    mes      = request.args.get("mes", hoje.month, type=int)
    bimestre = request.args.get("bimestre", 1, type=int)
    semestre = request.args.get("semestre", 1, type=int)
    turma_id = request.args.get("turma_id", type=int)

    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    query  = PlanoAula.query.filter_by(professor_id=current_user.id)
    query  = aplicar_filtro_plano(query, filtro, ano, mes, bimestre, semestre)
    if turma_id:
        query = query.filter_by(turma_id=turma_id)
    planos = query.order_by(PlanoAula.data_aula).all()
    label  = periodo_label(filtro, ano, mes, bimestre, semestre)

    return render_template("planejamento/relatorio.html",
        planos=planos, turmas=turmas, filtro=filtro,
        turma_id=turma_id, ano=ano, mes=mes, bimestre=bimestre, semestre=semestre,
        periodo_label=label, hoje=hoje,
    )


@plan_bp.route("/relatorio/pdf")
@login_required
def relatorio_pdf():
    hoje     = date.today()
    filtro   = request.args.get("filtro", "mes")
    ano      = request.args.get("ano", hoje.year, type=int)
    mes      = request.args.get("mes", hoje.month, type=int)
    bimestre = request.args.get("bimestre", 1, type=int)
    semestre = request.args.get("semestre", 1, type=int)
    turma_id = request.args.get("turma_id", type=int)

    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    query  = PlanoAula.query.filter_by(professor_id=current_user.id)
    query  = aplicar_filtro_plano(query, filtro, ano, mes, bimestre, semestre)
    if turma_id:
        query = query.filter_by(turma_id=turma_id)
    planos = query.order_by(PlanoAula.data_aula).all()
    label  = periodo_label(filtro, ano, mes, bimestre, semestre)
    turma_nome = next((t.nome for t in turmas if t.id == turma_id), "Todas as turmas") if turma_id else "Todas as turmas"

    buf = gerar_pdf_planejamento(planos, label, turma_nome, current_user.nome)
    nome = f"Planejamento_{label.replace('/','-').replace(' ','_')}.pdf"
    return send_file(buf, as_attachment=True, download_name=nome, mimetype="application/pdf")


def gerar_pdf_planejamento(planos, periodo_label, turma_nome, prof_nome):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    NAVY  = colors.HexColor("#1a3a5c")
    AMBER = colors.HexColor("#f59e0b")
    SAGE  = colors.HexColor("#4d7c5f")
    CINZA = colors.HexColor("#6b7280")
    LIGHT = colors.HexColor("#f0f6ff")
    SS    = getSampleStyleSheet()

    T_h1   = ParagraphStyle("h1", parent=SS["Title"], fontSize=14, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2)
    T_sub  = ParagraphStyle("sub", parent=SS["Normal"], fontSize=9, textColor=CINZA, alignment=TA_CENTER, spaceAfter=10)
    T_bold = ParagraphStyle("bold", parent=SS["Normal"], fontSize=10, fontName="Helvetica-Bold", textColor=NAVY, spaceBefore=4, spaceAfter=2)
    T_body = ParagraphStyle("body", parent=SS["Normal"], fontSize=9, leading=13, alignment=TA_JUSTIFY)
    T_label= ParagraphStyle("label", parent=SS["Normal"], fontSize=8, textColor=CINZA, fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=1)

    story = []
    story.append(Paragraph("Relatório de Planejamento de Aulas", T_h1))
    story.append(Paragraph(f"Professor(a): {prof_nome}  ·  Turma: {turma_nome}  ·  Período: {periodo_label}  ·  Gerado em {date.today().strftime('%d/%m/%Y')}", T_sub))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY))
    story.append(Spacer(1, 8))

    if not planos:
        story.append(Paragraph("Nenhum plano de aula no período selecionado.", T_body))
    else:
        # Sumário (tabela)
        sumario = [["Data", "Título", "Turma", "Bimestre"]]
        for p in planos:
            sumario.append([
                p.data_aula.strftime("%d/%m/%Y"),
                p.titulo[:60] + ("..." if len(p.titulo) > 60 else ""),
                p.turma.nome if p.turma else "—",
                f"{p.bimestre}º Bim" if p.bimestre else "—",
            ])
        tbl = Table(sumario, colWidths=[3*cm, 10*cm, 4*cm, 2.5*cm], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,0), NAVY),
            ("TEXTCOLOR",    (0,0),(-1,0), colors.white),
            ("FONTNAME",     (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",     (0,0),(-1,-1), 9),
            ("ALIGN",        (0,0),(-1,-1), "LEFT"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, LIGHT]),
            ("GRID",         (0,0),(-1,-1), 0.4, colors.HexColor("#e5e7eb")),
            ("TOPPADDING",   (0,0),(-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LEFTPADDING",  (0,0),(-1,-1), 6),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
        story.append(Spacer(1, 8))

        # Detalhe por plano
        story.append(Paragraph("Detalhamento dos Planos", T_bold))
        story.append(Spacer(1, 8))

        campos = [
            ("conteudo",           "Conteúdo / Objeto de Ensino"),
            ("objetivos",          "Objetivos"),
            ("metodologia",        "Metodologia"),
            ("recursos",           "Recursos Necessários"),
            ("avaliacao_descricao","Avaliação da Aprendizagem"),
        ]

        for p in planos:
            bloco = []
            bloco.append(HRFlowable(width="100%", thickness=1, color=AMBER))
            bloco.append(Spacer(1, 4))
            data_str = p.data_aula.strftime("%d/%m/%Y")
            bim_str  = f"  ·  {p.bimestre}º Bimestre" if p.bimestre else ""
            turma_str = f"  ·  {p.turma.nome}" if p.turma else ""
            bloco.append(Paragraph(f"<b>{p.titulo}</b>  —  {data_str}{turma_str}{bim_str}", T_bold))
            for campo, rotulo in campos:
                val = getattr(p, campo, None)
                if val and val.strip():
                    bloco.append(Paragraph(rotulo, T_label))
                    bloco.append(Paragraph(val, T_body))
            bloco.append(Spacer(1, 10))
            story.append(KeepTogether(bloco))

    doc.build(story)
    buf.seek(0)
    return buf



@plan_bp.route("/calendario")
@login_required
def calendario_web():
    """Calendário editável de planejamento — tela web com impressão."""
    import calendar as cal_mod
    hoje     = date.today()
    filtro   = request.args.get("filtro",   "mes")
    ano      = request.args.get("ano",       hoje.year,  type=int)
    mes      = request.args.get("mes",       hoje.month, type=int)
    bimestre = request.args.get("bimestre",  1,          type=int)
    semestre = request.args.get("semestre",  1,          type=int)
    turma_id = request.args.get("turma_id",  type=int)

    turmas  = Turma.query.filter_by(professor_id=current_user.id).all()
    query   = PlanoAula.query.filter_by(professor_id=current_user.id)
    query   = aplicar_filtro_plano(query, filtro, ano, mes, bimestre, semestre)
    if turma_id:
        query = query.filter_by(turma_id=turma_id)
    planos  = query.order_by(PlanoAula.data_aula).all()
    label   = periodo_label(filtro, ano, mes, bimestre, semestre)
    t_nome  = next((t.nome for t in turmas if t.id == turma_id), "Todas as turmas") if turma_id else "Todas as turmas"

    # Meses a exibir
    BIMESTRES_M = {1:(1,3),2:(4,6),3:(7,9),4:(10,12)}
    SEMESTRES_M = {1:(1,6),2:(7,12)}
    if filtro == "mes":
        meses = [(ano, mes)]
    elif filtro == "bimestre":
        m1, m2 = BIMESTRES_M.get(bimestre, (1,3))
        meses = [(ano, m) for m in range(m1, m2+1)]
    elif filtro == "semestre":
        m1, m2 = SEMESTRES_M.get(semestre, (1,6))
        meses = [(ano, m) for m in range(m1, m2+1)]
    else:
        meses = [(ano, m) for m in range(1, 13)]

    # Semanas por mês (calendário começa na segunda)
    meses_semanas = {}
    for (a, m) in meses:
        c = cal_mod.Calendar(firstweekday=0)  # 0 = segunda
        meses_semanas[(a, m)] = c.monthdayscalendar(a, m)

    # Indexa planos por data string YYYY-MM-DD
    planos_por_data = {}
    for p in planos:
        key = p.data_aula.strftime("%Y-%m-%d")
        planos_por_data.setdefault(key, []).append(p)

    # JSON dos planos para o modal JS
    import json
    planos_json = [{
        "id":         p.id,
        "titulo":     p.titulo,
        "data_aula":  p.data_aula.strftime("%d/%m/%Y"),
        "turma":      p.turma.nome if p.turma else None,
        "bimestre":   p.bimestre,
        "conteudo":   p.conteudo or "",
        "objetivos":  p.objetivos or "",
        "metodologia":p.metodologia or "",
        "recursos":   p.recursos or "",
    } for p in planos]

    return render_template("planejamento/calendario_web.html",
        planos=planos, planos_json=planos_json,
        planos_por_data=planos_por_data,
        meses=meses, meses_semanas=meses_semanas,
        label=label, turma_nome=t_nome,
        filtro=filtro, ano=ano, mes=mes,
        bimestre=bimestre, semestre=semestre,
        turma_id=turma_id,
    )

@plan_bp.route("/relatorio/calendario-pdf")
@login_required
def relatorio_calendario_pdf():
    hoje     = date.today()
    filtro   = request.args.get("filtro", "mes")
    ano      = request.args.get("ano", hoje.year, type=int)
    mes      = request.args.get("mes", hoje.month, type=int)
    bimestre = request.args.get("bimestre", 1, type=int)
    semestre = request.args.get("semestre", 1, type=int)
    turma_id = request.args.get("turma_id", type=int)

    query  = PlanoAula.query.filter_by(professor_id=current_user.id)
    query  = aplicar_filtro_plano(query, filtro, ano, mes, bimestre, semestre)
    if turma_id:
        query = query.filter_by(turma_id=turma_id)
    planos = query.order_by(PlanoAula.data_aula).all()
    label  = periodo_label(filtro, ano, mes, bimestre, semestre)

    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    turma_nome = next((t.nome for t in turmas if t.id == turma_id), "Todas") if turma_id else "Todas as turmas"

    buf  = gerar_pdf_planejamento_calendario(planos, label, turma_nome, current_user.nome,
                                              filtro, ano, mes, bimestre, semestre)
    nome = f"Planejamento_Calendario_{label.replace('/','-').replace(' ','_')}.pdf"
    return send_file(buf, as_attachment=True, download_name=nome, mimetype="application/pdf")


def gerar_pdf_planejamento_calendario(planos, label, turma_nome, prof_nome,
                                       filtro, ano, mes, bimestre, semestre):
    import calendar as cal_mod
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable, PageBreak)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    BIMESTRES_R = {1:(1,3),2:(4,6),3:(7,9),4:(10,12)}
    SEMESTRES_R = {1:(1,6),2:(7,12)}
    MESES_PT_R  = ['','Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                   'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    DIAS_FULL_R = ['DOMINGO','SEGUNDA','TERÇA','QUARTA','QUINTA','SEXTA','SÁBADO']

    def get_meses():
        if filtro=="mes":      return [(ano,mes)]
        if filtro=="bimestre":
            m1,m2=BIMESTRES_R.get(bimestre,(1,3)); return [(ano,m) for m in range(m1,m2+1)]
        if filtro=="semestre":
            m1,m2=SEMESTRES_R.get(semestre,(1,6)); return [(ano,m) for m in range(m1,m2+1)]
        return [(ano,m) for m in range(1,13)]

    # Indexa planos por data
    planos_por_dia = {}
    for p in planos:
        planos_por_dia.setdefault(p.data_aula, []).append(p)

    NAVY   = colors.HexColor("#1a3a5c")
    AMBER  = colors.HexColor("#f59e0b")
    LIGHT  = colors.HexColor("#fffbeb")
    CINZA  = colors.HexColor("#6b7280")
    WHITE  = colors.white
    SS     = getSampleStyleSheet()

    T_titulo = ParagraphStyle("tt", parent=SS["Title"],  fontSize=12, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2)
    T_sub    = ParagraphStyle("ts", parent=SS["Normal"], fontSize=8,  textColor=CINZA, alignment=TA_CENTER, spaceAfter=6)
    T_dow    = ParagraphStyle("td", parent=SS["Normal"], fontSize=7,  fontName="Helvetica-Bold", textColor=NAVY, alignment=TA_CENTER)
    T_num    = ParagraphStyle("tn", parent=SS["Normal"], fontSize=7,  fontName="Helvetica-Bold", textColor=colors.HexColor("#374151"))
    T_plan   = ParagraphStyle("tp", parent=SS["Normal"], fontSize=6.5, textColor=colors.HexColor("#1a3a5c"), leading=9)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1*cm, rightMargin=1*cm,
                            topMargin=1*cm, bottomMargin=1*cm)
    story = []

    story.append(Paragraph("Planejamento de Aulas — Calendário", T_titulo))
    story.append(Paragraph(f"Professor(a): {prof_nome}  ·  Turma: {turma_nome}  ·  Período: {label}", T_sub))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY))
    story.append(Spacer(1, 8))

    meses_list = get_meses()
    CELL_W = (28.5*cm) / 7
    CELL_H = 2.5*cm

    for (ano_m, mes_m) in meses_list:
        story.append(Paragraph(f"{MESES_PT_R[mes_m].upper()} {ano_m}",
                                ParagraphStyle("mh", parent=SS["Normal"], fontSize=10,
                                               fontName="Helvetica-Bold", textColor=NAVY,
                                               spaceBefore=10, spaceAfter=4)))

        cal = cal_mod.Calendar(firstweekday=6)
        semanas = cal.monthdayscalendar(ano_m, mes_m)

        header_row = [Paragraph(d, T_dow) for d in DIAS_FULL_R]
        cal_data   = [header_row]

        for semana in semanas:
            row = []
            for dow_idx, dia in enumerate(semana):
                if dia == 0:
                    row.append("")
                    continue
                d = date(ano_m, mes_m, dia)
                ps = planos_por_dia.get(d, [])
                if ps:
                    inner_rows = [[Paragraph(str(dia), T_num)]]
                    for p in ps:
                        titulo_curto = p.titulo[:35] + ("…" if len(p.titulo)>35 else "")
                        inner_rows.append([Paragraph(f"• {titulo_curto}", T_plan)])
                        if p.turma:
                            inner_rows.append([Paragraph(f"  {p.turma.nome}", ParagraphStyle("tx", parent=SS["Normal"], fontSize=5.5, textColor=CINZA, leading=7))])
                    cell = Table(inner_rows, colWidths=[CELL_W-0.2*cm])
                    cell.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1),("LEFTPADDING",(0,0),(-1,-1),3)]))
                    row.append(cell)
                else:
                    row.append(Paragraph(str(dia), T_num))
            cal_data.append(row)

        t = Table(cal_data, colWidths=[CELL_W]*7)
        style = TableStyle([
            ("BACKGROUND",   (0,0),(-1,0), NAVY),
            ("TEXTCOLOR",    (0,0),(-1,0), WHITE),
            ("FONTNAME",     (0,0),(-1,0), "Helvetica-Bold"),
            ("ALIGN",        (0,0),(-1,0), "CENTER"),
            ("TOPPADDING",   (0,0),(-1,0), 5),
            ("BOTTOMPADDING",(0,0),(-1,0), 5),
            ("GRID",         (0,0),(-1,-1), 0.5, colors.HexColor("#d1d5db")),
            ("VALIGN",       (0,1),(-1,-1), "TOP"),
            ("TOPPADDING",   (0,1),(-1,-1), 3),
            ("LEFTPADDING",  (0,1),(-1,-1), 4),
            ("BOTTOMPADDING",(0,1),(-1,-1), 3),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, colors.HexColor("#f9fafb")]),
            ("MINROWHEIGHT", (0,1),(-1,-1), CELL_H),
        ])
        # Destaca células com planos
        for row_i, semana in enumerate(semanas, 1):
            for col_i, dia in enumerate(semana):
                if dia == 0: continue
                d = date(ano_m, mes_m, dia)
                if planos_por_dia.get(d):
                    style.add("BACKGROUND", (col_i, row_i), (col_i, row_i), LIGHT)
                    style.add("LEFTBORDERPADDING", (col_i, row_i), (col_i, row_i), 0)
                    # borda laranja esquerda via BOX
                    style.add("BOX", (col_i, row_i), (col_i, row_i), 1, AMBER)
        t.setStyle(style)
        story.append(t)

    doc.build(story)
    buf.seek(0)
    return buf


# ── PDF Calendário de Planejamento ────────────────────────────────────────────

@plan_bp.route("/relatorio/calendario")
@login_required
def relatorio_calendario():
    hoje     = date.today()
    filtro   = request.args.get("filtro", "mes")
    ano      = request.args.get("ano",      hoje.year,  type=int)
    mes      = request.args.get("mes",      hoje.month, type=int)
    bimestre = request.args.get("bimestre", 1,          type=int)
    semestre = request.args.get("semestre", 1,          type=int)
    turma_id = request.args.get("turma_id", type=int)

    turmas  = Turma.query.filter_by(professor_id=current_user.id).all()
    query   = PlanoAula.query.filter_by(professor_id=current_user.id)
    query   = aplicar_filtro_plano(query, filtro, ano, mes, bimestre, semestre)
    if turma_id:
        query = query.filter_by(turma_id=turma_id)
    planos  = query.order_by(PlanoAula.data_aula).all()
    label   = periodo_label(filtro, ano, mes, bimestre, semestre)
    t_nome  = next((t.nome for t in turmas if t.id == turma_id), "Todas as turmas") if turma_id else "Todas as turmas"

    buf  = _pdf_calendario_planos(planos, label, t_nome, current_user.nome, filtro, ano, mes, bimestre, semestre)
    nome = f"Calendario_Planos_{label.replace('/','-').replace(' ','_')}.pdf"
    return send_file(buf, as_attachment=True, download_name=nome, mimetype="application/pdf")


def _pdf_calendario_planos(planos, periodo_label, turma_nome, prof_nome, filtro, ano, mes, bimestre, semestre):
    import calendar as cal_mod
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
    AMBER = colors.HexColor("#f59e0b")
    AMB_L = colors.HexColor("#fffbeb")
    SAGE  = colors.HexColor("#4d7c5f")
    SAGE_L= colors.HexColor("#f0fdf4")
    GRAY  = colors.HexColor("#e5e7eb")
    LIGHT = colors.HexColor("#f9fafb")
    CINZA = colors.HexColor("#9ca3af")
    WHITE = colors.white

    SS   = getSampleStyleSheet()
    T_h1 = ParagraphStyle("h1", parent=SS["Title"], fontSize=13, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2)
    T_sub= ParagraphStyle("sub", parent=SS["Normal"], fontSize=8,  textColor=CINZA, alignment=TA_CENTER, spaceAfter=6)
    T_mes= ParagraphStyle("mes", parent=SS["Normal"], fontSize=11, fontName="Helvetica-Bold", textColor=NAVY, alignment=TA_CENTER)
    T_day= ParagraphStyle("day", parent=SS["Normal"], fontSize=7,  textColor=colors.black)
    T_ev = ParagraphStyle("ev",  parent=SS["Normal"], fontSize=6,  textColor=NAVY, leading=8)

    # Mapeia planos por data
    planos_por_data = {}
    for p in planos:
        planos_por_data.setdefault(p.data_aula, []).append(p)

    # Meses a exibir
    BIMESTRES_MAP = {1:(1,3),2:(4,6),3:(7,9),4:(10,12)}
    SEMESTRES_MAP = {1:(1,6),2:(7,12)}
    if filtro == "mes":       meses = [(ano, mes)]
    elif filtro == "bimestre":
        m1,m2 = BIMESTRES_MAP.get(bimestre,(1,3))
        meses = [(ano,m) for m in range(m1,m2+1)]
    elif filtro == "semestre":
        m1,m2 = SEMESTRES_MAP.get(semestre,(1,6))
        meses = [(ano,m) for m in range(m1,m2+1)]
    else:
        meses = [(ano,m) for m in range(1,13)]

    MESES_PT = ['','Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    CAB = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]

    CELL_W = 3.85*cm
    CELL_H = 2.0*cm   # maior que frequência p/ caber título do plano

    story = []
    story.append(Paragraph(f"Calendário de Planejamento — {prof_nome}", T_h1))
    story.append(Paragraph(f"Turma: {turma_nome}  ·  Período: {periodo_label}  ·  {date.today().strftime('%d/%m/%Y')}", T_sub))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY))
    story.append(Spacer(1, 10))

    for (ano_c, mes_c) in meses:
        story.append(Paragraph(f"{MESES_PT[mes_c]} {ano_c}", T_mes))
        story.append(Spacer(1, 6))

        cal_month = cal_mod.monthcalendar(ano_c, mes_c)
        cab_cells = [Paragraph(f"<b>{d}</b>", ParagraphStyle(
            "dc", parent=T_day, alignment=TA_CENTER, textColor=WHITE)) for d in CAB]
        tbl_data = [cab_cells]

        for semana in cal_month:
            row = []
            for dia in semana:
                if dia == 0:
                    row.append("")
                    continue
                d = date(ano_c, mes_c, dia)
                planos_dia = planos_por_data.get(d, [])
                partes = [Paragraph(f"<b>{dia}</b>", ParagraphStyle(
                    "dn", parent=T_day, textColor=NAVY if planos_dia else CINZA))]
                for p in planos_dia[:2]:  # máx 2 por célula
                    titulo = p.titulo[:30] + ("…" if len(p.titulo)>30 else "")
                    partes.append(Paragraph(f"• {titulo}", T_ev))
                if len(planos_dia) > 2:
                    partes.append(Paragraph(f"  +{len(planos_dia)-2} mais", T_ev))
                row.append(partes)
            tbl_data.append(row)

        tbl = Table(tbl_data,
                    colWidths=[CELL_W]*7,
                    rowHeights=[0.55*cm] + [CELL_H]*len(cal_month))

        ts = TableStyle([
            ("BACKGROUND",   (0,0),(6,0), NAVY),
            ("TEXTCOLOR",    (0,0),(6,0), WHITE),
            ("ALIGN",        (0,0),(6,0), "CENTER"),
            ("VALIGN",       (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",   (0,0),(-1,-1), 3),
            ("LEFTPADDING",  (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 2),
            ("GRID",         (0,0),(-1,-1), 0.5, GRAY),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT]),
        ])

        for ri, semana in enumerate(cal_month, 1):
            for ci, dia in enumerate(semana):
                if dia == 0:
                    ts.add("BACKGROUND",(ci,ri),(ci,ri), LIGHT)
                    continue
                d = date(ano_c, mes_c, dia)
                if planos_por_data.get(d):
                    ts.add("BACKGROUND",(ci,ri),(ci,ri), AMB_L)
                    ts.add("LINEBELOW",(ci,ri),(ci,ri), 1.5, AMBER)
                if ci >= 5:  # sab/dom
                    ts.add("BACKGROUND",(ci,ri),(ci,ri), colors.HexColor("#f3f4f6"))

        tbl.setStyle(ts)
        story.append(tbl)
        story.append(Spacer(1, 12))

        if (ano_c, mes_c) != meses[-1]:
            story.append(PageBreak())

    doc.build(story)
    buf.seek(0)
    return buf
