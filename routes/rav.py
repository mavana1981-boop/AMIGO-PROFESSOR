from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db
from models.models import RegistroAvaliacao, Aluno, Turma
from datetime import datetime
import subprocess, os, json, tempfile

rav_bp = Blueprint("rav", __name__, url_prefix="/rav")


@rav_bp.route("/")
@login_required
def index():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    turma_id = request.args.get("turma_id", type=int)
    query = RegistroAvaliacao.query.filter_by(professor_id=current_user.id)
    ravs = query.order_by(RegistroAvaliacao.criado_em.desc()).all()
    if turma_id:
        ravs = [r for r in ravs if r.aluno.turma_id == turma_id]
    return render_template("rav/index.html", ravs=ravs, turmas=turmas, turma_id=turma_id)


@rav_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    alunos = []
    for t in turmas:
        alunos.extend(t.alunos)

    aluno_id = request.args.get("aluno_id", type=int)

    if request.method == "POST":
        aluno_id = request.form.get("aluno_id", type=int)
        rav = RegistroAvaliacao(
            aluno_id=aluno_id,
            professor_id=current_user.id,
            bimestre=request.form.get("bimestre", type=int),
            ano_letivo=request.form.get("ano_letivo", 2026, type=int),
            total_dias=request.form.get("total_dias", 48, type=int),
            total_faltas=request.form.get("total_faltas", 0, type=int),
            data_inicio_bim=request.form.get("data_inicio_bim", "12 de fevereiro"),
            data_fim_bim=request.form.get("data_fim_bim", "29 de maio de 2026"),
            comportamento=request.form.get("comportamento", ""),
            linguagem_leitura=request.form.get("linguagem_leitura", ""),
            linguagem_escrita=request.form.get("linguagem_escrita", ""),
            gramatica=request.form.get("gramatica", ""),
            matematica=request.form.get("matematica", ""),
            ciencias=request.form.get("ciencias", ""),
            historia=request.form.get("historia", ""),
            geografia=request.form.get("geografia", ""),
            artes=request.form.get("artes", ""),
            educacao_fisica=request.form.get("educacao_fisica", ""),
            sintese=request.form.get("sintese", ""),
            perspectiva=request.form.get("perspectiva", ""),
            resultado_final=request.form.get("resultado_final", ""),
        )
        db.session.add(rav)
        db.session.commit()
        flash("RAv salvo com sucesso!", "success")
        return redirect(url_for("rav.index"))

    return render_template("rav/form.html", turmas=turmas, alunos=alunos, aluno_id=aluno_id, rav=None)


