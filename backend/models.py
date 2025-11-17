# models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    ForeignKey,
    
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

DATABASE_URL = "sqlite:///sinan.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,      # coloque True se quiser ver o SQL no console
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


#---------
class Municipio(Base):
    __tablename__ = "municipios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cod_mun7 = Column(Integer, unique=True, index=True, nullable=False)
    nome = Column(String, nullable=False)
    uf = Column(String(2), nullable=False, default="SP")
    casos = relationship("Acidente", back_populates="municipio")
    postos = relationship("Posto", back_populates="municipio")

class Acidente(Base):
    __tablename__ = "acidentes"
    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- PACIENTE ---
    sexo = Column(String(1)) 
    sexo_desc = Column(String)
    idade_anos = Column(Float)
    raca = Column(String)
    raca_desc = Column(String)
    escolaridade = Column(String)
    escolaridade_desc = Column(String)
    gestante = Column(String)
    gestante_desc = Column(String)
    
    # --- TEMPORAL ---
    data_acidente = Column(Date)
    ano_dado = Column(Integer, index=True)

    # --- LOCAL ---
    municipio_acidente = Column(Integer, ForeignKey("municipios.cod_mun7"), index=True, nullable=True)
    zona = Column(String)
    zona_desc = Column(String) 
    local_picada = Column(String)
    local_picada_desc = Column(String) 

    # --- O ACIDENTE ---
    animal_tipo = Column(String(2))
    animal_tipo_desc = Column(String(20))
    acidente_trabalho = Column(String)
    acidente_trabalho_desc = Column(String) 

    # --- TRATAMENTO (NOVO) ---
    con_sorote = Column(String)      
    con_sorote_desc = Column(String)

    # --- CLÍNICA ---
    tempo_atendimento = Column(String)
    tempo_atendimento_desc = Column(String) 
    classificacao_final = Column(String)
    classificacao_final_desc = Column(String) 
    evolucao = Column(String)
    evolucao_desc = Column(String) 
    
    municipio = relationship("Municipio", back_populates="casos")

class Posto(Base):
    __tablename__ = "postos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    municipio_nome = Column(String, nullable=False)
    cod_mun7 = Column(Integer, ForeignKey("municipios.cod_mun7"), index=True, nullable=False)
    cod_mun6 = Column(String, index=True)
    gve = Column(String)
    ubs = Column(String)
    endereco = Column(String)
    tem_soro = Column(Integer)
    tipo_soro = Column(String)
    aberto_24h = Column(Integer)
    telefone = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    aracnidico = Column(Integer)
    botropico = Column(Integer)
    crotalico = Column(Integer)
    elapidico = Column(Integer)
    escorpionico = Column(Integer)
    lonomico = Column(Integer)
    municipio = relationship("Municipio", back_populates="postos")
    


if __name__ == "__main__":

    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso!")