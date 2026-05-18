from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models.models import Turma, Aluno, Frequencia
from datetime import date, datetime

freq_bp = Blueprint("frequencia", __name__, url_prefix="/frequencia")


@freq_bp.route("/")
@login_required
def index():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    return render_template("frequencia/index.html", turmas=turmas)


@freq_bp.route("/registrar/<int:turma_id>", methods=["GET", "POST"])
@login_required
def registrar(turma_id):
    turma = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()
    hoje = date.today()

    if request.method == "POST":
        data_str = request.form.get("data")
        try:
            data_aula = datetime.strptime(data_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            data_aula = hoje

        for aluno in alunos:
            status = request.form.get(f"status_{aluno.id}", "presente")
            obs = request.form.get(f"obs_{aluno.id}", "")

            freq_existente = Frequencia.query.filter_by(
                aluno_id=aluno.id, data=data_aula
            ).first()

            if freq_existente:
                freq_existente.status = status
                freq_existente.observacao = obs
            else:
                freq = Frequencia(
                    data=data_aula,
                    status=status,
                    observacao=obs,
                    aluno_id=aluno.id,
                    turma_id=turma_id,
                    professor_id=current_user.id,
                )
                db.session.add(freq)

        db.session.commit()
        flash("Frequência registrada com sucesso!", "success")
        return redirect(url_for("frequencia.registrar", turma_id=turma_id))

    freq_hoje = {f.aluno_id: f for f in Frequencia.query.filter_by(
        turma_id=turma_id, data=hoje
    ).all()}

    return render_template(
        "frequencia/registrar.html",
        turma=turma,
        alunos=alunos,
        hoje=hoje,
        freq_hoje=freq_hoje,
    )


@freq_bp.route("/historico/<int:turma_id>")
@login_required
def historico(turma_id):
    turma = Turma.query.filter_by(id=turma_id, professor_id=current_user.id).first_or_404()
    alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()

    mes = request.args.get("mes", date.today().month, type=int)
    ano = request.args.get("ano", date.today().year, type=int)

    frequencias = Frequencia.query.filter_by(turma_id=turma_id).filter(
        db.extract("month", Frequencia.data) == mes,
        db.extract("year", Frequencia.data) == ano,
    ).all()

    return render_template(
        "frequencia/historico.html",
        turma=turma,
        alunos=alunos,
        frequencias=frequencias,
        mes=mes,
        ano=ano,
    )
