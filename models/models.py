from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Professor(UserMixin, db.Model):
    __tablename__ = "professores"
    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(150), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash    = db.Column(db.String(256), nullable=False)
    regional      = db.Column(db.String(100))
    escola        = db.Column(db.String(200))
    disciplina    = db.Column(db.String(100))
    cargo         = db.Column(db.String(100))
    telefone      = db.Column(db.String(30))
    foto          = db.Column(db.Text)
    ativo         = db.Column(db.Boolean, default=True)
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)

    turmas        = db.relationship("Turma", backref="professor", lazy=True)
    planos        = db.relationship("PlanoAula", backref="professor", lazy=True)
    avaliacoes    = db.relationship("Avaliacao", backref="professor", lazy=True)
    eventos       = db.relationship("EventoCalendario", backref="professor", lazy=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


class Turma(db.Model):
    __tablename__ = "turmas"
    id           = db.Column(db.Integer, primary_key=True)
    nome         = db.Column(db.String(100), nullable=False)
    ano          = db.Column(db.Integer, nullable=False)
    serie        = db.Column(db.String(50))
    professor_id = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)

    alunos      = db.relationship("Aluno", backref="turma", lazy=True, cascade="all, delete-orphan")
    frequencias = db.relationship("Frequencia", backref="turma", lazy=True, cascade="all, delete-orphan")
    planos      = db.relationship("PlanoAula", backref="turma", lazy=True)
    avaliacoes  = db.relationship("Avaliacao", backref="turma", lazy=True)


class Aluno(db.Model):
    __tablename__ = "alunos"
    id              = db.Column(db.Integer, primary_key=True)
    nome            = db.Column(db.String(150), nullable=False)
    matricula       = db.Column(db.String(50))
    data_nascimento = db.Column(db.Date)
    responsavel     = db.Column(db.String(150))
    contato         = db.Column(db.String(50))
    turma_id        = db.Column(db.Integer, db.ForeignKey("turmas.id"), nullable=False)
    # Campos RAv — cabeçalho (Bloco A)
    apresenta_deficiencia    = db.Column(db.Boolean, default=False)
    tipo_deficiencia         = db.Column(db.String(100))
    adequacao_curricular     = db.Column(db.Boolean, default=False)
    indicado_temporalidade   = db.Column(db.Boolean, default=False)
    sala_recursos            = db.Column(db.Boolean, default=False)
    programa_superacao       = db.Column(db.Boolean, default=False)
    tipo_atendimento         = db.Column(db.String(50))
    org_curricular_superacao = db.Column(db.String(20), default="nao")

    frequencias     = db.relationship("Frequencia", backref="aluno", lazy=True, cascade="all, delete-orphan")
    notas           = db.relationship("Nota", backref="aluno", lazy=True, cascade="all, delete-orphan")
    acompanhamentos = db.relationship("AcompanhamentoPedagogico", backref="aluno", lazy=True, cascade="all, delete-orphan")
    ravs            = db.relationship("RegistroAvaliacao", backref="aluno", lazy=True, cascade="all, delete-orphan")


class RegistroAvaliacao(db.Model):
    __tablename__ = "registros_avaliacao"
    id              = db.Column(db.Integer, primary_key=True)
    aluno_id        = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    professor_id    = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)
    bimestre        = db.Column(db.Integer, nullable=False)
    ano_letivo      = db.Column(db.Integer, default=2026)
    total_dias      = db.Column(db.Integer, default=48)
    total_faltas    = db.Column(db.Integer, default=0)
    data_inicio_bim = db.Column(db.String(50), default="12 de fevereiro")
    data_fim_bim    = db.Column(db.String(50), default="29 de maio de 2026")
    # Bloco B — conteúdo por área
    comportamento   = db.Column(db.Text)
    linguagem_leitura = db.Column(db.Text)
    linguagem_escrita = db.Column(db.Text)
    gramatica       = db.Column(db.Text)
    matematica      = db.Column(db.Text)
    ciencias        = db.Column(db.Text)
    historia        = db.Column(db.Text)
    geografia       = db.Column(db.Text)
    artes           = db.Column(db.Text)
    educacao_fisica = db.Column(db.Text)
    sintese         = db.Column(db.Text)
    perspectiva     = db.Column(db.Text)
    resultado_final = db.Column(db.String(50))
    criado_em       = db.Column(db.DateTime, default=datetime.utcnow)
    professor       = db.relationship("Professor", foreign_keys=[professor_id])


