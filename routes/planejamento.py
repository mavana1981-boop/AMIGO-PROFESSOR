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
    if request.method == "POST":
        plano = PlanoAula(
            titulo=request.form["titulo"],
            data_aula=datetime.strptime(request.form["data_aula"], "%Y-%m-%d").date(),
            bimestre=request.form.get("bimestre", type=int),
            semestre=request.form.get("semestre", type=int),
            conteudo=request.form.get("conteudo"),
            objetivos=request.form.get("objetivos"),
            metodologia=request.form.get("metodologia"),
            recursos=request.form.get("recursos"),
            avaliacao_descricao=request.form.get("avaliacao_descricao"),
            professor_id=current_user.id,
            turma_id=request.form.get("turma_id", type=int),
        )
        db.session.add(plano)
        db.session.commit()
        flash("Plano criado!", "success")
        return redirect(url_for("planejamento.index"))
    return render_template("planejamento/form.html", turmas=turmas, plano=None)


@plan_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    plano  = PlanoAula.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    if request.method == "POST":
        plano.titulo    = request.form["titulo"]
        plano.data_aula = datetime.strptime(request.form["data_aula"], "%Y-%m-%d").date()
        plano.bimestre  = request.form.get("bimestre", type=int)
        plano.semestre  = request.form.get("semestre", type=int)
        plano.conteudo  = request.form.get("conteudo")
        plano.objetivos = request.form.get("objetivos")
        plano.metodologia       = request.form.get("metodologia")
        plano.recursos          = request.form.get("recursos")
        plano.avaliacao_descricao = request.form.get("avaliacao_descricao")
        plano.turma_id  = request.form.get("turma_id", type=int)
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
