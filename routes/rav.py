from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db
from models.models import RegistroAvaliacao, Aluno, Turma
from datetime import datetime
import subprocess, os, json

rav_bp = Blueprint("rav", __name__, url_prefix="/rav")


@rav_bp.route("/")
@login_required
def index():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    turma_id = request.args.get("turma_id", type=int)
    ravs = RegistroAvaliacao.query.filter_by(professor_id=current_user.id)\
                                  .order_by(RegistroAvaliacao.criado_em.desc()).all()
    if turma_id:
        ravs = [r for r in ravs if r.aluno.turma_id == turma_id]
    return render_template("rav/index.html", ravs=ravs, turmas=turmas, turma_id=turma_id)


def get_alunos():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    alunos = []
    for t in turmas:
        alunos.extend(sorted(t.alunos, key=lambda a: a.nome))
    return sorted(alunos, key=lambda a: a.nome)


@rav_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    alunos = get_alunos()
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

    bim_num   = rav.bimestre
    bim_label = f"{bim_num}º Bimestre"
    bloco1    = bim_num in [1, 2]

    # Check boxes
    def xou(cond): return "X" if cond else " "

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
    bloco_x  = xou(bloco1)
    bloco2_x = xou(not bloco1)

    # Build body text
    partes = [
        f"Este relatorio sintetiza as observacoes realizadas durante e com base nos objetivos do {bim_label}, "
        f"que teve inicio em {rav.data_inicio_bim} e se encerrou no dia {rav.data_fim_bim}. "
        f"O presente instrumento visa compartilhar o processo de desenvolvimento e aprendizagens do(a) estudante {aluno.nome}.",
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
    # Escape for JS template literal
    texto_b = texto_b.replace("\\", "\\\\").replace("`", "'").replace("${", "\\${")

    regional = (professor.regional or "PLANO PILOTO").upper()
    escola   = professor.escola or ""
    ano_turma = turma.serie or f"{turma.ano}\u00ba Ano"
    turma_nome = turma.nome
    prof_nome  = professor.nome

    out_path = f"/tmp/rav_{id}.docx"
    js_path  = f"/tmp/gerar_rav_{id}.mjs"

    script = f"""
import {{ Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
         AlignmentType, BorderStyle, WidthType, VerticalAlign, ShadingType }} from 'docx';
import fs from 'fs';

const S = BorderStyle.SINGLE;
const brd = (sz=4,clr="000000") => ({{ style: S, size: sz, color: clr }});
const borders = {{ top: brd(), bottom: brd(), left: brd(), right: brd() }};
const TW = WidthType.DXA;
const W  = 9640;

const txt = (text, opts={{}}) => new TextRun({{
  text: String(text),
  font: "Times New Roman",
  size: opts.size || 18,
  bold: !!opts.bold
}});

const p = (text, opts={{}}) => new Paragraph({{
  alignment: opts.align !== undefined ? opts.align : AlignmentType.JUSTIFIED,
  spacing: {{ line: 240, before: 30, after: 30 }},
  children: [ txt(text, opts) ]
}});

const cell = (content, w, opts={{}}) => {{
  const children = typeof content === 'string'
    ? [p(content, opts)]
    : content;
  return new TableCell({{
    borders, width: {{ size: w, type: TW }},
    columnSpan: opts.span || 1,
    verticalAlign: VerticalAlign.CENTER,
    margins: {{ top: 40, bottom: 40, left: 80, right: 80 }},
    children
  }});
}};

const letra = (l) => new TableCell({{
  borders,
  width: {{ size: 500, type: TW }},
  shading: {{ fill: "DDDDDD", type: ShadingType.CLEAR }},
  verticalAlign: VerticalAlign.CENTER,
  margins: {{ top: 40, bottom: 40, left: 80, right: 80 }},
  children: [new Paragraph({{
    alignment: AlignmentType.CENTER,
    children: [txt(l, {{ bold: true }})]
  }})]
}});

const row = (...cells) => new TableRow({{ children: cells }});
const emptyLetra = () => new TableCell({{
  borders, width: {{ size: 500, type: TW }},
  margins: {{ top: 20, bottom: 20, left: 80, right: 80 }},
  children: [new Paragraph({{ children: [] }})]
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
      new Paragraph({{ alignment: AlignmentType.CENTER, spacing: {{ before:0, after:60 }},
        children: [txt("SECRETARIA DE ESTADO DE EDUCACAO DO DISTRITO FEDERAL", {{ bold:true }})] }}),
      new Paragraph({{ alignment: AlignmentType.CENTER, spacing: {{ before:0, after:60 }},
        children: [txt("SUBSECRETARIA DE EDUCACAO BASICA", {{ bold:true }})] }}),
      new Paragraph({{ alignment: AlignmentType.CENTER, spacing: {{ before:60, after:40 }},
        children: [txt("REGISTRO DE AVALIACAO - RAv", {{ bold:true, size:20 }})] }}),
      new Paragraph({{ alignment: AlignmentType.CENTER, spacing: {{ before:0, after:40 }},
        children: [txt("Formulario 1: Descricao do Processo de Aprendizagem do Estudante", {{ bold:true }})] }}),
      new Paragraph({{ alignment: AlignmentType.CENTER, spacing: {{ before:0, after:120 }},
        children: [txt("Ensino Fundamental (Anos Iniciais)", {{ bold:true }})] }}),

      new Table({{
        width: {{ size: W, type: TW }}, columnWidths: [500, W-500],
        rows: [
          row(letra("A"), cell("Ano Letivo: {rav.ano_letivo}", W-500)),
          row(emptyLetra(), cell("Coordenacao Regional de Ensino: {regional}", W-500)),
          row(emptyLetra(), cell("Unidade Escolar: {escola}", W-500)),
          row(emptyLetra(), cell("Bloco: ({bloco_x}) 1 Bloco  ({bloco2_x}) 2 Bloco", W-500)),
          row(emptyLetra(), cell("Ano: {ano_turma}    Turma: {turma_nome}    Turno: ( ) Matutino  (X) Vespertino  ( ) Integral", W-500)),
          row(emptyLetra(), cell("Professor(a) Regente da turma: {prof_nome}", W-500)),
          row(emptyLetra(), cell("Professor(a): Davidson Bispo da Silva", W-500)),
          row(emptyLetra(), cell("Estudante: {aluno.nome}", W-500)),
          row(emptyLetra(), cell("Apresenta Deficiencia ou TEA? ({def_nao}) nao  ({def_sim}) sim", W-500)),
          row(emptyLetra(), cell("Houve adequacao curricular? ({adeq_nao}) nao  ({adeq_sim}) sim", W-500)),
          row(emptyLetra(), cell("Estudante indicado para temporalidade? ({temp_nao}) nao  ({temp_sim}) sim", W-500)),
          row(emptyLetra(), cell("Esta sendo atendido em Sala de Recursos? ({sala_nao}) nao  ({sala_sim}) sim", W-500)),
          row(emptyLetra(), cell("Estudante do Programa SuperAcao no Sistema de Gestao i-Educar? ({sup_nao}) nao  ({sup_sim}) sim", W-500)),
          row(emptyLetra(), cell("Atendimento:", W-500)),
          row(emptyLetra(), cell("({cl_x}) Classe Comum com atendimento personalizado", W-500)),
          row(emptyLetra(), cell("({sa_x}) Turma SuperAcao", W-500)),
          row(emptyLetra(), cell("({sr_x}) Turma SuperAcao Reduzida", W-500)),
          row(emptyLetra(), cell("Foi aplicada a Organizacao Curricular especifica do Programa Superacao?", W-500)),
          row(emptyLetra(), cell("({org_n}) nao  ({org_s}) sim  ({org_p}) parcialmente", W-500)),
          row(emptyLetra(), new TableCell({{
            borders, width: {{ size: W-500, type: TW }},
            margins: {{ top: 40, bottom: 40, left: 80, right: 80 }},
            children: [new Paragraph({{ children: [
              txt("{bim_label}    Total de dias letivos: {rav.total_dias}    Total de Faltas: {rav.total_faltas}", {{ bold:true }})
            ]}})]
          }}),
        ]
      }}),

      new Table({{
        width: {{ size: W, type: TW }}, columnWidths: [500, W-500],
        rows: [
          new TableRow({{ children: [
            letra("B"),
            new TableCell({{
              borders, width: {{ size: W-500, type: TW }},
              margins: {{ top: 80, bottom: 80, left: 100, right: 80 }},
              children: [new Paragraph({{
                alignment: AlignmentType.JUSTIFIED,
                spacing: {{ line: 240 }},
                children: [txt(`{texto_b}`)]
              }})]
            }})
          ]}})
        ]
      }}),

      new Table({{
        width: {{ size: W, type: TW }}, columnWidths: [500, W-500],
        rows: [ row(letra("C"), cell("Local/Data: Brasilia/DF, 29 de Abril de 2026.", W-500)) ]
      }}),

      new Table({{
        width: {{ size: W, type: TW }}, columnWidths: [500, W-500],
        rows: [
          new TableRow({{ children: [
            letra("D"),
            new TableCell({{
              borders, width: {{ size: W-500, type: TW }},
              margins: {{ top: 80, bottom: 80, left: 80, right: 80 }},
              children: [
                p("{prof_nome.upper()}", {{ bold:true }}),
                p("Assinatura/Matricula da Professora Regente", {{ size:16 }}),
                p(" "),
                p("Assinatura/Matricula do(a) Coordenador(a) Pedagogico", {{ size:16 }}),
                p(" "),
                p("Assinatura do(a) Pai/Mae ou Responsavel Legal", {{ size:16 }}),
              ]
            }})
          ]}})
        ]
      }}),

      new Table({{
        width: {{ size: W, type: TW }}, columnWidths: [500, W-500],
        rows: [
          new TableRow({{ children: [
            letra("E"),
            new TableCell({{
              borders, width: {{ size: W-500, type: TW }},
              margins: {{ top: 80, bottom: 80, left: 80, right: 80 }},
              children: [
                p("Resultado Final (Preencher somente ao final do 4 bimestre)", {{ bold:true }}),
                p("({r_cur}) Cursando  ({r_pro}) Progressao Continuada  ({r_ava}) Avanco das Aprendizagens"),
                p("({r_apr}) Aprovado  ({r_rep}) Reprovado  ({r_aba}) Abandono"),
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
  console.log("OK:" + buf.length);
}}).catch(e => {{ console.error("ERRO:" + e.message); process.exit(1); }});
"""

    with open(js_path, "w", encoding="utf-8") as f:
        f.write(script)

    result = subprocess.run(
        ["node", "--input-type=module"],
        input=open(js_path).read(),
        capture_output=True, text=True, cwd="/home/claude/.npm-global/lib/node_modules"
    )

    if result.returncode != 0 or not os.path.exists(out_path):
        flash(f"Erro ao gerar .docx: {(result.stderr or result.stdout)[:300]}", "danger")
        return redirect(url_for("rav.index"))

    nome = f"RAv_{aluno.nome.replace(' ','_')}_{bim_num}Bim_{rav.ano_letivo}.docx"
    return send_file(out_path, as_attachment=True, download_name=nome,
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
