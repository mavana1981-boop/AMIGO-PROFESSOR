from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db
from models.models import AcompanhamentoPedagogico, Turma, Aluno
from datetime import datetime, date
import io

ped_bp = Blueprint("pedagogico", __name__, url_prefix="/pedagogico")


def get_turmas():
    return Turma.query.filter_by(professor_id=current_user.id).all()


def get_todos_alunos():
    turmas = get_turmas()
    alunos = []
    for t in turmas:
        alunos.extend(sorted(t.alunos, key=lambda x: x.nome))
    return sorted(alunos, key=lambda x: x.nome)


@ped_bp.route("/")
@login_required
def index():
    turma_id = request.args.get("turma_id", type=int)
    tipo     = request.args.get("tipo", "")
    turmas   = get_turmas()
    query    = AcompanhamentoPedagogico.query.filter_by(professor_id=current_user.id)
    if tipo:
        query = query.filter_by(tipo=tipo)
    registros = query.order_by(AcompanhamentoPedagogico.data.desc()).all()
    if turma_id:
        registros = [r for r in registros
                     if r.aluno_id is None or (r.aluno and r.aluno.turma_id == turma_id)
                     or r.turma_id == turma_id]
    return render_template("pedagogico/index.html",
        registros=registros, turmas=turmas, turma_id=turma_id, tipo=tipo, hoje=date.today())


@ped_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    turmas   = get_turmas()
    alunos   = get_todos_alunos()
    aluno_id = request.args.get("aluno_id", type=int)
    turma_id_pre = request.args.get("turma_id", type=int)

    if request.method == "POST":
        aluno_sel = request.form.get("aluno_id", "")
        turma_sel = request.form.get("turma_id_form", type=int)

        # "todos" = registro para toda a turma
        if aluno_sel in ("", "todos"):
            aluno_id_val = None
            turma_id_val = turma_sel
        else:
            aluno_id_val = int(aluno_sel)
            turma_id_val = None

        reg = AcompanhamentoPedagogico(
            data        = datetime.strptime(request.form["data"], "%Y-%m-%d").date(),
            tipo        = request.form.get("tipo", "observacao"),
            descricao   = request.form["descricao"],
            encaminhamento  = request.form.get("encaminhamento", ""),
            status          = request.form.get("status", "aberto"),
            aluno_id        = aluno_id_val,
            turma_id        = turma_id_val,
            professor_id    = current_user.id,
        )
        db.session.add(reg)
        db.session.commit()
        flash("Registro salvo!", "success")
        return redirect(url_for("pedagogico.index"))

    return render_template("pedagogico/form.html",
        turmas=turmas, alunos=alunos, registro=None,
        aluno_id=aluno_id, turma_id_pre=turma_id_pre, today=date.today())


@ped_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    reg    = AcompanhamentoPedagogico.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    turmas = get_turmas()
    alunos = get_todos_alunos()

    if request.method == "POST":
        aluno_sel = request.form.get("aluno_id", "")
        turma_sel = request.form.get("turma_id_form", type=int)
        if aluno_sel in ("", "todos"):
            reg.aluno_id = None
            reg.turma_id = turma_sel
        else:
            reg.aluno_id = int(aluno_sel)
            reg.turma_id = None
        reg.data           = datetime.strptime(request.form["data"], "%Y-%m-%d").date()
        reg.tipo           = request.form.get("tipo", "observacao")
        reg.descricao      = request.form["descricao"]
        reg.encaminhamento = request.form.get("encaminhamento", "")
        reg.status         = request.form.get("status", "aberto")
        db.session.commit()
        flash("Registro atualizado!", "success")
        return redirect(url_for("pedagogico.index"))

    return render_template("pedagogico/form.html",
        turmas=turmas, alunos=alunos, registro=reg,
        aluno_id=reg.aluno_id, turma_id_pre=reg.turma_id, today=date.today())


@ped_bp.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    reg = AcompanhamentoPedagogico.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    db.session.delete(reg)
    db.session.commit()
    flash("Registro excluído.", "info")
    return redirect(url_for("pedagogico.index"))

from flask import jsonify
import calendar as cal_mod_ped


@ped_bp.route("/api/mes")
@login_required
def api_mes():
    hoje     = date.today()
    ano      = request.args.get("ano",  hoje.year,  type=int)
    mes      = request.args.get("mes",  hoje.month, type=int)
    turma_id = request.args.get("turma_id", type=int)

    q = AcompanhamentoPedagogico.query.filter_by(professor_id=current_user.id).filter(
        db.extract("year",  AcompanhamentoPedagogico.data) == ano,
        db.extract("month", AcompanhamentoPedagogico.data) == mes,
    )
    regs = q.all()
    if turma_id:
        regs = [r for r in regs if r.aluno and r.aluno.turma_id == turma_id]

    return jsonify([{
        "id":       r.id,
        "data":     r.data.strftime("%Y-%m-%d"),
        "data_fmt": r.data.strftime("%d/%m/%Y"),
        "tipo":     r.tipo or "observacao",
        "aluno":    r.aluno.nome if r.aluno else None,
        "descricao":r.descricao or "",
        "encaminhamento": r.encaminhamento or "",
        "status":   r.status or "",
    } for r in regs])


@ped_bp.route("/relatorio-preview")
@login_required
def relatorio_preview():
    hoje     = date.today()
    tipo     = request.args.get("tipo", "mes")
    turma_id = request.args.get("turma_id", type=int)
    turmas   = get_turmas()
    t_nome   = next((t.nome for t in turmas if t.id==turma_id), "Todas as turmas") if turma_id else "Todas as turmas"

    if tipo == "mes":
        ano   = request.args.get("ano", hoje.year, type=int)
        meses = [int(m) for m in request.args.get("meses", str(hoje.month)).split(",") if m]
        datas = [(date(ano,m,1), date(ano,m,cal_mod_ped.monthrange(ano,m)[1])) for m in meses]
        MNOMES=['','Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
        label = f"{', '.join(MNOMES[m] for m in meses)}/{ano}"
    elif tipo == "ano":
        ano   = request.args.get("ano", hoje.year, type=int)
        datas = [(date(ano,1,1), date(ano,12,31))]
        label = f"Ano Letivo {ano}"
    else:
        di    = datetime.strptime(request.args.get("data_ini", hoje.replace(day=1).isoformat()), "%Y-%m-%d").date()
        df    = datetime.strptime(request.args.get("data_fim", hoje.isoformat()), "%Y-%m-%d").date()
        datas = [(di, df)]
        label = f"{di.strftime('%d/%m/%Y')} a {df.strftime('%d/%m/%Y')}"

    registros = []
    for (di, df) in datas:
        q = AcompanhamentoPedagogico.query.filter(
            AcompanhamentoPedagogico.professor_id == current_user.id,
            AcompanhamentoPedagogico.data >= di,
            AcompanhamentoPedagogico.data <= df,
        )
        rs = q.order_by(AcompanhamentoPedagogico.data).all()
        if turma_id:
            rs = [r for r in rs if r.aluno and r.aluno.turma_id == turma_id]
        registros.extend(rs)

    return render_template("pedagogico/relatorio_preview.html",
        registros=registros, label=label, turma_nome=t_nome,
        prof_nome=current_user.nome, escola=current_user.escola or "")
