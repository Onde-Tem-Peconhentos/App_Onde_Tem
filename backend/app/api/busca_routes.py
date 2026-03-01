from __future__ import annotations

import os
import unicodedata
from typing import Optional
import math

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import iniciar_session
from db.models import Posto, Acidente 

busca_router = APIRouter(prefix="/busca", tags=["busca"])

ORS_API_KEY = os.getenv("ORS_API_KEY")
TOP_MATRIX = 5

def normalizar(texto: str) -> str:
    if not texto: return ""
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .lower()
        .strip()
    )

def identificar_coluna_soro(animal: str) -> Optional[str]:
    a = normalizar(animal)
    mapa = {
        "jararaca": "botropico", "botropico": "botropico",
        "cascavel": "crotalico", "crotalico": "crotalico",
        "coral": "elapidico", "elapidico": "elapidico",
        "surucucu": "botropico", "laquetico": "botropico", 
        "escorpiao": "escorpionico", "escorpionico": "escorpionico",
        "aranha": "aracnidico", "aracnidico": "aracnidico",
        "taturana": "lonomico", "lonomia": "lonomico", "lagarta": "lonomico",
    }
    if a in mapa: return mapa[a]
    if "jarar" in a or "botrop" in a: return "botropico"
    if "cascav" in a or "crotal" in a: return "crotalico"
    if "coral" in a or "elap" in a: return "elapidico"
    if "escorp" in a: return "escorpionico"
    if "aranh" in a or "aracn" in a: return "aracnidico"
    if "lagart" in a or "lonom" in a: return "lonomico"
    return None

def modo_para_ors(modo: str) -> str:
    m = normalizar(modo)
    if m in ["carro", "driving"]: return "driving-car"
    if m in ["caminhando", "a pe", "ape", "walking", "pe"]: return "foot-walking"
    if m in ["bicicleta", "bike", "cycling"]: return "cycling-regular"
    return "driving-car"

def raio_por_modo_km(modo: str) -> float:
    m = normalizar(modo)
    if m in ["caminhando", "a pe", "ape", "walking", "pe"]: return 8.0
    if m in ["bicicleta", "bike"]: return 15.0
    return 30.0

def geocodificar_origem(endereco_bruto: str, municipio_selecionado: str) -> tuple[float, float]:
    if not ORS_API_KEY: raise ValueError("ORS_API_KEY não configurada.")
    url = "https://api.openrouteservice.org/geocode/search"
    params = {"api_key": ORS_API_KEY, "text": endereco_bruto, "boundary.country": "BR", "size": 3}
    
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    feats = data.get("features") or []
    if not feats: raise ValueError("Localização não encontrada.")
    
    municipio_alvo = normalizar(municipio_selecionado)
    melhor_feat = None

    # Varre os resultados em busca de QUALQUER menção ao município selecionado
    for f in feats:
        props = f.get("properties") or {}
        # Campos onde a cidade pode estar escondida
        campos_busca = [
            props.get("locality", ""),
            props.get("county", ""),
            props.get("region", ""),
            props.get("label", ""),
            props.get("neighborhood", "")
        ]
        
        # Se o nome do município (normalizado) estiver em qualquer um desses campos, é o certo!
        if any(municipio_alvo in normalizar(campo) for campo in campos_busca):
            melhor_feat = f
            break

    # Se varremos tudo e não achamos o nome da cidade, agora sim barramos o acesso
    if not melhor_feat:
        raise ValueError(f"O local encontrado não pertence a {municipio_selecionado}.")
        
    lon, lat = melhor_feat["geometry"]["coordinates"]
    return float(lat), float(lon)

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def bounding_box(lat: float, lon: float, raio_km: float) -> tuple[float, float, float, float]:
    delta_lat = raio_km / 111.0
    delta_lon = raio_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    return (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon)

def matrix_dist_duration(lat_o, lon_o, destinos, modo_ors) -> tuple[list, list]:
    url = f"https://api.openrouteservice.org/v2/matrix/{modo_ors}"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    locations = [[lon_o, lat_o]] + [[lon, lat] for (lat, lon) in destinos]
    payload = {"locations": locations, "metrics": ["distance", "duration"], "units": "km", "sources": [0], "destinations": list(range(1, len(locations)))}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    dur_min = [None if d is None else d / 60 for d in (data.get("durations") or [[None]])[0]]
    return (data.get("distances") or [[None]])[0], dur_min

@busca_router.get("/postos")
async def buscar_postos(
    endereco: Optional[str] = Query(None), 
    numero: Optional[str] = Query(None), 
    bairro: Optional[str] = Query(None),
    cep: Optional[str] = Query(None), # Adicione este parâmetro se ainda não tiver
    municipio: str = Query(...), 
    animal: str = Query(...), 
    modo: str = Query("carro"),
    limite: int = Query(10), 
    session: Session = Depends(iniciar_session)
):
    try:
        # Se o usuário mandou CEP, limpamos e formatamos com o hífen (00000-000)
        if cep:
            cep_limpo = "".join(filter(str.isdigit, cep))
            if len(cep_limpo) == 8:
                cep_formatado = f"{cep_limpo[:5]}-{cep_limpo[5:]}"
                search_text = f"{cep_formatado}, {municipio}, SP, Brasil"
            else:
                search_text = f"{endereco}, {numero} - {bairro}, {municipio}, SP"
        else:
            search_text = f"{endereco}, {numero} - {bairro}, {municipio}, SP"

        lat_o, lon_o = geocodificar_origem(search_text, municipio)
        coluna_soro = identificar_coluna_soro(animal)
        
        if not coluna_soro:
            return {"erro": f"Soro para '{animal}' não mapeado."}

        min_lat, max_lat, min_lon, max_lon = bounding_box(lat_o, lon_o, raio_por_modo_km(modo))
        
        postos_bb = session.query(Posto).filter(
            getattr(Posto, coluna_soro) == 1,
            Posto.latitude.between(min_lat, max_lat),
            Posto.longitude.between(min_lon, max_lon)
        ).all()
        
        if not postos_bb:
            postos_bb = session.query(Posto).filter(getattr(Posto, coluna_soro) == 1).all()

        if not postos_bb: return {"erro": "Nenhum posto encontrado."}

        candidatos = sorted([(haversine_km(lat_o, lon_o, p.latitude, p.longitude), p) for p in postos_bb], key=lambda x: x[0])[:TOP_MATRIX]
        postos_sel = [c[1] for c in candidatos]
        dist, dur = matrix_dist_duration(lat_o, lon_o, [(p.latitude, p.longitude) for p in postos_sel], modo_para_ors(modo))

        resultados = []
        for p, d, t in zip(postos_sel, dist, dur):
            if d is None: continue
            resultados.append({
                "id": p.id, "ubs": p.ubs, "endereco": p.endereco, "municipio": p.municipio_nome,
                "distancia_km": round(float(d), 2), "tempo_min": round(float(t), 1),
                "latitude": p.latitude, "longitude": p.longitude
            })
        
        return {
            "origem": {"lat": lat_o, "lon": lon_o, "endereco": search_text}, 
            "top": sorted(resultados, key=lambda x: x["tempo_min"])[:limite]
        }

    except ValueError as e: raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro interno na busca.")