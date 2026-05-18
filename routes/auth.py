from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db, login_manager
from models.models import Professor
import os

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "mavana1981@gmail.com")


@login_manager.user_loader
def load_user(user_id):
    return Professor.query.get(int(user_id))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        lembrar = request.form.get("lembrar") == "on"

        professor = Professor.query.filter_by(email=email).first()
        if professor and professor.check_senha(senha):
            login_user(professor, remember=lembrar)
            next_page = request.args.get("next")
            flash(f"Bem-vindo(a), {professor.nome.split()[0]}!", "success")
            return redirect(next_page or url_for("main.dashboard"))
        else:
            flash("E-mail ou senha incorretos. Tente novamente.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/usuarios")
@login_required
def usuarios():
    if current_user.email != ADMIN_EMAIL:
        flash("Acesso restrito ao administrador.", "danger")
        return redirect(url_for("main.dashboard"))
    professores = Professor.query.order_by(Professor.nome).all()
    return render_template("auth/usuarios.html", professores=professores)


@auth_bp.route("/usuarios/novo", methods=["GET", "POST"])
@login_required
def novo_usuario():
    if current_user.email != ADMIN_EMAIL:
        flash("Acesso restrito ao administrador.", "danger")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        escola = request.form.get("escola", "").strip()
        disciplina = request.form.get("disciplina", "").strip()

        if not nome or not email or not senha:
            flash("Preencha todos os campos obrigatórios.", "danger")
            return render_template("auth/novo_usuario.html")

        if len(senha) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return render_template("auth/novo_usuario.html")

        if Professor.query.filter_by(email=email).first():
            flash("Este e-mail já está cadastrado.", "danger")
            return render_template("auth/novo_usuario.html")

        professor = Professor(nome=nome, email=email, escola=escola, disciplina=disciplina)
        professor.set_senha(senha)
        db.session.add(professor)
        db.session.commit()

        flash(f"Usuário {nome} criado com sucesso!", "success")
        return redirect(url_for("auth.usuarios"))

    return render_template("auth/novo_usuario.html")


@auth_bp.route("/usuarios/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_usuario(id):
    if current_user.email != ADMIN_EMAIL:
        flash("Acesso restrito ao administrador.", "danger")
        return redirect(url_for("main.dashboard"))

    professor = Professor.query.get_or_404(id)
    if professor.email == ADMIN_EMAIL:
        flash("Não é possível excluir o administrador.", "danger")
        return redirect(url_for("auth.usuarios"))

    db.session.delete(professor)
    db.session.commit()
    flash(f"Usuário {professor.nome} removido.", "info")
    return redirect(url_for("auth.usuarios"))


@auth_bp.route("/usuarios/resetar-senha/<int:id>", methods=["POST"])
@login_required
def resetar_senha(id):
    if current_user.email != ADMIN_EMAIL:
        flash("Acesso restrito ao administrador.", "danger")
        return redirect(url_for("main.dashboard"))

    professor = Professor.query.get_or_404(id)
    nova_senha = request.form.get("nova_senha", "")
    if len(nova_senha) < 6:
        flash("A senha deve ter pelo menos 6 caracteres.", "danger")
        return redirect(url_for("auth.usuarios"))

    professor.set_senha(nova_senha)
    db.session.commit()
    flash(f"Senha de {professor.nome} redefinida com sucesso!", "success")
    return redirect(url_for("auth.usuarios"))
