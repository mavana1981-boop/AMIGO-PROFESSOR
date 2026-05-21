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
        registros=registros, turmas=turmas, turma_id=turma_id, tipo=tipo)


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
