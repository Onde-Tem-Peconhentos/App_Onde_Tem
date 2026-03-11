from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import iniciar_session
from app.api.services.busca_cidades import (
    ORS_API_KEY,
    buscar_postos_por_cidades_e_soro,
    calcular_cidades_proximas,
    calcular_distancias_postos_em_blocos,
    geocodificar_origem,
    modo_para_ors,
)

busca_router = APIRouter(prefix="/busca", tags=["busca"])


@busca_router.get("/postos")
async def buscar_postos(
    endereco: Optional[str] = Query(None),
    numero: Optional[str] = Query(None),
    bairro: Optional[str] = Query(None),
    cep: Optional[str] = Query(None),
    municipio: str = Query(...),
    animal: str = Query(...),
    modo: str = Query("carro"),
    limite: int = Query(10),
    session: Session = Depends(iniciar_session),
):
    try:
        if cep:
            tipo_entrada = "cep"
            entrada = cep
        else:
            tipo_entrada = "endereco"
            partes = [
                endereco or "",
                numero or "",
                bairro or "",
                municipio or "",
                "SP",
                "Brasil",
            ]
            entrada = ", ".join([p for p in partes if p]).strip()

        origem_coords, endereco_origem, endereco_busca = geocodificar_origem(
            tipo_entrada,
            entrada,
            ORS_API_KEY,
        )

        cidades_proximas = calcular_cidades_proximas(origem_coords, top_n=25)

        postos_filtrados = buscar_postos_por_cidades_e_soro(
            session=session,
            animal=animal,
            cidades_proximas=cidades_proximas,
        )

        if not postos_filtrados:
            return {
                "origem": {
                    "lat": origem_coords[0],
                    "lon": origem_coords[1],
                    "endereco": endereco_busca,
                },
                "cidades_consideradas": cidades_proximas,
                "top": [],
                "erro": "Nenhum posto encontrado nas cidades mais próximas com o soro necessário.",
            }

        resultados = calcular_distancias_postos_em_blocos(
            postos=postos_filtrados,
            origem_coords=origem_coords,
            modo_ors=modo_para_ors(modo),
            api_key=ORS_API_KEY,
        )

        if not resultados:
            return {
                "origem": {
                    "lat": origem_coords[0],
                    "lon": origem_coords[1],
                    "endereco": endereco_busca,
                },
                "cidades_consideradas": cidades_proximas,
                "top": [],
                "erro": "Nenhum posto com rota válida encontrada.",
            }

        top = sorted(
            resultados,
            key=lambda x: (
                x["tempo_min"] is None,
                x["tempo_min"] if x["tempo_min"] is not None else float("inf"),
            ),
        )[:limite]

        return {
            "origem": {
                "lat": origem_coords[0],
                "lon": origem_coords[1],
                "endereco": endereco_busca,
                "cep_info": endereco_origem,
            },
            "cidades_consideradas": cidades_proximas,
            "top": top,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Erro na busca: {e}")
        raise HTTPException(status_code=500, detail="Erro interno na busca.")