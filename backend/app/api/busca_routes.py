from __future__ import annotations

import os
import unicodedata
from typing import Optional
import math

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import iniciar_session
from db.models import Posto, Acidente  # ajuste para app.db.models se necessário

busca_router = APIRouter(prefix="/busca", tags=["busca"])

ORS_API_KEY = os.getenv("ORS_API_KEY")

# Quantos postos no máximo vão para a Matrix (quanto menor, mais rápido)
# 20 costuma ficar ótimo. Pode testar 10/15/20/30.
TOP_MATRIX = 5


def normalizar(texto: str) -> str:
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .lower()
        .strip()
    )


def identificar_coluna_soro(animal: str) -> Optional[str]:
    """
    Converte o animal para a coluna de soro da tabela Posto.
    Ajuste o mapeamento conforme os textos reais do seu banco.
    """
    a = normalizar(animal)

    mapa = {
        "escorpiao": "escorpionico",
        "aranha": "aracnidico",
        "aranha marrom": "aracnidico",
        "aranha armadeira": "aracnidico",
        "aranha viuva-negra": "aracnidico",
        "aranha viuva negra": "aracnidico",
        "taturana": "lonomico",
        "lagarta": "lonomico",
        "cobra jararaca": "botropico",
        "jararaca": "botropico",
        "cobra surucucu": "laquetico",
        "surucucu": "laquetico",
        "cobra cascavel": "crotalico",
        "cascavel": "crotalico",
        "cobra coral": "elapidico",
        "coral": "elapidico",
    }

    if a in mapa:
        return mapa[a]

    # Heurísticas (ajuda quando o texto vem diferente)
    if "escorp" in a:
        return "escorpionico"
    if "aranh" in a:
        return "aracnidico"
    if "tatur" in a or "lagart" in a or "lonom" in a:
        return "lonomico"
    if "cascavel" in a:
        return "crotalico"
    if "surucucu" in a or "laquet" in a:
        return "laquetico"
    if "coral" in a or "elap" in a:
        return "elapidico"
    if "cobra" in a or "serp" in a or "jarar" in a or "botrop" in a:
        return "botropico"

    return None


def modo_para_ors(modo: str) -> str:
    m = normalizar(modo)
    if m in ["carro", "driving"]:
        return "driving-car"
    if m in ["caminhando", "a pe", "ape", "walking", "pé", "pe"]:
        return "foot-walking"
    if m in ["bicicleta", "bike", "bicycling"]:
        return "cycling-regular"
    return "driving-car"


def raio_por_modo_km(modo: str) -> float:
    """
    Raio inicial (aproximado) para pré-filtrar no banco por bounding box.
    """
    m = normalizar(modo)
    if m in ["caminhando", "a pe", "ape", "walking", "pé", "pe"]:
        return 8.0
    if m in ["bicicleta", "bike", "bicycling"]:
        return 15.0
    return 30.0  # carro


def geocodificar_origem(endereco: str, municipio_selecionado: str) -> tuple[float, float]:

    if not ORS_API_KEY:
        raise ValueError("ORS_API_KEY não configurada no servidor.")

    url = "https://api.openrouteservice.org/geocode/search"
    params = {
        "api_key": ORS_API_KEY,
        "text": endereco,
        "boundary.country": "BR",
        "size": 1,
    }

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    feats = data.get("features") or []
    if not feats:
        raise ValueError("Endereço não encontrado.")

    feat = feats[0]
    props = feat.get("properties") or {}

    # 🔎 1) Validar confiança
    confidence = props.get("confidence")
    if confidence is not None and confidence < 0.7:
        raise ValueError("Endereço inválido ou impreciso.")

    # 🔎 2) Validar município
    cidade_retorno = normalizar(props.get("locality") or props.get("county") or "")
    if normalizar(municipio_selecionado) not in cidade_retorno:
        raise ValueError("Endereço não corresponde ao município selecionado.")

    # 🔎 3) Verificar se rua foi reconhecida
    label = normalizar(props.get("label") or "")
    rua_digitada = normalizar(endereco.split(",")[0])

    if rua_digitada[:5] not in label:
        raise ValueError("Rua não reconhecida. Verifique o endereço.")

    lon, lat = feat["geometry"]["coordinates"]
    return float(lat), float(lon)



def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def bounding_box(lat: float, lon: float, raio_km: float) -> tuple[float, float, float, float]:
    # 1 grau lat ~ 111km
    delta_lat = raio_km / 111.0
    # 1 grau lon ~ 111km * cos(lat)
    cos_lat = max(0.1, math.cos(math.radians(lat)))
    delta_lon = raio_km / (111.0 * cos_lat)

    return (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon)


