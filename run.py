import os
from app import create_app, db
from models.models import Professor

app = create_app()

def criar_admin():
    with app.app_context():
        if not Professor.query.filter_by(email="mavana1981@gmail.com").first():
            admin = Professor(nome="Administrador", email="mavana1981@gmail.com")
            admin.set_senha("69512400")
            db.session.add(admin)
            db.session.commit()
            print("[Admin criado com sucesso]")

criar_admin()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
