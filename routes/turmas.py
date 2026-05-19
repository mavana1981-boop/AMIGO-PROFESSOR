from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models.models import Turma, Aluno
from datetime import date, datetime

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
        flash(f"Turma '{turma.nome}' criada!", "success")
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
        turma.nome  = request.form["nome"]
        turma.ano   = request.form.get("ano", type=int)
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


# ── Alunos ──────────────────────────────────────────────────────────────────

def salvar_aluno_form(aluno, form):
    """Salva todos os campos do formulário no objeto aluno."""
    aluno.nome                    = form.get("nome", "").strip()
    aluno.matricula               = form.get("matricula", "").strip()
    aluno.responsavel             = form.get("responsavel", "").strip()
    aluno.contato                 = form.get("contato", "").strip()
    # RAv — bloco A
    aluno.apresenta_deficiencia   = form.get("apresenta_deficiencia") == "sim"
    aluno.tipo_deficiencia        = form.get("tipo_deficiencia", "").strip()
    aluno.adequacao_curricular    = form.get("adequacao_curricular") == "sim"
    aluno.indicado_temporalidade  = form.get("indicado_temporalidade") == "sim"
    aluno.sala_recursos           = form.get("sala_recursos") == "sim"
    aluno.programa_superacao      = form.get("programa_superacao") == "sim"
    aluno.tipo_atendimento        = form.get("tipo_atendimento", "")
    aluno.org_curricular_superacao = form.get("org_curricular_superacao", "nao")


@turmas_bp.route("/<int:turma_id>/alunos/novo", methods=["GET", "POST"])
@login_required
def novo_aluno(turma_id):
    turma = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    if request.method == "POST":
        aluno = Aluno(turma_id=turma_id)
        salvar_aluno_form(aluno, request.form)
        db.session.add(aluno)
        db.session.commit()
        flash(f"Aluno '{aluno.nome}' adicionado!", "success")
        return redirect(url_for("turmas.detalhe", id=turma_id))
    return render_template("turmas/novo_aluno.html", turma=turma, aluno=None)


@turmas_bp.route("/alunos/<int:aluno_id>/editar", methods=["GET", "POST"])
@login_required
def editar_aluno(aluno_id):
    aluno = Aluno.query.get_or_404(aluno_id)
    turma = Turma.query.filter_by(id=aluno.turma_id, professor_id=current_user.id).first_or_404()
    if request.method == "POST":
        salvar_aluno_form(aluno, request.form)
        db.session.commit()
        flash(f"Dados de {aluno.nome} atualizados!", "success")
        return redirect(url_for("turmas.detalhe", id=turma.id))
    return render_template("turmas/novo_aluno.html", turma=turma, aluno=aluno)


@turmas_bp.route("/alunos/<int:aluno_id>/excluir", methods=["POST"])
@login_required
def excluir_aluno(aluno_id):
    aluno = Aluno.query.get_or_404(aluno_id)
    turma_id = aluno.turma_id
    db.session.delete(aluno)
    db.session.commit()
    flash(f"Aluno '{aluno.nome}' removido.", "info")
    return redirect(url_for("turmas.detalhe", id=turma_id))
