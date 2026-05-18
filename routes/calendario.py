from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models.models import EventoCalendario
from datetime import datetime

cal_bp = Blueprint("calendario", __name__, url_prefix="/calendario")

@cal_bp.route("/")
@login_required
def index():
    eventos = EventoCalendario.query.filter_by(professor_id=current_user.id).order_by(EventoCalendario.data_inicio).all()
    return render_template("calendario/index.html", eventos=eventos)

@cal_bp.route("/api/eventos")
@login_required
def api_eventos():
    eventos = EventoCalendario.query.filter_by(professor_id=current_user.id).all()
    return jsonify([{
        "id": e.id,
        "title": e.titulo,
        "start": e.data_inicio.isoformat(),
        "end": e.data_fim.isoformat() if e.data_fim else e.data_inicio.isoformat(),
        "color": e.cor,
        "extendedProps": {"tipo": e.tipo, "descricao": e.descricao}
    } for e in eventos])

@cal_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if request.method == "POST":
        ev = EventoCalendario(
            titulo=request.form["titulo"],
            data_inicio=datetime.strptime(request.form["data_inicio"], "%Y-%m-%d").date(),
            data_fim=datetime.strptime(request.form["data_fim"], "%Y-%m-%d").date() if request.form.get("data_fim") else None,
            tipo=request.form.get("tipo"),
            descricao=request.form.get("descricao"),
            cor=request.form.get("cor", "#3B82F6"),
            professor_id=current_user.id,
        )
        db.session.add(ev)
        db.session.commit()
        flash("Evento adicionado!", "success")
        return redirect(url_for("calendario.index"))
    return render_template("calendario/form.html", evento=None)

@cal_bp.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    ev = EventoCalendario.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    db.session.delete(ev)
    db.session.commit()
    flash("Evento removido.", "info")
    return redirect(url_for("calendario.index"))
