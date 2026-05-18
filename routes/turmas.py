from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models.models import Turma, Aluno
from datetime import date

turmas_bp = Blueprint("turmas", __name__, url_prefix="/turmas")


@turmas_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    if request.method == "POST":
        turma = Turma(
            nome=request.form["nome"],
            ano=request.form.get("ano", date.today().year, type=int),
            serie=request.form.get("serie", ""),
            professor_id=current_user.id,
        )
        db.session.add(turma)
        db.session.commit()
        flash(f"Turma '{turma.nome}' criada com sucesso!", "success")
        return redirect(url_for("turmas.detalhe", id=turma.id))
    return render_template("turmas/form.html", turma=None)


@turmas_bp.route("/<int:id>")
@login_required
def detalhe(id):
    turma = Turma.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=id).order_by(Aluno.nome).all()
    return render_template("turmas/detalhe.html", turma=turma, alunos=alunos)


@turmas_bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar(id):
    turma = Turma.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    if request.method == "POST":
        turma.nome = request.form["nome"]
        turma.ano = request.form.get("ano", type=int)
        turma.serie = request.form.get("serie", "")
        db.session.commit()
        flash("Turma atualizada!", "success")
        return redirect(url_for("turmas.detalhe", id=turma.id))
    return render_template("turmas/form.html", turma=turma)


@turmas_bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
def excluir(id):
    turma = Turma.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    db.session.delete(turma)
    db.session.commit()
    flash("Turma excluída.", "info")
    return redirect(url_for("main.dashboard"))


# ── Alunos ────────────────────────────────────────────────────────────────────

@turmas_bp.route("/<int:turma_id>/alunos/novo", methods=["GET", "POST"])
@login_required
def novo_aluno(turma_id):
    turma = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    if request.method == "POST":
        aluno = Aluno(
            nome=request.form["nome"],
            matricula=request.form.get("matricula", ""),
            responsavel=request.form.get("responsavel", ""),
            contato=request.form.get("contato", ""),
            turma_id=turma_id,
        )
        db.session.add(aluno)
        db.session.commit()
        flash(f"Aluno '{aluno.nome}' adicionado!", "success")
        return redirect(url_for("turmas.detalhe", id=turma_id))
    return render_template("turmas/novo_aluno.html", turma=turma)


@turmas_bp.route("/alunos/<int:aluno_id>/excluir", methods=["POST"])
@login_required
def excluir_aluno(aluno_id):
    aluno = Aluno.query.get_or_404(aluno_id)
    turma_id = aluno.turma_id
    db.session.delete(aluno)
    db.session.commit()
    flash(f"Aluno '{aluno.nome}' removido.", "info")
    return redirect(url_for("turmas.detalhe", id=turma_id))
