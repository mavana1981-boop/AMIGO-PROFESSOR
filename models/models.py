from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Professor(UserMixin, db.Model):
    __tablename__ = "professores"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    escola = db.Column(db.String(200))
    disciplina = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    turmas = db.relationship("Turma", backref="professor", lazy=True)
    planos = db.relationship("PlanoAula", backref="professor", lazy=True)
    avaliacoes = db.relationship("Avaliacao", backref="professor", lazy=True)
    eventos = db.relationship("EventoCalendario", backref="professor", lazy=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f"<Professor {self.nome}>"


class Turma(db.Model):
    __tablename__ = "turmas"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    serie = db.Column(db.String(50))
    professor_id = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)

    alunos = db.relationship("Aluno", backref="turma", lazy=True)
    frequencias = db.relationship("Frequencia", backref="turma", lazy=True)
    planos = db.relationship("PlanoAula", backref="turma", lazy=True)
    avaliacoes = db.relationship("Avaliacao", backref="turma", lazy=True)


class Aluno(db.Model):
    __tablename__ = "alunos"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    matricula = db.Column(db.String(50))
    data_nascimento = db.Column(db.Date)
    responsavel = db.Column(db.String(150))
    contato = db.Column(db.String(50))
    turma_id = db.Column(db.Integer, db.ForeignKey("turmas.id"), nullable=False)

    frequencias = db.relationship("Frequencia", backref="aluno", lazy=True)
    notas = db.relationship("Nota", backref="aluno", lazy=True)
    acompanhamentos = db.relationship("AcompanhamentoPedagogico", backref="aluno", lazy=True)


class Frequencia(db.Model):
    __tablename__ = "frequencias"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), nullable=False)  # presente, ausente, atestado, afastamento
    observacao = db.Column(db.Text)
    aluno_id = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey("turmas.id"), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)


class PlanoAula(db.Model):
    __tablename__ = "planos_aula"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    data_aula = db.Column(db.Date, nullable=False)
    bimestre = db.Column(db.Integer)  # 1, 2, 3, 4
    semestre = db.Column(db.Integer)  # 1, 2
    conteudo = db.Column(db.Text)
    objetivos = db.Column(db.Text)
    metodologia = db.Column(db.Text)
    recursos = db.Column(db.Text)
    avaliacao_descricao = db.Column(db.Text)
    professor_id = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey("turmas.id"), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


class Avaliacao(db.Model):
    __tablename__ = "avaliacoes"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50))  # prova, trabalho, seminário, etc.
    data_aplicacao = db.Column(db.Date)
    data_entrega = db.Column(db.Date)
    valor_total = db.Column(db.Float, default=10.0)
    descricao = db.Column(db.Text)
    gabarito = db.Column(db.Text)
    bimestre = db.Column(db.Integer)
    professor_id = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey("turmas.id"), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    notas = db.relationship("Nota", backref="avaliacao", lazy=True)


class Nota(db.Model):
    __tablename__ = "notas"
    id = db.Column(db.Integer, primary_key=True)
    nota = db.Column(db.Float)
    comentario = db.Column(db.Text)
    aluno_id = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey("avaliacoes.id"), nullable=False)
    lancado_em = db.Column(db.DateTime, default=datetime.utcnow)


class AcompanhamentoPedagogico(db.Model):
    __tablename__ = "acompanhamentos_pedagogicos"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(50))  # aprendizado, carência, encaminhamento
    descricao = db.Column(db.Text, nullable=False)
    encaminhamento = db.Column(db.String(200))  # psicólogo, fonoaudiólogo, etc.
    status = db.Column(db.String(30), default="aberto")  # aberto, em andamento, concluído
    aluno_id = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


class EventoCalendario(db.Model):
    __tablename__ = "eventos_calendario"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date)
    tipo = db.Column(db.String(50))  # feriado, prova, reunião, evento, recesso
    descricao = db.Column(db.Text)
    cor = db.Column(db.String(20), default="#3B82F6")
    professor_id = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
