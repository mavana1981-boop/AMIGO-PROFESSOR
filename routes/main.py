from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models.models import Turma, Aluno, PlanoAula, Avaliacao, EventoCalendario, Frequencia
from datetime import date, timedelta
from app import db
from sqlalchemy import func

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    from flask_login import current_user
    if current_user.is_authenticated:
        return __import__('flask').redirect(__import__('flask').url_for('main.dashboard'))
    return __import__('flask').redirect(__import__('flask').url_for('auth.login'))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)

    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    total_alunos = db.session.query(func.count(Aluno.id)).join(Turma).filter(
        Turma.professor_id == current_user.id
    ).scalar() or 0

    planos_semana = PlanoAula.query.filter(
        PlanoAula.professor_id == current_user.id,
        PlanoAula.data_aula >= inicio_semana,
        PlanoAula.data_aula <= fim_semana
    ).count()

    proximos_eventos = EventoCalendario.query.filter(
        EventoCalendario.professor_id == current_user.id,
        EventoCalendario.data_inicio >= hoje
    ).order_by(EventoCalendario.data_inicio).limit(5).all()

    avaliacoes_pendentes = Avaliacao.query.filter(
        Avaliacao.professor_id == current_user.id,
        Avaliacao.data_aplicacao >= hoje
    ).order_by(Avaliacao.data_aplicacao).limit(3).all()

    stats = {
        "total_turmas": len(turmas),
        "total_alunos": total_alunos,
        "planos_semana": planos_semana,
    }

    return render_template(
        "main/dashboard.html",
        stats=stats,
        turmas=turmas,
        proximos_eventos=proximos_eventos,
        avaliacoes_pendentes=avaliacoes_pendentes,
        hoje=hoje,
    )
