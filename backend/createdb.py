# createdb.py
from db import engine, Base
import models  # importa para registrar os modelos


if __name__ == "__main__":
    # ⚠️ DESCOMENTE a linha abaixo somente se você QUISER apagar todas as tabelas antigas.
    # Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso!")
