from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, login_manager
from models.models import Professor

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


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


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        confirmar = request.form.get("confirmar_senha", "")
        escola = request.form.get("escola", "").strip()
        disciplina = request.form.get("disciplina", "").strip()

        if not nome or not email or not senha:
            flash("Preencha todos os campos obrigatórios.", "danger")
            return render_template("auth/cadastro.html")

        if senha != confirmar:
            flash("As senhas não conferem.", "danger")
            return render_template("auth/cadastro.html")

        if len(senha) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return render_template("auth/cadastro.html")

        if Professor.query.filter_by(email=email).first():
            flash("Este e-mail já está cadastrado.", "danger")
            return render_template("auth/cadastro.html")

        professor = Professor(nome=nome, email=email, escola=escola, disciplina=disciplina)
        professor.set_senha(senha)
        db.session.add(professor)
        db.session.commit()

        login_user(professor)
        flash("Cadastro realizado com sucesso! Bem-vindo(a)!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/cadastro.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))
