import os
from app import create_app, db
from models.models import Professor

app = create_app()


def migrar_banco():
    """Adiciona colunas novas ao banco existente sem perder dados."""
    from sqlalchemy import text, inspect
    with app.app_context():
        inspector = inspect(db.engine)

        # Colunas novas na tabela professores
        colunas_prof = {c['name'] for c in inspector.get_columns('professores')}
        novas_prof = {
            'regional':   'ALTER TABLE professores ADD COLUMN regional TEXT',
            'escola':     'ALTER TABLE professores ADD COLUMN escola TEXT',
            'disciplina': 'ALTER TABLE professores ADD COLUMN disciplina TEXT',
            'cargo':      'ALTER TABLE professores ADD COLUMN cargo TEXT',
            'telefone':   'ALTER TABLE professores ADD COLUMN telefone TEXT',
            'foto':       'ALTER TABLE professores ADD COLUMN foto TEXT',
            'ativo':      'ALTER TABLE professores ADD COLUMN ativo INTEGER DEFAULT 1',
            'criado_em':  'ALTER TABLE professores ADD COLUMN criado_em TEXT',
        }
        for col, sql in novas_prof.items():
            if col not in colunas_prof:
                try:
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f'[Migration] Coluna adicionada: professores.{col}')
                except Exception as e:
                    db.session.rollback()
                    print(f'[Migration] Erro em professores.{col}: {e}')

        # Colunas novas na tabela alunos
        colunas_aluno = {c['name'] for c in inspector.get_columns('alunos')}
        novas_aluno = {
            'apresenta_deficiencia':    'ALTER TABLE alunos ADD COLUMN apresenta_deficiencia INTEGER DEFAULT 0',
            'tipo_deficiencia':         'ALTER TABLE alunos ADD COLUMN tipo_deficiencia TEXT',
            'adequacao_curricular':     'ALTER TABLE alunos ADD COLUMN adequacao_curricular INTEGER DEFAULT 0',
            'indicado_temporalidade':   'ALTER TABLE alunos ADD COLUMN indicado_temporalidade INTEGER DEFAULT 0',
            'sala_recursos':            'ALTER TABLE alunos ADD COLUMN sala_recursos INTEGER DEFAULT 0',
            'programa_superacao':       'ALTER TABLE alunos ADD COLUMN programa_superacao INTEGER DEFAULT 0',
            'tipo_atendimento':         'ALTER TABLE alunos ADD COLUMN tipo_atendimento TEXT',
            'org_curricular_superacao': 'ALTER TABLE alunos ADD COLUMN org_curricular_superacao TEXT DEFAULT "nao"',
        }
        for col, sql in novas_aluno.items():
            if col not in colunas_aluno:
                try:
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f'[Migration] Coluna adicionada: alunos.{col}')
                except Exception as e:
                    db.session.rollback()
                    print(f'[Migration] Erro em alunos.{col}: {e}')

        # Tabelas novas (frases_rav, registros_avaliacao)
        tabelas = set(inspector.get_table_names())
        db.create_all()
        print('[Migration] Tabelas verificadas/criadas.')


def criar_admin():
    """Cria o usuário admin se não existir."""
    with app.app_context():
        if not Professor.query.filter_by(email="mavana1981@gmail.com").first():
            admin = Professor(nome="Administrador", email="mavana1981@gmail.com")
            admin.set_senha("69512400")
            db.session.add(admin)
            db.session.commit()
            print("[Admin criado] mavana1981@gmail.com")
        else:
            print("[Admin já existe]")


migrar_banco()
criar_admin()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
