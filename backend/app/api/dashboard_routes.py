from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Float, and_, case, cast, func, text
from sqlalchemy.orm import Session

from app.dependencies import iniciar_session
from db.models import Acidente, Municipio

BASE_DIR = Path(__file__).resolve().parents[2]
DB_FILE = str(BASE_DIR / "data" / "sinan.db")


dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# ===== Cache (somente para o caso "default": sem filtros) =====
CACHE_TTL = 300  # segundos (5 min)

_CACHE_DEFAULT = {"ts": 0.0, "data": None}
_DB_MTIME = None


def _invalidate_cache_if_db_changed() -> None:
    """Se o arquivo do SQLite mudou, limpa o cache default."""
    global _DB_MTIME
    try:
        m = os.path.getmtime(DB_FILE)
    except OSError:
        return

    if _DB_MTIME is None:
        _DB_MTIME = m
        return

    if m != _DB_MTIME:
        _DB_MTIME = m
        _CACHE_DEFAULT["ts"] = 0.0
        _CACHE_DEFAULT["data"] = None


# ===== Endpoints de filtros =====

@dashboard_router.get("/municipios")
async def listar_municipios(session: Session = Depends(iniciar_session)):
    rows = (
        session.query(Municipio.nome)
        .distinct()
        .order_by(Municipio.nome)
        .all()
    )
    return [{"nome": nome} for (nome,) in rows if nome is not None]


@dashboard_router.get("/anos")
async def listar_anos(session: Session = Depends(iniciar_session)):
    rows = (
        session.query(Acidente.ano_dado)
        .distinct()
        .order_by(Acidente.ano_dado)
        .all()
    )
    return [{"ano": int(ano)} for (ano,) in rows if ano is not None]


@dashboard_router.get("/animal")
async def listar_animal(session: Session = Depends(iniciar_session)):
    rows = (
        session.query(Acidente.animal_tipo_desc)
        .distinct()
        .order_by(Acidente.animal_tipo_desc)
        .all()
    )
    return [{"nome": nome} for (nome,) in rows if nome is not None]


# ===== Resumo do dashboard =====

