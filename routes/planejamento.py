from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models.models import PlanoAula, Turma
from datetime import date, datetime

plan_bp = Blueprint("planejamento", __name__, url_prefix="/planejamento")


@plan_bp.route("/")
@login_required
def index():
    filtro = request.args.get("filtro", "semana")
    turma_id = request.args.get("turma_id", type=int)
    hoje = date.today()

    query = PlanoAula.query.filter_by(professor_id=current_user.id)

    if filtro == "semana":
        from datetime import timedelta
        inicio = hoje - __import__('datetime').timedelta(days=hoje.weekday())
        fim = inicio + __import__('datetime').timedelta(days=6)
        query = query.filter(PlanoAula.data_aula.between(inicio, fim))
    elif filtro == "mes":
        query = query.filter(
            db.extract("month", PlanoAula.data_aula) == hoje.month,
            db.extract("year", PlanoAula.data_aula) == hoje.year,
        )
    elif filtro == "bimestre":
        bim = (hoje.month - 1) // 3 + 1
        query = query.filter(PlanoAula.bimestre == bim)
    elif filtro == "semestre":
        sem = 1 if hoje.month <= 6 else 2
        query = query.filter(PlanoAula.semestre == sem)
    elif filtro == "ano":
        query = query.filter(db.extract("year", PlanoAula.data_aula) == hoje.year)

    if turma_id:
        query = query.filter_by(turma_id=turma_id)

    planos = query.order_by(PlanoAula.data_aula.desc()).all()
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()

    return render_template("planejamento/index.html", planos=planos, turmas=turmas, filtro=filtro, turma_id=turma_id)


@plan_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    if request.method == "POST":
        plano = PlanoAula(
            titulo=request.form["titulo"],
            data_aula=datetime.strptime(request.form["data_aula"], "%Y-%m-%d").date(),
            bimestre=request.form.get("bimestre", type=int),
            semestre=request.form.get("semestre", type=int),
            conteudo=request.form.get("conteudo"),
            objetivos=request.form.get("objetivos"),
            metodologia=request.form.get("metodologia"),
            recursos=request.form.get("recursos"),
            avaliacao_descricao=request.form.get("avaliacao_descricao"),
            professor_id=current_user.id,
            turma_id=request.form.get("turma_id", type=int),
        )
        db.session.add(plano)
        db.session.commit()
        flash("Plano de aula criado com sucesso!", "success")
        return redirect(url_for("planejamento.index"))
    return render_template("planejamento/form.html", turmas=turmas, plano=None)


@plan_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    plano = PlanoAula.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    if request.method == "POST":
        plano.titulo = request.form["titulo"]
        plano.data_aula = datetime.strptime(request.form["data_aula"], "%Y-%m-%d").date()
        plano.bimestre = request.form.get("bimestre", type=int)
        plano.semestre = request.form.get("semestre", type=int)
        plano.conteudo = request.form.get("conteudo")
        plano.objetivos = request.form.get("objetivos")
        plano.metodologia = request.form.get("metodologia")
        plano.recursos = request.form.get("recursos")
        plano.avaliacao_descricao = request.form.get("avaliacao_descricao")
        plano.turma_id = request.form.get("turma_id", type=int)
        db.session.commit()
        flash("Plano atualizado!", "success")
        return redirect(url_for("planejamento.index"))
    return render_template("planejamento/form.html", turmas=turmas, plano=plano)


@plan_bp.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    plano = PlanoAula.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    db.session.delete(plano)
    db.session.commit()
    flash("Plano excluído.", "info")
    return redirect(url_for("planejamento.index"))
