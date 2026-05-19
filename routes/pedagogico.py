from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models.models import AcompanhamentoPedagogico, Turma, Aluno
from datetime import datetime

ped_bp = Blueprint("pedagogico", __name__, url_prefix="/pedagogico")


def get_todos_alunos():
    """Retorna todos os alunos de todas as turmas do professor logado."""
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    alunos = []
    for t in turmas:
        for a in sorted(t.alunos, key=lambda x: x.nome):
            alunos.append(a)
    return sorted(alunos, key=lambda x: x.nome)


@ped_bp.route("/")
@login_required
def index():
    turma_id = request.args.get("turma_id", type=int)
    tipo     = request.args.get("tipo")
    turmas   = Turma.query.filter_by(professor_id=current_user.id).all()
    query    = AcompanhamentoPedagogico.query.filter_by(professor_id=current_user.id)
    if tipo:
        query = query.filter_by(tipo=tipo)
    registros = query.order_by(AcompanhamentoPedagogico.data.desc()).all()
    if turma_id:
        registros = [r for r in registros if r.aluno.turma_id == turma_id]
    return render_template("pedagogico/index.html", registros=registros, turmas=turmas, turma_id=turma_id, tipo=tipo)


@ped_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    alunos   = get_todos_alunos()
    turmas   = Turma.query.filter_by(professor_id=current_user.id).all()
    aluno_id = request.args.get("aluno_id", type=int)

    if request.method == "POST":
        reg = AcompanhamentoPedagogico(
            data          = datetime.strptime(request.form["data"], "%Y-%m-%d").date(),
            tipo          = request.form.get("tipo"),
            descricao     = request.form["descricao"],
            encaminhamento= request.form.get("encaminhamento"),
            status        = request.form.get("status", "aberto"),
            aluno_id      = request.form.get("aluno_id", type=int),
            professor_id  = current_user.id,
        )
        db.session.add(reg)
        db.session.commit()
        flash("Registro pedagógico salvo!", "success")
        return redirect(url_for("pedagogico.index"))

    return render_template("pedagogico/form.html", turmas=turmas, alunos=alunos, aluno_id=aluno_id)


@ped_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    reg    = AcompanhamentoPedagogico.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    alunos = get_todos_alunos()
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()

    if request.method == "POST":
        reg.data           = datetime.strptime(request.form["data"], "%Y-%m-%d").date()
        reg.tipo           = request.form.get("tipo")
        reg.descricao      = request.form["descricao"]
        reg.encaminhamento = request.form.get("encaminhamento")
        reg.status         = request.form.get("status", "aberto")
        reg.aluno_id       = request.form.get("aluno_id", type=int)
        db.session.commit()
        flash("Registro atualizado!", "success")
        return redirect(url_for("pedagogico.index"))

    return render_template("pedagogico/form.html", turmas=turmas, alunos=alunos, aluno_id=reg.aluno_id, reg=reg)