def matrix_dist_duration(
    lat_origem: float,
    lon_origem: float,
    destinos: list[tuple[float, float]],
    modo_ors: str,
) -> tuple[list[float | None], list[float | None]]:
    """
    Retorna (dist_km_list, dur_min_list) na mesma ordem de destinos.
    """
    url = f"https://api.openrouteservice.org/v2/matrix/{modo_ors}"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}

    # ORS espera [lon, lat]
    locations = [[lon_origem, lat_origem]] + [[lon, lat] for (lat, lon) in destinos]

    payload = {
        "locations": locations,
        "metrics": ["distance", "duration"],
        "units": "km",
        "sources": [0],
        "destinations": list(range(1, len(locations))),
    }

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()

    dist = (data.get("distances") or [[None]])[0]
    dur = (data.get("durations") or [[None]])[0]
    dur_min = [None if d is None else d / 60 for d in dur]
    return dist, dur_min


# ======= Endpoint para popular select de animais =======
@busca_router.get("/animais")
async def listar_animais(session: Session = Depends(iniciar_session)):
    rows = (
        session.query(Acidente.animal_tipo_desc)
        .distinct()
        .order_by(Acidente.animal_tipo_desc)
        .all()
    )

    out = []
    for (nome,) in rows:
        if not nome:
            continue
        # só devolve opções que o backend consegue mapear para soro
        if identificar_coluna_soro(nome) is None:
            continue
        out.append({"label": nome, "value": nome})

    return out


# ======= Busca otimizada (rápida) =======
@busca_router.get("/postos")
async def buscar_postos(
    endereco: str = Query(..., min_length=5),
    numero: str = Query(..., min_length=1),
    municipio: str = Query(..., min_length=2),
    animal: str = Query(..., min_length=2),
    modo: str = Query("carro", description="carro | caminhando | bicicleta"),
    limite: int = Query(10, ge=1, le=30),
    session: Session = Depends(iniciar_session),
):

    """
    1) Geocodifica o endereço
    2) Filtra postos com soro no DB
    3) Pré-seleciona TOP_MATRIX por Haversine (linha reta) -> rápido
    4) Chama ORS Matrix 1x nesses TOP_MATRIX -> tempo/dist real
    5) Ordena por tempo e retorna top N
    """
    try:
        lat_o, lon_o = geocodificar_origem(endereco, municipio)


        coluna_soro = identificar_coluna_soro(animal)
        if not coluna_soro:
            raise HTTPException(status_code=400, detail="Animal não reconhecido ou sem mapeamento de soro.")

        # Pré-filtro no DB por bounding box
        raio_km = raio_por_modo_km(modo)
        min_lat, max_lat, min_lon, max_lon = bounding_box(lat_o, lon_o, raio_km)

        q = (
            session.query(Posto)
            .filter(
                getattr(Posto, coluna_soro) == 1,
                Posto.latitude.isnot(None),
                Posto.longitude.isnot(None),
                Posto.latitude >= min_lat,
                Posto.latitude <= max_lat,
                Posto.longitude >= min_lon,
                Posto.longitude <= max_lon,
            )
        )

        postos_bb = q.all()

        # fallback se o bounding box retornar vazio
        if not postos_bb:
            postos_bb = (
                session.query(Posto)
                .filter(
                    getattr(Posto, coluna_soro) == 1,
                    Posto.latitude.isnot(None),
                    Posto.longitude.isnot(None),
                )
                .all()
            )

        if not postos_bb:
            return {"erro": "Nenhum posto encontrado com esse soro."}

        # Ordena por haversine e pega TOP_MATRIX (rápido)
        candidatos = []
        for p in postos_bb:
            d = haversine_km(lat_o, lon_o, p.latitude, p.longitude)
            candidatos.append((d, p))

        candidatos.sort(key=lambda x: x[0])
        postos_sel = [p for _, p in candidatos[:TOP_MATRIX]]

        # ORS matrix 1x (TOP_MATRIX <= 40)
        modo_ors = modo_para_ors(modo)
        destinos = [(p.latitude, p.longitude) for p in postos_sel]
        dist_km, dur_min = matrix_dist_duration(lat_o, lon_o, destinos, modo_ors)

        resultados = []
        for p, d, t in zip(postos_sel, dist_km, dur_min):
            if d is None or t is None:
                continue
            resultados.append(
                {
                    "id": p.id,
                    "ubs": p.ubs,
                    "endereco": p.endereco,
                    "municipio": p.municipio_nome,
                    "telefone": p.telefone,
                    "distancia_km": float(d),
                    "tempo_min": float(t),
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "soro_coluna": coluna_soro,
                }
            )

        if not resultados:
            return {"erro": "Não foi possível calcular distâncias/tempos para os postos."}

        resultados.sort(key=lambda x: x["tempo_min"])

        return {
            "origem": {"endereco": endereco, "lat": lat_o, "lon": lon_o},
            "animal": animal,
            "modo": modo,
            "soro_coluna": coluna_soro,
            "total_considerados": len(postos_bb),
            "enviados_para_matrix": len(postos_sel),
            "top": resultados[:limite],
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Erro ao consultar ORS: {str(e)}")
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno na busca.")
