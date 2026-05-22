from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models.models import Avaliacao, Nota, Turma, Aluno
from datetime import datetime

aval_bp = Blueprint("avaliacoes", __name__, url_prefix="/avaliacoes")

@aval_bp.route("/")
@login_required
def index():
    from datetime import date
    hoje     = date.today()
    turma_id = request.args.get("turma_id", type=int)
    turmas   = Turma.query.filter_by(professor_id=current_user.id).all()
    return render_template("avaliacoes/index.html", turmas=turmas, turma_id=turma_id, hoje=hoje)

@aval_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    turmas = Turma.query.filter_by(professor_id=current_user.id).all()
    if not turmas:
        flash("Cadastre uma turma antes de criar avaliações.", "warning")
        return redirect(url_for("turmas.nova"))
    if request.method == "POST":
        try:
            data_ap = datetime.strptime(request.form["data_aplicacao"], "%Y-%m-%d").date() if request.form.get("data_aplicacao") else None
        except ValueError:
            data_ap = None
        av = Avaliacao(
            titulo=request.form.get("titulo","").strip() or "Sem título",
            tipo=request.form.get("tipo") or None,
            data_aplicacao=data_ap,
            valor_total=request.form.get("valor_total", 10.0, type=float),
            descricao=request.form.get("descricao") or None,
            gabarito=request.form.get("gabarito") or None,
            bimestre=request.form.get("bimestre", type=int),
            professor_id=current_user.id,
            turma_id=request.form.get("turma_id", type=int) or None,
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

from flask import jsonify
from datetime import date, datetime
import calendar as cal_mod


@aval_bp.route("/api/mes")
@login_required
def api_mes():
    hoje     = date.today()
    ano      = request.args.get("ano",  hoje.year,  type=int)
    mes      = request.args.get("mes",  hoje.month, type=int)
    turma_id = request.args.get("turma_id", type=int)
    q = Avaliacao.query.filter_by(professor_id=current_user.id)
    if turma_id:
        q = q.filter_by(turma_id=turma_id)
    avs = q.filter(
        Avaliacao.data_aplicacao.isnot(None),
        db.extract("year",  Avaliacao.data_aplicacao) == ano,
        db.extract("month", Avaliacao.data_aplicacao) == mes,
    ).all()
    return jsonify([{
        "id": a.id, "titulo": a.titulo, "tipo": a.tipo or "outro",
        "data_aplicacao": a.data_aplicacao.strftime("%Y-%m-%d"),
        "data_fmt": a.data_aplicacao.strftime("%d/%m/%Y"),
        "turma": a.turma.nome if a.turma else None,
        "bimestre": a.bimestre, "valor_total": a.valor_total,
        "descricao": a.descricao or "",
    } for a in avs])


@aval_bp.route("/relatorio-preview")
@login_required
def relatorio_preview():
    hoje     = date.today()
    tipo     = request.args.get("tipo", "mes")
    turma_id = request.args.get("turma_id", type=int)
    turmas   = Turma.query.filter_by(professor_id=current_user.id).all()
    t_nome   = next((t.nome for t in turmas if t.id==turma_id), "Todas as turmas") if turma_id else "Todas as turmas"

    if tipo == "mes":
        ano   = request.args.get("ano", hoje.year, type=int)
        meses = [int(m) for m in request.args.get("meses", str(hoje.month)).split(",") if m]
        datas = [(date(ano,m,1), date(ano,m,cal_mod.monthrange(ano,m)[1])) for m in meses]
        MNOMES=['','Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
        label = f"{', '.join(MNOMES[m] for m in meses)}/{ano}"
    elif tipo == "ano":
        ano   = request.args.get("ano", hoje.year, type=int)
        datas = [(date(ano,1,1), date(ano,12,31))]
        label = f"Ano Letivo {ano}"
    else:
        di    = datetime.strptime(request.args.get("data_ini", hoje.replace(day=1).isoformat()), "%Y-%m-%d").date()
        df    = datetime.strptime(request.args.get("data_fim", hoje.isoformat()), "%Y-%m-%d").date()
        datas = [(di, df)]
        label = f"{di.strftime('%d/%m/%Y')} a {df.strftime('%d/%m/%Y')}"

    avaliacoes = []
    for (di, df) in datas:
        q = Avaliacao.query.filter(
            Avaliacao.professor_id == current_user.id,
            Avaliacao.data_aplicacao >= di,
            Avaliacao.data_aplicacao <= df,
        )
        if turma_id:
            q = q.filter_by(turma_id=turma_id)
        avaliacoes.extend(q.order_by(Avaliacao.data_aplicacao).all())

    return render_template("avaliacoes/relatorio_preview.html",
        avaliacoes=avaliacoes, label=label, turma_nome=t_nome,
        prof_nome=current_user.nome, escola=current_user.escola or "")


@aval_bp.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    av = Avaliacao.query.filter_by(id=id, professor_id=current_user.id).first_or_404()
    db.session.delete(av)
    db.session.commit()
    return jsonify({"ok": True})