class Frequencia(db.Model):
    __tablename__ = "frequencias"
    id           = db.Column(db.Integer, primary_key=True)
    data         = db.Column(db.Date, nullable=False)
    status       = db.Column(db.String(30), nullable=False)
    observacao   = db.Column(db.Text)
    aluno_id     = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    turma_id     = db.Column(db.Integer, db.ForeignKey("turmas.id"), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)


class PlanoAula(db.Model):
    __tablename__ = "planos_aula"
    id                  = db.Column(db.Integer, primary_key=True)
    titulo              = db.Column(db.String(200), nullable=False)
    data_aula           = db.Column(db.Date, nullable=False)
    bimestre            = db.Column(db.Integer)
    semestre            = db.Column(db.Integer)
    conteudo            = db.Column(db.Text)
    objetivos           = db.Column(db.Text)
    metodologia         = db.Column(db.Text)
    recursos            = db.Column(db.Text)
    avaliacao_descricao = db.Column(db.Text)
    professor_id        = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)
    turma_id            = db.Column(db.Integer, db.ForeignKey("turmas.id"), nullable=True)
    criado_em           = db.Column(db.DateTime, default=datetime.utcnow)


class Avaliacao(db.Model):
    __tablename__ = "avaliacoes"
    id             = db.Column(db.Integer, primary_key=True)
    titulo         = db.Column(db.String(200), nullable=False)
    tipo           = db.Column(db.String(50))
    data_aplicacao = db.Column(db.Date)
    valor_total    = db.Column(db.Float, default=10.0)
    descricao      = db.Column(db.Text)
    gabarito       = db.Column(db.Text)
    bimestre       = db.Column(db.Integer)
    professor_id   = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)
    turma_id       = db.Column(db.Integer, db.ForeignKey("turmas.id"), nullable=False)
    criado_em      = db.Column(db.DateTime, default=datetime.utcnow)
    notas          = db.relationship("Nota", backref="avaliacao", lazy=True, cascade="all, delete-orphan")


class Nota(db.Model):
    __tablename__ = "notas"
    id           = db.Column(db.Integer, primary_key=True)
    nota         = db.Column(db.Float)
    comentario   = db.Column(db.Text)
    aluno_id     = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey("avaliacoes.id"), nullable=False)
    lancado_em   = db.Column(db.DateTime, default=datetime.utcnow)


class AcompanhamentoPedagogico(db.Model):
    __tablename__ = "acompanhamentos_pedagogicos"
    id             = db.Column(db.Integer, primary_key=True)
    data           = db.Column(db.Date, nullable=False)
    tipo           = db.Column(db.String(50))
    descricao      = db.Column(db.Text, nullable=False)
    encaminhamento = db.Column(db.String(200))
    status         = db.Column(db.String(30), default="aberto")
    aluno_id       = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=True)
    professor_id   = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)
    criado_em      = db.Column(db.DateTime, default=datetime.utcnow)


class EventoCalendario(db.Model):
    __tablename__ = "eventos_calendario"
    id           = db.Column(db.Integer, primary_key=True)
    titulo       = db.Column(db.String(200), nullable=False)
    data_inicio  = db.Column(db.Date, nullable=False)
    data_fim     = db.Column(db.Date)
    tipo         = db.Column(db.String(50))
    descricao    = db.Column(db.Text)
    cor          = db.Column(db.String(20), default="#3B82F6")
    professor_id = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)
    criado_em    = db.Column(db.DateTime, default=datetime.utcnow)


class FraseRAv(db.Model):
    """Frases pré-definidas personalizadas por professor para uso no RAv."""
    __tablename__ = "frases_rav"
    id           = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=False)
    area         = db.Column(db.String(50), nullable=False)  # comportamento, linguagem_leitura, etc.
    texto        = db.Column(db.Text, nullable=False)
    criado_em    = db.Column(db.DateTime, default=datetime.utcnow)
