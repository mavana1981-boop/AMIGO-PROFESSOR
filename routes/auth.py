from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db, login_manager
from models.models import Professor
import os, base64

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
ADMIN_EMAIL = "mavana1981@gmail.com"


@login_manager.user_loader
def load_user(user_id):
    return Professor.query.get(int(user_id))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email  = request.form.get("email", "").strip()
        senha  = request.form.get("senha", "")
        lembrar = request.form.get("lembrar") == "on"
        professor = Professor.query.filter_by(email=email).first()
        if professor and professor.check_senha(senha):
            login_user(professor, remember=lembrar)
            flash(f"Bem-vindo(a), {professor.nome.split()[0]}!", "success")
            return redirect(request.args.get("next") or url_for("main.dashboard"))
        flash("E-mail ou senha incorretos.", "danger")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))


# ── Gerenciamento de usuários (apenas admin) ──────────────────

def is_admin():
    return current_user.is_authenticated and current_user.email == ADMIN_EMAIL


@auth_bp.route("/usuarios")
@login_required
def usuarios():
    if not is_admin():
        flash("Acesso restrito ao administrador.", "danger")
        return redirect(url_for("main.dashboard"))
    professores = Professor.query.order_by(Professor.nome).all()
    return render_template("auth/usuarios.html", professores=professores)


@auth_bp.route("/usuarios/novo", methods=["GET", "POST"])
@login_required
def novo_usuario():
    if not is_admin():
        flash("Acesso restrito ao administrador.", "danger")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        nome       = request.form.get("nome", "").strip()
        email      = request.form.get("email", "").strip()
        senha      = request.form.get("senha", "")
        regional   = request.form.get("regional", "").strip()
        escola     = request.form.get("escola", "").strip()
        disciplina = request.form.get("disciplina", "").strip()
        cargo      = request.form.get("cargo", "").strip()
        telefone   = request.form.get("telefone", "").strip()

        if not nome or not email or not senha:
            flash("Nome, e-mail e senha são obrigatórios.", "danger")
            return render_template("auth/novo_usuario.html")
        if len(senha) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return render_template("auth/novo_usuario.html")
        if Professor.query.filter_by(email=email).first():
            flash("Este e-mail já está cadastrado.", "danger")
            return render_template("auth/novo_usuario.html")

        # Foto (converte para base64)
        foto_b64 = None
        foto_file = request.files.get("foto")
        if foto_file and foto_file.filename:
            dados = foto_file.read()
            mime  = foto_file.content_type or "image/jpeg"
            foto_b64 = f"data:{mime};base64,{base64.b64encode(dados).decode()}"

        professor = Professor(
            nome=nome, email=email, regional=regional,
            escola=escola, disciplina=disciplina,
            cargo=cargo, telefone=telefone, foto=foto_b64
        )
        professor.set_senha(senha)
        db.session.add(professor)
        db.session.commit()
        flash(f"Usuário {nome} criado com sucesso!", "success")
        return redirect(url_for("auth.usuarios"))

    return render_template("auth/novo_usuario.html")


@auth_bp.route("/usuarios/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_usuario(id):
    if not is_admin():
        flash("Acesso restrito ao administrador.", "danger")
        return redirect(url_for("main.dashboard"))

    professor = Professor.query.get_or_404(id)

    if request.method == "POST":
        professor.nome       = request.form.get("nome", "").strip()
        professor.email      = request.form.get("email", "").strip()
        professor.regional   = request.form.get("regional", "").strip()
        professor.escola     = request.form.get("escola", "").strip()
        professor.disciplina = request.form.get("disciplina", "").strip()
        professor.cargo      = request.form.get("cargo", "").strip()
        professor.telefone   = request.form.get("telefone", "").strip()

        nova_senha = request.form.get("nova_senha", "")
        if nova_senha:
            if len(nova_senha) < 6:
                flash("A senha deve ter pelo menos 6 caracteres.", "danger")
                return render_template("auth/editar_usuario.html", professor=professor)
            professor.set_senha(nova_senha)

        foto_file = request.files.get("foto")
        if foto_file and foto_file.filename:
            dados = foto_file.read()
            mime  = foto_file.content_type or "image/jpeg"
            professor.foto = f"data:{mime};base64,{base64.b64encode(dados).decode()}"

        db.session.commit()
        flash(f"Usuário {professor.nome} atualizado!", "success")
        return redirect(url_for("auth.usuarios"))

    return render_template("auth/editar_usuario.html", professor=professor)


@auth_bp.route("/usuarios/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_usuario(id):
    if not is_admin():
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
