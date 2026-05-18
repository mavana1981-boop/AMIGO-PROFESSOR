from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models.models import AcompanhamentoPedagogico, Turma, Aluno
from datetime import datetime

ped_bp = Blueprint("pedagogico", __name__, url_prefix="/pedagogico")

@ped_bp.route("/")
@login_required
def index():
    turma_id = request.args.get("turma_id", type=int)
    tipo = request.args.get("tipo")
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    query = AcompanhamentoPedagogico.query.filter_by(professor_id=current_user.id)
    if tipo:
        query = query.filter_by(tipo=tipo)
    registros = query.order_by(AcompanhamentoPedagogico.data.desc()).all()
    if turma_id:
        registros = [r for r in registros if r.aluno.turma_id == turma_id]
    return render_template("pedagogico/index.html", registros=registros, turmas=turmas, turma_id=turma_id, tipo=tipo)

@ped_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    alunos = []
    for t in turmas:
        alunos.extend(t.alunos)
    if request.method == "POST":
        reg = AcompanhamentoPedagogico(
            data=datetime.strptime(request.form["data"], "%Y-%m-%d").date(),
            tipo=request.form.get("tipo"),
            descricao=request.form["descricao"],
            encaminhamento=request.form.get("encaminhamento"),
            status=request.form.get("status", "aberto"),
            aluno_id=request.form.get("aluno_id", type=int),
            professor_id=current_user.id,
        )
        db.session.add(reg)
        db.session.commit()
        flash("Registro pedagógico salvo!", "success")
        return redirect(url_for("pedagogico.index"))
    aluno_id = request.args.get("aluno_id", type=int)
    return render_template("pedagogico/form.html", turmas=turmas, alunos=alunos, aluno_id=aluno_id)
