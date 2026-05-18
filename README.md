# 📚 Amigo do Professor

Plataforma de gestão pedagógica para professores — controle de frequência, planejamento de aulas, avaliações, acompanhamento individual e calendário escolar.

## 🚀 Como rodar localmente

### 1. Clonar o repositório
```bash
git clone https://github.com/SEU-USUARIO/amigo-do-professor.git
cd amigo-do-professor
```

### 2. Criar ambiente virtual e instalar dependências
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente
```bash
cp .env.example .env
# Edite o .env e troque o SECRET_KEY por algo seguro
```

### 4. Rodar o app
```bash
python run.py
```

Acesse: http://localhost:5000

---

## ☁️ Deploy no Railway

### Opção 1: Via GitHub (recomendado)

1. Suba o projeto no GitHub
2. Acesse [railway.app](https://railway.app) e faça login
3. Clique em **New Project → Deploy from GitHub Repo**
4. Selecione este repositório
5. O Railway detecta automaticamente o `Procfile` e sobe o app

### Opção 2: Via Railway CLI
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Variáveis de ambiente no Railway
No painel do Railway, vá em **Variables** e adicione:
```
SECRET_KEY=sua-chave-secreta-muito-segura
```
Opcionalmente, adicione um PostgreSQL plugin — o Railway injeta `DATABASE_URL` automaticamente.

---

## 📱 Funcionalidades

| Módulo | Descrição |
|--------|-----------|
| **Frequência** | Registro diário, atestados, afastamentos, histórico por mês |
| **Planejamento** | Planos de aula com filtros de semana, mês, bimestre, semestre e ano |
| **Avaliações** | Criação de provas/trabalhos, lançamento de notas por aluno |
| **Pedagógico** | Registro individual de aprendizado, carências e encaminhamentos |
| **Calendário** | Calendário visual com FullCalendar, eventos por tipo e cor |

### Acesso mobile
- Interface totalmente responsiva para celular
- Suporte a **biometria via WebAuthn** (Touch ID / Face ID) nos dispositivos compatíveis

---

## 🗂️ Estrutura do projeto

```
amigo-do-professor/
├── app.py              # Factory do Flask
├── run.py              # Entry point
├── models/
│   └── models.py       # Modelos SQLAlchemy
├── routes/
│   ├── auth.py         # Login / cadastro
│   ├── main.py         # Dashboard
│   ├── frequencia.py
│   ├── planejamento.py
│   ├── avaliacoes.py
│   ├── pedagogico.py
│   └── calendario.py
├── templates/          # Jinja2 templates
├── static/
│   ├── css/main.css
│   └── js/main.js
├── requirements.txt
├── Procfile
└── railway.toml
```

## 🔐 Segurança
- Senhas com hash (Werkzeug `generate_password_hash`)
- Sessões protegidas por `SECRET_KEY`
- Dados isolados por professor (cada usuário vê apenas o seu)
- Biometria via WebAuthn (padrão W3C, sem dados biométricos no servidor)
