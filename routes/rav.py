from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db
from models.models import RegistroAvaliacao, Aluno, Turma
from datetime import datetime
import io, os

rav_bp = Blueprint("rav", __name__, url_prefix="/rav")


def get_alunos():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    alunos = []
    for t in turmas:
        alunos.extend(sorted(t.alunos, key=lambda a: a.nome))
    return sorted(alunos, key=lambda a: a.nome)


@rav_bp.route("/")
@login_required
def index():
    turmas   = Turma.query.filter_by(professor_id=current_user.id).all()
    turma_id = request.args.get("turma_id", type=int)
    ravs     = RegistroAvaliacao.query.filter_by(professor_id=current_user.id)\
                                      .order_by(RegistroAvaliacao.criado_em.desc()).all()
    if turma_id:
        ravs = [r for r in ravs if r.aluno.turma_id == turma_id]
    return render_template("rav/index.html", ravs=ravs, turmas=turmas, turma_id=turma_id)


@rav_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    alunos   = get_alunos()
    aluno_id = request.args.get("aluno_id", type=int)
    if request.method == "POST":
        rav = RegistroAvaliacao(
            aluno_id        = request.form.get("aluno_id", type=int),
            professor_id    = current_user.id,
            bimestre        = request.form.get("bimestre", type=int),
            ano_letivo      = request.form.get("ano_letivo", 2026, type=int),
            total_dias      = request.form.get("total_dias", 48, type=int),
            total_faltas    = request.form.get("total_faltas", 0, type=int),
            data_inicio_bim = request.form.get("data_inicio_bim", "12 de fevereiro"),
            data_fim_bim    = request.form.get("data_fim_bim", "29 de maio de 2026"),
            comportamento   = request.form.get("comportamento", ""),
            linguagem_leitura = request.form.get("linguagem_leitura", ""),
            linguagem_escrita = request.form.get("linguagem_escrita", ""),
            gramatica       = request.form.get("gramatica", ""),
            matematica      = request.form.get("matematica", ""),
            ciencias        = request.form.get("ciencias", ""),
            historia        = request.form.get("historia", ""),
            geografia       = request.form.get("geografia", ""),
            artes           = request.form.get("artes", ""),
            educacao_fisica = request.form.get("educacao_fisica", ""),
            sintese         = request.form.get("sintese", ""),
            perspectiva     = request.form.get("perspectiva", ""),
            resultado_final = request.form.get("resultado_final", ""),
        )
        db.session.add(rav)
        db.session.commit()
        flash("RAv salvo!", "success")
        return redirect(url_for("rav.index"))
    return render_template("rav/form.html", alunos=alunos, aluno_id=aluno_id, rav=None)


@rav_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    rav    = RegistroAvaliacao.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    alunos = get_alunos()
    if request.method == "POST":
        rav.bimestre          = request.form.get("bimestre", type=int)
        rav.ano_letivo        = request.form.get("ano_letivo", 2026, type=int)
        rav.total_dias        = request.form.get("total_dias", 48, type=int)
        rav.total_faltas      = request.form.get("total_faltas", 0, type=int)
        rav.data_inicio_bim   = request.form.get("data_inicio_bim", "")
        rav.data_fim_bim      = request.form.get("data_fim_bim", "")
        rav.comportamento     = request.form.get("comportamento", "")
        rav.linguagem_leitura = request.form.get("linguagem_leitura", "")
        rav.linguagem_escrita = request.form.get("linguagem_escrita", "")
        rav.gramatica         = request.form.get("gramatica", "")
        rav.matematica        = request.form.get("matematica", "")
        rav.ciencias          = request.form.get("ciencias", "")
        rav.historia          = request.form.get("historia", "")
        rav.geografia         = request.form.get("geografia", "")
        rav.artes             = request.form.get("artes", "")
        rav.educacao_fisica   = request.form.get("educacao_fisica", "")
        rav.sintese           = request.form.get("sintese", "")
        rav.perspectiva       = request.form.get("perspectiva", "")
        rav.resultado_final   = request.form.get("resultado_final", "")
        db.session.commit()
        flash("RAv atualizado!", "success")
        return redirect(url_for("rav.index"))
    return render_template("rav/form.html", alunos=alunos, aluno_id=rav.aluno_id, rav=rav)


