from fastapi import APIRouter, Depends
from models import Acidente, Municipio
from dependencies import iniciar_session
from sqlalchemy.orm import Session
from sqlalchemy import func


dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@dashboard_router.get("/municipios")
async def listar_municipios(session: Session = Depends(iniciar_session)):
    municipios = (
        session.query( Municipio.nome)
        .order_by(Municipio.nome)
        .all()
    )
    return [{"nome": nome} for nome, in municipios]

@dashboard_router.get("/anos")
async def listar_anos(session: Session = Depends(iniciar_session)):
    anos = (
        session.query(Acidente.ano_dado)
        .distinct()
        .order_by(Acidente.ano_dado)
        .all()
    )

    return [
        {"ano": int(row.ano_dado)}
        for row in anos
        if row.ano_dado is not None
    ]


@dashboard_router.get("/animal")
async def listar_animal(session: Session = Depends(iniciar_session)):
    animais = (
        session.query(Acidente.animal_tipo_desc)
        .distinct()
        .order_by(Acidente.animal_tipo_desc)
        .all()
    )

    return [
        {"nome": nome}
        for nome, in animais
    ]

@dashboard_router.get("/total_acidentes")
async def total_acidentes(session: Session = Depends(iniciar_session)):
    total = session.query(Acidente).count()
    return {"total_acidentes": total}  

@dashboard_router.get("/taxa_obitos")
async def taxa_obitos(session: Session = Depends(iniciar_session)):
    codigos_obito = [2, 3]
    
    total_geral = session.query(Acidente).count()
    if total_geral == 0:
        return {"taxa_obitos": 0.0}
    total = session.query(Acidente).filter(Acidente.evolucao.in_(codigos_obito)).count()
    
    total_percent = round((total / total_geral) * 100, 2)
    
    return {"taxa_obitos": total_percent}

@dashboard_router.get("/tempo_medio_atendimento")
async def tempo_medio_atendimento(session: Session = Depends(iniciar_session)):
    media = session.query(func.avg(Acidente.tempo_atendimento_desc)).scalar()
    if media is None:
        media = 0

    return {"tempo_medio_atendimento_horas": round(media, 2)}


@dashboard_router.get("/casos_por_ano")
async def casos_por_ano(session: Session = Depends(iniciar_session)):
       resultados = (
            session.query(
                Acidente.ano_dado,
                func.count(Acidente.id).label("total_acidentes")
            )
            .group_by(Acidente.ano_dado)
            .order_by(Acidente.ano_dado)
            .all()
        )
       return [
            {"ano": int(ano), "total_acidentes": total_acidentes}
            for ano, total_acidentes in resultados
            if ano is not None
        ]    
       
@dashboard_router.get("/distribuicao_por_tipo_animal")
async def distribuicao_por_tipo_animal(session: Session = Depends(iniciar_session)):
       resultados = (
            session.query(
                Acidente.animal_tipo_desc,
                func.count(Acidente.id).label("total_acidentes")
            )
            .group_by(Acidente.animal_tipo_desc)
            .order_by(Acidente.animal_tipo_desc)
            .all()
        )
       return [
            {"animal_tipo": animal_tipo, "total_acidentes": total_acidentes}
            for animal_tipo, total_acidentes in resultados
        ]
       
@dashboard_router.get("/gravidade_dos_casos")
async def gravidade_dos_casos(session: Session = Depends(iniciar_session)):
       resultados = (
            session.query(
                Acidente.classificacao_final_desc,
                func.count(Acidente.id).label("total_acidentes")
            )
            .group_by(Acidente.classificacao_final_desc)
            .order_by(Acidente.classificacao_final_desc)
            .all()
        )
       return [
            {"classificacao": classificacao, "total_acidentes": total_acidentes}
            for classificacao, total_acidentes in resultados
        ]