@rav_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    rav = RegistroAvaliacao.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    alunos = []
    for t in turmas:
        alunos.extend(t.alunos)

    if request.method == "POST":
        rav.bimestre        = request.form.get("bimestre", type=int)
        rav.ano_letivo      = request.form.get("ano_letivo", 2026, type=int)
        rav.total_dias      = request.form.get("total_dias", 48, type=int)
        rav.total_faltas    = request.form.get("total_faltas", 0, type=int)
        rav.data_inicio_bim = request.form.get("data_inicio_bim", "")
        rav.data_fim_bim    = request.form.get("data_fim_bim", "")
        rav.comportamento   = request.form.get("comportamento", "")
        rav.linguagem_leitura = request.form.get("linguagem_leitura", "")
        rav.linguagem_escrita = request.form.get("linguagem_escrita", "")
        rav.gramatica       = request.form.get("gramatica", "")
        rav.matematica      = request.form.get("matematica", "")
        rav.ciencias        = request.form.get("ciencias", "")
        rav.historia        = request.form.get("historia", "")
        rav.geografia       = request.form.get("geografia", "")
        rav.artes           = request.form.get("artes", "")
        rav.educacao_fisica = request.form.get("educacao_fisica", "")
        rav.sintese         = request.form.get("sintese", "")
        rav.perspectiva     = request.form.get("perspectiva", "")
        rav.resultado_final = request.form.get("resultado_final", "")
        db.session.commit()
        flash("RAv atualizado!", "success")
        return redirect(url_for("rav.index"))

    return render_template("rav/form.html", turmas=turmas, alunos=alunos, aluno_id=rav.aluno_id, rav=rav)


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
    rav = RegistroAvaliacao.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    aluno = rav.aluno
    turma = aluno.turma
    professor = rav.professor

    # Build data dict for JS generator
    dados = {
        "ano_letivo": rav.ano_letivo,
        "regional": professor.regional or "PLANO PILOTO",
        "escola": professor.escola or "",
        "bimestre": rav.bimestre,
        "ano_turma": turma.serie or f"{turma.ano}º Ano",
        "turma_nome": turma.nome,
        "professor_regente": professor.nome,
        "professor_matricula": "",
        "aluno_nome": aluno.nome,
        "deficiencia": "sim" if aluno.apresenta_deficiencia else "não",
        "tipo_deficiencia": aluno.tipo_deficiencia or "",
        "adequacao": "sim" if aluno.adequacao_curricular else "não",
        "temporalidade": "sim" if aluno.indicado_temporalidade else "não",
        "sala_recursos": "sim" if aluno.sala_recursos else "não",
        "superacao": "sim" if aluno.programa_superacao else "não",
        "tipo_atendimento": aluno.tipo_atendimento or "",
        "org_curricular": aluno.org_curricular_superacao or "não",
        "total_dias": rav.total_dias,
        "total_faltas": rav.total_faltas,
        "data_inicio_bim": rav.data_inicio_bim or "12 de fevereiro",
        "data_fim_bim": rav.data_fim_bim or "29 de maio de 2026",
        "comportamento": rav.comportamento or "",
        "linguagem_leitura": rav.linguagem_leitura or "",
        "linguagem_escrita": rav.linguagem_escrita or "",
        "gramatica": rav.gramatica or "",
        "matematica": rav.matematica or "",
        "ciencias": rav.ciencias or "",
        "historia": rav.historia or "",
        "geografia": rav.geografia or "",
        "artes": rav.artes or "",
        "educacao_fisica": rav.educacao_fisica or "",
        "sintese": rav.sintese or "",
        "perspectiva": rav.perspectiva or "",
        "resultado_final": rav.resultado_final or "",
    }

    # Write JS generator
    js_path = "/tmp/gerar_rav.mjs"
    out_path = f"/tmp/rav_{id}.docx"

    with open(js_path, "w") as f:
        f.write(gerar_script(dados, out_path))

    result = subprocess.run(["node", js_path], capture_output=True, text=True)
    if result.returncode != 0:
        flash(f"Erro ao gerar documento: {result.stderr[:200]}", "danger")
        return redirect(url_for("rav.index"))

    nome_arquivo = f"RAv_{aluno.nome.replace(' ','_')}_{rav.bimestre}Bim_{rav.ano_letivo}.docx"
    return send_file(out_path, as_attachment=True, download_name=nome_arquivo,
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def gerar_script(d, out_path):
    bim_label = f"{d['bimestre']}º Bimestre"
    ord_bim = {1:"primeiro",2:"segundo",3:"terceiro",4:"quarto"}.get(d['bimestre'],'primeiro')

    # Build the descriptive paragraph text
    texto_b = f"""Este relatório sintetiza as observações realizadas durante e com base nos objetivos do {bim_label}, que teve início em {d['data_inicio_bim']} e se encerrou no dia {d['data_fim_bim']}. O presente instrumento visa compartilhar o processo de desenvolvimento e aprendizagens do(a) estudante {d['aluno_nome']}. {d['comportamento']} {d['linguagem_leitura']} {d['linguagem_escrita']} {d['gramatica']} {d['matematica']} {d['ciencias']} {d['historia']} {d['geografia']} {d['artes']} {d['educacao_fisica']} {d['sintese']} {d['perspectiva']}"""

    resultado = d['resultado_final']

    atend = d['tipo_atendimento']
    classe_x   = "X" if atend == "classe_comum" else " "
    superacao_x = "X" if atend == "superacao" else " "
    superacao_r_x = "X" if atend == "superacao_reduzida" else " "

    org_nao = "x" if d['org_curricular'] == "nao" else " "
    org_sim = "x" if d['org_curricular'] == "sim" else " "
    org_parc = "x" if d['org_curricular'] == "parcialmente" else " "

    res_cursando = "X" if resultado == "cursando" else " "
    res_progressao = "X" if resultado == "progressao" else " "
    res_avanco = "X" if resultado == "avanco" else " "
    res_aprovado = "X" if resultado == "aprovado" else " "
    res_reprovado = "X" if resultado == "reprovado" else " "
    res_abandono = "X" if resultado == "abandono" else " "

    def_nao = "X" if d['deficiencia'] == "não" else " "
    def_sim = "X" if d['deficiencia'] == "sim" else " "
    adeq_nao = "X" if d['adequacao'] == "não" else " "
    adeq_sim = "X" if d['adequacao'] == "sim" else " "
    temp_nao = "X" if d['temporalidade'] == "não" else " "
    temp_sim = "X" if d['temporalidade'] == "sim" else " "
    sala_nao = "X" if d['sala_recursos'] == "não" else " "
    sala_sim = "X" if d['sala_recursos'] == "sim" else " "
    sup_nao  = "X" if d['superacao'] == "não" else " "
    sup_sim  = "X" if d['superacao'] == "sim" else " "

    return f"""
import {{ Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
         AlignmentType, BorderStyle, WidthType, VerticalAlign, ShadingType }} from 'docx';
import fs from 'fs';

const border = {{ style: BorderStyle.SINGLE, size: 4, color: "000000" }};
const borders = {{ top: border, bottom: border, left: border, right: border }};
const noBorder = {{ style: BorderStyle.NONE, size: 0, color: "FFFFFF" }};
const noBorders = {{ top: noBorder, bottom: noBorder, left: noBorder, right: noBorder }};
const TW = WidthType.DXA;
const W = 9640; // content width DXA (A4 narrow margins)

const cell = (text, opts={{}}) => new TableCell({{
  borders,
  width: {{ size: opts.w || W, type: TW }},
  columnSpan: opts.span || 1,
  shading: opts.shade ? {{ fill: opts.shade, type: ShadingType.CLEAR }} : undefined,
  verticalAlign: VerticalAlign.CENTER,
  margins: {{ top: 40, bottom: 40, left: 80, right: 80 }},
  children: [new Paragraph({{
    alignment: opts.align || AlignmentType.LEFT,
    children: [new TextRun({{ text, font: "Times New Roman", size: opts.size || 18,
      bold: !!opts.bold }})]
  }})]
}});

const row = (...cells) => new TableRow({{ children: cells }});

const labelCell = (label, w) => new TableCell({{
  borders, width: {{ size: w, type: TW }},
  margins: {{ top: 40, bottom: 40, left: 80, right: 80 }},
  children: [new Paragraph({{ children: [
    new TextRun({{ text: label, font: "Times New Roman", size: 18 }})
  ]}})]
}});

const para = (text, opts={{}}) => new Paragraph({{
  alignment: opts.align || AlignmentType.JUSTIFIED,
  spacing: {{ before: 40, after: 40, line: 240 }},
  children: [new TextRun({{ text, font: "Times New Roman", size: 18, bold: !!opts.bold }})]
}});

const sectionLabel = (letter) => new TableCell({{
  borders,
  width: {{ size: 500, type: TW }},
  rowSpan: 1,
  shading: {{ fill: "DDDDDD", type: ShadingType.CLEAR }},
  verticalAlign: VerticalAlign.CENTER,
  margins: {{ top: 40, bottom: 40, left: 80, right: 80 }},
  children: [new Paragraph({{ alignment: AlignmentType.CENTER,
    children: [new TextRun({{ text: letter, font: "Times New Roman", size: 18, bold: true }})]
  }})]
}});

const doc = new Document({{
  sections: [{{
    properties: {{
      page: {{
        size: {{ width: 11906, height: 16838 }},
        margin: {{ top: 720, right: 720, bottom: 720, left: 720 }}
      }}
    }},
    children: [
      // Header
      new Paragraph({{ alignment: AlignmentType.CENTER, spacing: {{ before: 0, after: 60 }},
        children: [new TextRun({{ text: "SECRETARIA DE ESTADO DE EDUCAÇÃO DO DISTRITO FEDERAL", font: "Times New Roman", size: 18, bold: true }})] }}),
      new Paragraph({{ alignment: AlignmentType.CENTER, spacing: {{ before: 0, after: 60 }},
        children: [new TextRun({{ text: "SUBSECRETARIA DE EDUCAÇÃO BÁSICA", font: "Times New Roman", size: 18, bold: true }})] }}),
      new Paragraph({{ alignment: AlignmentType.CENTER, spacing: {{ before: 80, after: 40 }},
        children: [new TextRun({{ text: "REGISTRO DE AVALIAÇÃO - RAv", font: "Times New Roman", size: 20, bold: true }})] }}),
      new Paragraph({{ alignment: AlignmentType.CENTER, spacing: {{ before: 0, after: 40 }},
        children: [new TextRun({{ text: "Formulário 1: Descrição do Processo de Aprendizagem do Estudante", font: "Times New Roman", size: 18, bold: true }})] }}),
      new Paragraph({{ alignment: AlignmentType.CENTER, spacing: {{ before: 0, after: 120 }},
        children: [new TextRun({{ text: "Ensino Fundamental (Anos Iniciais)", font: "Times New Roman", size: 18, bold: true }})] }}),

      // Bloco A
      new Table({{
        width: {{ size: W, type: TW }}, columnWidths: [500, W-500],
        rows: [
          row(sectionLabel("A"), cell("Ano Letivo: {d['ano_letivo']}")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("Coordenação Regional de Ensino: {d['regional'].upper()}")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("Unidade Escolar: {d['escola']}")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell(f"Bloco: ({'X' if ord_bim in ['primeiro','segundo'] else ' '}) 1\u00ba Bloco  ({'X' if ord_bim in ['terceiro','quarto'] else ' '}) 2\u00ba Bloco")),
          new TableRow({{ children: [
            new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
            new TableCell({{ borders, width: {{ size: W-500, type: TW }},
              margins: {{ top: 40, bottom: 40, left: 80, right: 80 }},
              children: [new Paragraph({{ children: [
                new TextRun({{ text: "Ano: {d['ano_turma']}    Turma: {d['turma_nome']}    Turno: ( ) Matutino  (X) Vespertino  ( ) Integral", font: "Times New Roman", size: 18 }})
              ]}})]
            }})
          ]}}),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("Professor (a) Regente da turma: {d['professor_regente']}")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("Professor(a):")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("Estudante: {d['aluno_nome']}")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("Apresenta Deficiência ou TEA? ({def_nao}) não  ({def_sim}) sim")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("Houve adequação curricular? ({adeq_nao}) não  ({adeq_sim}) sim")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("Estudante indicado para temporalidade? ({temp_nao}) não  ({temp_sim}) sim")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("Está sendo atendido em Sala de Recursos? ({sala_nao}) não  ({sala_sim}) sim")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell('Estudante do Programa SuperAção "setado" no Sistema de Gestão i-Educar? ({sup_nao}) não  ({sup_sim}) sim')),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("Atendimento:")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("({classe_x}) Classe Comum com atendimento personalizado")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("({superacao_x}) Turma SuperAção")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("({superacao_r_x}) Turma SuperAção Reduzida")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("Foi aplicada a Organização Curricular específica do Programa Superação?")),
          row(new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
              cell("({org_nao}) não  ({org_sim}) sim  ({org_parc}) parcialmente")),
          new TableRow({{ children: [
            new TableCell({{ borders, width: {{ size: 500, type: TW }}, children: [new Paragraph({{ children: [] }})] }}),
            new TableCell({{ borders, width: {{ size: W-500, type: TW }},
              margins: {{ top: 40, bottom: 40, left: 80, right: 80 }},
              children: [new Paragraph({{ children: [
                new TextRun({{ text: "{bim_label}    Total de dias letivos: {d['total_dias']}    Total de Faltas: {d['total_faltas']}", font: "Times New Roman", size: 18, bold: true }})
              ]}})]
            }})
          ]}})
        ]
      }}),

      // Bloco B
      new Table({{
        width: {{ size: W, type: TW }}, columnWidths: [500, W-500],
        rows: [
          new TableRow({{ children: [
            sectionLabel("B"),
            new TableCell({{ borders, width: {{ size: W-500, type: TW }},
              margins: {{ top: 80, bottom: 80, left: 100, right: 80 }},
              children: [new Paragraph({{
                alignment: AlignmentType.JUSTIFIED,
                spacing: {{ line: 240 }},
                children: [new TextRun({{ text: `{texto_b.replace('`', "'").replace(chr(10), ' ')}`, font: "Times New Roman", size: 18 }})]
              }})]
            }})
          ]}})
        ]
      }}),

      // Bloco C
      new Table({{
        width: {{ size: W, type: TW }}, columnWidths: [500, W-500],
        rows: [
          row(sectionLabel("C"), cell("Local/Data: Brasília/DF, 29 de Abril de 2026."))
        ]
      }}),

      // Bloco D - assinaturas
      new Table({{
        width: {{ size: W, type: TW }}, columnWidths: [500, W-500],
        rows: [
          new TableRow({{ children: [
            sectionLabel("D"),
            new TableCell({{ borders, width: {{ size: W-500, type: TW }},
              margins: {{ top: 80, bottom: 80, left: 80, right: 80 }},
              children: [
                new Paragraph({{ spacing: {{ before: 40, after: 200 }}, children: [new TextRun({{ text: "{d['professor_regente'].upper()}", font: "Times New Roman", size: 18, bold: true }})] }}),
                new Paragraph({{ spacing: {{ before: 0, after: 120 }}, children: [new TextRun({{ text: "Assinatura/Matrícula da Professora Regente", font: "Times New Roman", size: 16 }})] }}),
                new Paragraph({{ spacing: {{ before: 200, after: 40 }}, children: [new TextRun({{ text: " ", font: "Times New Roman", size: 18 }})] }}),
                new Paragraph({{ spacing: {{ before: 0, after: 120 }}, children: [new TextRun({{ text: "Assinatura/Matrícula do(a) Coordenador(a) Pedagógico", font: "Times New Roman", size: 16 }})] }}),
                new Paragraph({{ spacing: {{ before: 200, after: 40 }}, children: [new TextRun({{ text: " ", font: "Times New Roman", size: 18 }})] }}),
                new Paragraph({{ spacing: {{ before: 0, after: 40 }}, children: [new TextRun({{ text: "Assinatura do(a) Pai/Mãe ou Responsável Legal", font: "Times New Roman", size: 16 }})] }}),
              ]
            }})
          ]}})
        ]
      }}),

      // Bloco E
      new Table({{
        width: {{ size: W, type: TW }}, columnWidths: [500, W-500],
        rows: [
          new TableRow({{ children: [
            sectionLabel("E"),
            new TableCell({{ borders, width: {{ size: W-500, type: TW }},
              margins: {{ top: 80, bottom: 80, left: 80, right: 80 }},
              children: [
                para("Resultado Final (Preencher somente ao final do 4º bimestre)", {{ bold: true }}),
                para("({res_cursando}) Cursando  ({res_progressao}) Progressão Continuada  ({res_avanco}) Avanço das Aprendizagens - Correção de Fluxo"),
                para("({res_aprovado}) Aprovado  ({res_reprovado}) Reprovado  ({res_abandono}) Abandono"),
              ]
            }})
          ]}})
        ]
      }}),
    ]
  }}]
}});

Packer.toBuffer(doc).then(buf => {{
  fs.writeFileSync("{out_path}", buf);
  console.log("OK");
}}).catch(e => {{ console.error(e.message); process.exit(1); }});
"""