@rav_bp.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    rav = RegistroAvaliacao.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    db.session.delete(rav)
    db.session.commit()
    flash("RAv excluído.", "info")
    return redirect(url_for("rav.index"))


@rav_bp.route("/gerar/<int:id>")
@login_required
def gerar(id):
    rav       = RegistroAvaliacao.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    aluno     = rav.aluno
    turma     = aluno.turma
    professor = rav.professor

    try:
        buffer = gerar_docx(rav, aluno, turma, professor)
        nome = f"RAv_{aluno.nome.replace(' ','_')}_{rav.bimestre}Bim_{rav.ano_letivo}.docx"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=nome,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        flash(f"Erro ao gerar documento: {str(e)}", "danger")
        return redirect(url_for("rav.index"))


def xou(cond):
    return "X" if cond else " "


def gerar_docx(rav, aluno, turma, professor):
    """Gera o RAv em formato .docx usando python-docx."""
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_ALIGN_VERTICAL
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    bim_num   = rav.bimestre or 1
    bim_label = f"{bim_num}º Bimestre"
    bloco1    = bim_num in [1, 2]

    # Checkboxes
    def_nao  = xou(not aluno.apresenta_deficiencia)
    def_sim  = xou(aluno.apresenta_deficiencia)
    adeq_nao = xou(not aluno.adequacao_curricular)
    adeq_sim = xou(aluno.adequacao_curricular)
    temp_nao = xou(not aluno.indicado_temporalidade)
    temp_sim = xou(aluno.indicado_temporalidade)
    sala_nao = xou(not aluno.sala_recursos)
    sala_sim = xou(aluno.sala_recursos)
    sup_nao  = xou(not aluno.programa_superacao)
    sup_sim  = xou(aluno.programa_superacao)
    atend    = aluno.tipo_atendimento or ""
    cl_x     = xou(atend == "classe_comum")
    sa_x     = xou(atend == "superacao")
    sr_x     = xou(atend == "superacao_reduzida")
    org      = aluno.org_curricular_superacao or "nao"
    org_n    = xou(org == "nao")
    org_s    = xou(org == "sim")
    org_p    = xou(org == "parcialmente")
    res      = rav.resultado_final or ""
    r_cur    = xou(res == "cursando")
    r_pro    = xou(res == "progressao")
    r_ava    = xou(res == "avanco")
    r_apr    = xou(res == "aprovado")
    r_rep    = xou(res == "reprovado")
    r_aba    = xou(res == "abandono")
    b1x      = xou(bloco1)
    b2x      = xou(not bloco1)

    regional  = (professor.regional or "PLANO PILOTO").upper()
    escola    = professor.escola or ""
    ano_turma = turma.serie or f"{turma.ano}º Ano"
    prof_nome = professor.nome

    # Texto do Bloco B
    partes = [
        f"Este relatório sintetiza as observações realizadas durante e com base nos objetivos do {bim_label}, "
        f"que teve início em {rav.data_inicio_bim or '12 de fevereiro'} e se encerrou no dia "
        f"{rav.data_fim_bim or '29 de maio de 2026'}. "
        f"O presente instrumento visa compartilhar o processo de desenvolvimento e aprendizagens "
        f"do(a) estudante {aluno.nome}.",
        rav.comportamento or "",
        rav.linguagem_leitura or "",
        rav.linguagem_escrita or "",
        rav.gramatica or "",
        rav.matematica or "",
        rav.ciencias or "",
        rav.historia or "",
        rav.geografia or "",
        rav.artes or "",
        rav.educacao_fisica or "",
        rav.sintese or "",
        rav.perspectiva or "",
    ]
    texto_b = " ".join(p.strip() for p in partes if p.strip())

    # ── Cria o documento ──────────────────────────────────────────────────────
    doc = Document()

    # Margens estreitas (A4)
    for section in doc.sections:
        section.page_width  = Cm(21)
        section.page_height = Cm(29.7)
        section.left_margin = section.right_margin = Cm(1.5)
        section.top_margin  = section.bottom_margin = Cm(1.5)

    def set_font(run, size=10, bold=False):
        run.font.name = "Times New Roman"
        run.font.size = Pt(size)
        run.bold = bold

    def add_centered(text, size=10, bold=False):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(2)
        run = p.add_run(text)
        set_font(run, size, bold)
        return p

    def cell_text(cell, text, size=10, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = align
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(0)
        run = p.add_run(text)
        set_font(run, size, bold)
        return p

    def set_cell_margins(cell, top=40, bottom=40, left=80, right=80):
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcMar = OxmlElement('w:tcMar')
        for side, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
            node = OxmlElement(f'w:{side}')
            node.set(qn('w:w'), str(val))
            node.set(qn('w:type'), 'dxa')
            tcMar.append(node)
        tcPr.append(tcMar)

    def shade_cell(cell, fill="DDDDDD"):
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd  = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), fill)
        tcPr.append(shd)

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    add_centered("SECRETARIA DE ESTADO DE EDUCAÇÃO DO DISTRITO FEDERAL", 10, True)
    add_centered("SUBSECRETARIA DE EDUCAÇÃO BÁSICA", 10, True)
    add_centered("REGISTRO DE AVALIAÇÃO - RAv", 11, True)
    add_centered("Formulário 1: Descrição do Processo de Aprendizagem do Estudante", 10, True)
    p = add_centered("Ensino Fundamental (Anos Iniciais)", 10, True)
    p.paragraph_format.space_after = Pt(6)

    # ── Tabela Bloco A ─────────────────────────────────────────────────────────
    def add_bloco_row(table, letra_col_cell, texto, bold=False):
        row = table.add_row()
        # Coluna letra (já preenchida na primeira linha)
        c0 = row.cells[0]
        c1 = row.cells[1]
        set_cell_margins(c0)
        set_cell_margins(c1)
        cell_text(c1, texto, bold=bold)
        return row

    linhas_a = [
        (True,  f"Ano Letivo: {rav.ano_letivo}"),
        (False, f"Coordenação Regional de Ensino: {regional}"),
        (False, f"Unidade Escolar: {escola}"),
        (False, f"Bloco: ({b1x}) 1º Bloco   ({b2x}) 2º Bloco"),
        (False, f"Ano: {ano_turma}   Turma: {turma.nome}   Turno: ( ) Matutino   (X) Vespertino   ( ) Integral"),
        (False, f"Professor (a) Regente da turma: {prof_nome}"),
        (False, f"Professor(a): "),
        (False, f"Professor(a): "),
        (False, f"Estudante: {aluno.nome}"),
        (False, f"Apresenta Deficiência ou TEA? ({def_nao}) não   ({def_sim}) sim"),
        (False, f"Houve adequação curricular? ({adeq_nao}) não   ({adeq_sim}) sim"),
        (False, f"Estudante indicado para temporalidade? ({temp_nao}) não   ({temp_sim}) sim"),
        (False, f"Está sendo atendido em Sala de Recursos? ({sala_nao}) não   ({sala_sim}) sim"),
        (False, f'Estudante do Programa SuperAção "setado" no Sistema de Gestão i-Educar? ({sup_nao}) não   ({sup_sim}) sim'),
        (False, "Atendimento:"),
        (False, f"({cl_x}) Classe Comum com atendimento personalizado"),
        (False, f"({sa_x}) Turma SuperAção"),
        (False, f"({sr_x}) Turma SuperAção Reduzida"),
        (False, "Foi aplicada a Organização Curricular específica do Programa Superação?"),
        (False, f"({org_n}) não   ({org_s}) sim   ({org_p}) parcialmente"),
        (False, f"{bim_label}   Total de dias letivos: {rav.total_dias}   Total de Faltas: {rav.total_faltas}"),
    ]

    tbl_a = doc.add_table(rows=0, cols=2)
    tbl_a.style = "Table Grid"
    col_widths_a = [Cm(1.0), Cm(17.0)]

    first = True
    for is_first, texto in linhas_a:
        row = tbl_a.add_row()
        c0, c1 = row.cells[0], row.cells[1]
        set_cell_margins(c0); set_cell_margins(c1)
        if first:
            shade_cell(c0)
            cell_text(c0, "A", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
            first = False
        else:
            c0.text = ""
        ultima = (texto == linhas_a[-1][1])
        cell_text(c1, texto, bold=ultima)

    # Ajusta larguras
    for row in tbl_a.rows:
        row.cells[0].width = col_widths_a[0]
        row.cells[1].width = col_widths_a[1]

    doc.add_paragraph().paragraph_format.space_after = Pt(0)

    # ── Tabela Bloco B ─────────────────────────────────────────────────────────
    tbl_b = doc.add_table(rows=1, cols=2)
    tbl_b.style = "Table Grid"
    row_b = tbl_b.rows[0]
    c0b, c1b = row_b.cells[0], row_b.cells[1]
    set_cell_margins(c0b); set_cell_margins(c1b, left=100, right=100)
    shade_cell(c0b)
    cell_text(c0b, "B", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    c0b.width = Cm(1.0)
    c1b.width = Cm(17.0)

    # Texto justificado do bloco B
    c1b.text = ""
    p_b = c1b.paragraphs[0]
    p_b.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_b.paragraph_format.space_before = Pt(0)
    p_b.paragraph_format.space_after  = Pt(0)
    from docx.oxml import OxmlElement as OE
    # Set line spacing 1.0
    pPr = p_b._p.get_or_add_pPr()
    spacing = OE('w:spacing')
    spacing.set(qn('w:line'), '240')
    spacing.set(qn('w:lineRule'), 'auto')
    pPr.append(spacing)
    run_b = p_b.add_run(texto_b)
    set_font(run_b, 10)

    doc.add_paragraph().paragraph_format.space_after = Pt(0)

    # ── Bloco C ────────────────────────────────────────────────────────────────
    tbl_c = doc.add_table(rows=1, cols=2)
    tbl_c.style = "Table Grid"
    c0c, c1c = tbl_c.rows[0].cells[0], tbl_c.rows[0].cells[1]
    set_cell_margins(c0c); set_cell_margins(c1c)
    shade_cell(c0c)
    cell_text(c0c, "C", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    cell_text(c1c, "Local/Data: Brasília/DF, 29 de Abril de 2026.")
    c0c.width = Cm(1.0); c1c.width = Cm(17.0)

    doc.add_paragraph().paragraph_format.space_after = Pt(0)

    # ── Bloco D — Assinaturas ──────────────────────────────────────────────────
    tbl_d = doc.add_table(rows=1, cols=2)
    tbl_d.style = "Table Grid"
    c0d, c1d = tbl_d.rows[0].cells[0], tbl_d.rows[0].cells[1]
    set_cell_margins(c0d); set_cell_margins(c1d)
    shade_cell(c0d)
    cell_text(c0d, "D", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    c0d.width = Cm(1.0); c1d.width = Cm(17.0)

    c1d.text = ""
    for linha, bold in [
        (prof_nome.upper(), True),
        ("Assinatura/Matrícula da Professora Regente", False),
        (" ", False),
        ("Assinatura/Matrícula do(a) Coordenador(a) Pedagógico", False),
        (" ", False),
        ("Assinatura do(a) Pai/Mãe ou Responsável Legal", False),
    ]:
        p = c1d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(4)
        run = p.add_run(linha)
        set_font(run, 9 if not bold else 10, bold)

    doc.add_paragraph().paragraph_format.space_after = Pt(0)

    # ── Bloco E — Resultado Final ──────────────────────────────────────────────
    tbl_e = doc.add_table(rows=1, cols=2)
    tbl_e.style = "Table Grid"
    c0e, c1e = tbl_e.rows[0].cells[0], tbl_e.rows[0].cells[1]
    set_cell_margins(c0e); set_cell_margins(c1e)
    shade_cell(c0e)
    cell_text(c0e, "E", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    c0e.width = Cm(1.0); c1e.width = Cm(17.0)

    c1e.text = ""
    for linha in [
        ("Resultado Final (Preencher somente ao final do 4º bimestre)", True),
        (f"({r_cur}) Cursando   ({r_pro}) Progressão Continuada   ({r_ava}) Avanço das Aprendizagens - Correção de Fluxo", False),
        (f"({r_apr}) Aprovado   ({r_rep}) Reprovado   ({r_aba}) Abandono", False),
    ]:
        p = c1e.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(2)
        run = p.add_run(linha[0])
        set_font(run, 10, linha[1])

    # ── Salva em memória ───────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
