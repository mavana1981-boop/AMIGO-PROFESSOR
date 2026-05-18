from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models.models import Avaliacao, Nota, Turma, Aluno
from datetime import datetime

aval_bp = Blueprint("avaliacoes", __name__, url_prefix="/avaliacoes")

@aval_bp.route("/")
@login_required
def index():
    turma_id = request.args.get("turma_id", type=int)
    query = Avaliacao.query.filter_by(professor_id=current_user.id)
    if turma_id:
        query = query.filter_by(turma_id=turma_id)
    avaliacoes = query.order_by(Avaliacao.data_aplicacao.desc()).all()
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    return render_template("avaliacoes/index.html", avaliacoes=avaliacoes, turmas=turmas, turma_id=turma_id)

@aval_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    if request.method == "POST":
        av = Avaliacao(
            titulo=request.form["titulo"],
            tipo=request.form.get("tipo"),
            data_aplicacao=datetime.strptime(request.form["data_aplicacao"], "%Y-%m-%d").date() if request.form.get("data_aplicacao") else None,
            valor_total=request.form.get("valor_total", 10.0, type=float),
            descricao=request.form.get("descricao"),
            gabarito=request.form.get("gabarito"),
            bimestre=request.form.get("bimestre", type=int),
            professor_id=current_user.id,
            turma_id=request.form.get("turma_id", type=int),
        )
        db.session.add(av)
        db.session.commit()
        flash("Avaliação criada!", "success")
        return redirect(url_for("avaliacoes.index"))
    return render_template("avaliacoes/form.html", turmas=turmas, avaliacao=None)

@aval_bp.route("/notas/<int:id>", methods=["GET", "POST"])
@login_required
def notas(id):
    avaliacao = Avaliacao.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=avaliacao.turma_id).order_by(Aluno.nome).all()
    if request.method == "POST":
        for aluno in alunos:
            nota_val = request.form.get(f"nota_{aluno.id}", type=float)
            comentario = request.form.get(f"comentario_{aluno.id}", "")
            nota_obj = Nota.query.filter_by(aluno_id=aluno.id, avaliacao_id=id).first()
            if nota_obj:
                nota_obj.nota = nota_val
                nota_obj.comentario = comentario
            else:
                db.session.add(Nota(nota=nota_val, comentario=comentario, aluno_id=aluno.id, avaliacao_id=id))
        db.session.commit()
        flash("Notas salvas!", "success")
        return redirect(url_for("avaliacoes.index"))
    notas_map = {n.aluno_id: n for n in Nota.query.filter_by(avaliacao_id=id).all()}
    return render_template("avaliacoes/notas.html", avaliacao=avaliacao, alunos=alunos, notas_map=notas_map)