@dashboard_router.get("/resumo")
async def dashboard_resumo(
    municipio: Optional[str] = None,
    anos: List[int] = Query(default=[]),
    animais: List[str] = Query(default=[]),
    session: Session = Depends(iniciar_session),
):
    codigos_obito = ["2", "3"]

    is_default = (not municipio) and (not anos) and (not animais)

    # Invalida cache se o DB mudou
    _invalidate_cache_if_db_changed()

    # 1) Caminho rápido: se for default, tenta cache em memória
    if is_default and _CACHE_DEFAULT["data"] is not None:
        if (time.time() - _CACHE_DEFAULT["ts"]) < CACHE_TTL:
            return _CACHE_DEFAULT["data"]

    # 2) Caminho mais rápido ainda: se for default, tenta mini-tabelas pré-agregadas
    #    (criadas no seu script de atualização)
    if is_default:
        try:
            metrics = session.execute(
                text(
                    "SELECT totalCasos, taxaObitos, tempoAtendimento "
                    "FROM dashboard_metrics LIMIT 1"
                )
            ).fetchone()

            if metrics is not None:
                anos_rows = session.execute(
                    text("SELECT ano, total FROM dashboard_casos_por_ano")
                ).fetchall()

                animais_rows = session.execute(
                    text("SELECT animal, total FROM dashboard_por_animal")
                ).fetchall()

                grav_rows = session.execute(
                    text("SELECT classificacao, total FROM dashboard_por_gravidade")
                ).fetchall()

                resp = {
                    "metrics": {
                        "totalCasos": int(metrics[0] or 0),
                        "taxaObitos": float(metrics[1] or 0),
                        "tempoAtendimento": float(metrics[2] or 0),
                    },
                    "casosPorAno": [
                        {"ano": int(a), "total_acidentes": int(t)} for a, t in anos_rows
                    ],
                    "distAnimal": [
                        {"animal_tipo": n, "total_acidentes": int(t)} for n, t in animais_rows
                    ],
                    "gravidade": [
                        {"classificacao": c, "total_acidentes": int(t)} for c, t in grav_rows
                    ],
                }

                _CACHE_DEFAULT["data"] = resp
                _CACHE_DEFAULT["ts"] = time.time()
                return resp

        except Exception:
            # Se ainda não criou as tabelas resumo, cai pro caminho normal
            pass

    # 3) Caminho normal (com filtros): monta query base
    q = session.query(Acidente)

    # Município: resolve cod_mun7 e filtra direto em Acidente (sem JOIN)
    if municipio:
        cod = (
            session.query(Municipio.cod_mun7)
            .filter(Municipio.nome == municipio)
            .scalar()
        )
        if cod is None:
            return {
                "metrics": {"totalCasos": 0, "taxaObitos": 0.0, "tempoAtendimento": 0.0},
                "casosPorAno": [],
                "distAnimal": [],
                "gravidade": [],
            }
        q = q.filter(Acidente.municipio_acidente == cod)

    if anos:
        q = q.filter(Acidente.ano_dado.in_(anos))

    if animais:
        q = q.filter(Acidente.animal_tipo_desc.in_(animais))

    # ===== METRICS em 1 query =====
    tempo_num = cast(func.replace(Acidente.tempo_atendimento_desc, ",", "."), Float)

    cond_tempo = and_(
        Acidente.tempo_atendimento_desc.isnot(None),
        ~Acidente.tempo_atendimento_desc.like("%-%"),
        ~Acidente.tempo_atendimento_desc.like("%h%"),
        ~Acidente.tempo_atendimento_desc.like("%H%"),
    )
    tempo_val = case((cond_tempo, tempo_num), else_=None)

    total_geral, total_obitos, tempo_medio = (
        q.with_entities(
            func.count(Acidente.id),
            func.sum(case((Acidente.evolucao.in_(codigos_obito), 1), else_=0)),
            func.avg(tempo_val),
        ).one()
    )

    total_geral = int(total_geral or 0)
    total_obitos = int(total_obitos or 0)
    taxa_obitos = round((total_obitos / total_geral) * 100, 2) if total_geral else 0.0
    tempo_medio = round(float(tempo_medio), 2) if tempo_medio is not None else 0.0

    # ===== GRÁFICOS =====
    casos_por_ano_rows = (
        q.with_entities(Acidente.ano_dado, func.count(Acidente.id))
        .filter(Acidente.ano_dado.isnot(None))
        .group_by(Acidente.ano_dado)
        .order_by(Acidente.ano_dado)
        .all()
    )

    dist_animal_rows = (
        q.with_entities(Acidente.animal_tipo_desc, func.count(Acidente.id))
        .filter(Acidente.animal_tipo_desc.isnot(None))
        .group_by(Acidente.animal_tipo_desc)
        .order_by(Acidente.animal_tipo_desc)
        .all()
    )

    gravidade_rows = (
        q.with_entities(Acidente.classificacao_final_desc, func.count(Acidente.id))
        .filter(Acidente.classificacao_final_desc.isnot(None))
        .group_by(Acidente.classificacao_final_desc)
        .order_by(Acidente.classificacao_final_desc)
        .all()
    )

    casos_por_ano = [
        {"ano": int(ano), "total_acidentes": int(total)}
        for ano, total in casos_por_ano_rows
    ]
    dist_animal = [
        {"animal_tipo": animal, "total_acidentes": int(total)}
        for animal, total in dist_animal_rows
    ]
    gravidade = [
        {"classificacao": clas, "total_acidentes": int(total)}
        for clas, total in gravidade_rows
    ]

    resp = {
        "metrics": {
            "totalCasos": total_geral,
            "taxaObitos": taxa_obitos,
            "tempoAtendimento": tempo_medio,
        },
        "casosPorAno": casos_por_ano,
        "distAnimal": dist_animal,
        "gravidade": gravidade,
    }

    # Se for default e caiu no caminho normal, salva em cache
    if is_default:
        _CACHE_DEFAULT["data"] = resp
        _CACHE_DEFAULT["ts"] = time.time()

    return resp
