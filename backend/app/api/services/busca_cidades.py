from __future__ import annotations

import os
import time
import unicodedata
from functools import lru_cache
from typing import Optional

import numpy as np
import pandas as pd
import requests
from scipy.sparse.csgraph import dijkstra
from shapely.geometry import shape
from sqlalchemy.orm import Session

from db.models import Posto

ORS_API_KEY = os.getenv("ORS_API_KEY")
MAX_DESTINOS = 40
SLEEP_TIME = 0.5

MATRIZ_URL = "https://raw.githubusercontent.com/juliabu3no/Projeto-IC/refs/heads/main/Dados/matriz_dist_cidades.csv"
GEOJSON_SP_URL = "https://raw.githubusercontent.com/juliabu3no/Projeto-IC/refs/heads/main/Dados/geojson_sp.json"


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    return (
        unicodedata.normalize("NFKD", str(texto))
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .lower()
        .strip()
    )


def identificar_coluna_soro(animal: str) -> Optional[str]:
    a = normalizar(animal)

    mapa = {
        "jararaca": "botropico",
        "botropico": "botropico",
        "cascavel": "crotalico",
        "crotalico": "crotalico",
        "coral": "elapidico",
        "elapidico": "elapidico",
        "escorpiao": "escorpionico",
        "escorpionico": "escorpionico",
        "aranha": "aracnidico",
        "aracnidico": "aracnidico",
        "taturana": "lonomico",
        "lonomia": "lonomico",
        "lagarta": "lonomico",
        "lonomico": "lonomico",
    }

    if a in mapa:
        return mapa[a]

    if "jarar" in a or "botrop" in a:
        return "botropico"
    if "cascav" in a or "crotal" in a:
        return "crotalico"
    if "coral" in a or "elap" in a:
        return "elapidico"
    if "escorp" in a:
        return "escorpionico"
    if "aranh" in a or "aracn" in a:
        return "aracnidico"
    if "lagart" in a or "lonom" in a or "tatur" in a:
        return "lonomico"

    return None


def modo_para_ors(modo: str) -> str:
    m = normalizar(modo)
    if m in ["carro", "driving"]:
        return "driving-car"
    if m in ["caminhando", "a pe", "ape", "walking", "pe"]:
        return "foot-walking"
    if m in ["bicicleta", "bike", "cycling"]:
        return "cycling-regular"
    return "driving-car"


def buscar_endereco_por_cep(cep: str) -> dict:
    cep = "".join(filter(str.isdigit, cep))
    if len(cep) != 8:
        raise ValueError("CEP inválido.")

    url = f"https://viacep.com.br/ws/{cep}/json/"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()

    if data.get("erro"):
        raise ValueError("CEP não encontrado.")

    return {
        "street": data.get("logradouro", ""),
        "district": data.get("bairro", ""),
        "city": data.get("localidade", ""),
        "uf": data.get("uf", ""),
        "cep": cep,
    }


def geocodificar_origem(
    tipo_entrada: str,
    entrada: str,
    api_key: str,
) -> tuple[tuple[float, float], Optional[dict], str]:
    if not api_key:
        raise ValueError("ORS_API_KEY não configurada.")

    if tipo_entrada == "cep":
        endereco_completo = buscar_endereco_por_cep(entrada)
        partes = [
            endereco_completo.get("street", ""),
            endereco_completo.get("district", ""),
            endereco_completo.get("city", ""),
            endereco_completo.get("uf", ""),
            f"CEP {endereco_completo.get('cep', '')}",
            "Brasil",
        ]
        endereco_busca = ", ".join([p for p in partes if p])

    elif tipo_entrada == "endereco":
        endereco_busca = entrada.strip()
        endereco_completo = None
        if not endereco_busca:
            raise ValueError("Endereço vazio.")
    else:
        raise ValueError("Tipo de entrada inválido.")

    url = "https://api.openrouteservice.org/geocode/search"
    params = {
        "api_key": api_key,
        "text": endereco_busca,
        "boundary.country": "BR",
        "size": 5,
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    features = data.get("features") or []
    if not features:
        raise ValueError("Local não encontrado.")

    coords = features[0]["geometry"]["coordinates"]
    return (float(coords[1]), float(coords[0])), endereco_completo, endereco_busca


def reverse_geocodificar_origem(
    latitude: float,
    longitude: float,
    api_key: str,
) -> dict:
    nominatim_data = {}
    ors_data = {}

    try:
        nominatim_url = "https://nominatim.openstreetmap.org/reverse"
        nominatim_params = {
            "format": "jsonv2",
            "lat": latitude,
            "lon": longitude,
            "addressdetails": 1,
            "zoom": 18,
            "accept-language": "pt-BR",
        }
        nominatim_headers = {"User-Agent": "App_Onde_Tem/1.0"}

        nominatim_response = requests.get(
            nominatim_url,
            params=nominatim_params,
            headers=nominatim_headers,
            timeout=15,
        )
        nominatim_response.raise_for_status()
        address = (nominatim_response.json() or {}).get("address") or {}

        nominatim_data = {
            "endereco": address.get("road") or address.get("pedestrian") or address.get("path") or "",
            "numero": address.get("house_number") or "",
            "bairro": address.get("suburb") or address.get("neighbourhood") or address.get("quarter") or "",
            "municipio": address.get("city") or address.get("town") or address.get("village") or address.get("municipality") or "",
            "cep": address.get("postcode") or "",
        }
    except Exception:
        nominatim_data = {}

    if api_key:
        try:
            ors_url = "https://api.openrouteservice.org/geocode/reverse"
            ors_params = {
                "api_key": api_key,
                "point.lon": longitude,
                "point.lat": latitude,
                "size": 1,
            }

            ors_response = requests.get(ors_url, params=ors_params, timeout=15)
            ors_response.raise_for_status()
            features = (ors_response.json() or {}).get("features") or []
            properties = features[0].get("properties") if features else {}

            ors_data = {
                "endereco": properties.get("street") or properties.get("name") or "",
                "numero": properties.get("housenumber") or "",
                "bairro": properties.get("neighbourhood") or properties.get("borough") or "",
                "municipio": properties.get("locality") or properties.get("county") or "",
                "cep": properties.get("postalcode") or "",
            }
        except Exception:
            ors_data = {}

    merged = {
        "endereco": nominatim_data.get("endereco") or ors_data.get("endereco") or "",
        "numero": nominatim_data.get("numero") or ors_data.get("numero") or "",
        "bairro": nominatim_data.get("bairro") or ors_data.get("bairro") or "",
        "municipio": nominatim_data.get("municipio") or ors_data.get("municipio") or "",
        "cep": nominatim_data.get("cep") or ors_data.get("cep") or "",
    }

    if not any(merged.values()):
        raise ValueError("Não foi possível localizar um endereço para as coordenadas informadas.")

    return merged


@lru_cache(maxsize=1)
def carregar_malha_cidades():
    df_matriz = pd.read_csv(MATRIZ_URL, index_col=0)
    cidades = df_matriz.index.tolist()
    matriz = df_matriz.values

    geojson = requests.get(GEOJSON_SP_URL, timeout=20).json()

    coordenadas = []
    for feature in geojson["features"]:
        centroide = shape(feature["geometry"]).centroid
        coordenadas.append((centroide.y, centroide.x))

    return cidades, matriz, coordenadas


def calcular_cidades_proximas(origem_coords: tuple[float, float], top_n: int = 25) -> list[str]:
    cidades, matriz, coordenadas = carregar_malha_cidades()

    lat_origem, lon_origem = origem_coords

    dist_cidades = [
        np.linalg.norm(np.subtract((lat_origem, lon_origem), (lat, lon)))
        for lat, lon in coordenadas
    ]

    cidade_origem = cidades[int(np.argmin(dist_cidades))]

    cidades_normalizadas = [normalizar(c) for c in cidades]
    origem_idx = cidades_normalizadas.index(normalizar(cidade_origem))

    distancias, _ = dijkstra(
        matriz,
        directed=False,
        indices=origem_idx,
        return_predecessors=True,
    )

    resultado = pd.DataFrame({
        "Cidade": cidades,
        "Distancia": distancias,
    }).sort_values(by="Distancia")

    return resultado["Cidade"].head(top_n).tolist()


def buscar_postos_por_cidades_e_soro(
    session: Session,
    animal: str,
    cidades_proximas: list[str],
) -> list[Posto]:
    coluna_soro = identificar_coluna_soro(animal)
    if not coluna_soro:
        raise ValueError(f"Soro para '{animal}' não mapeado no banco atual.")

    cidades_norm = {normalizar(c) for c in cidades_proximas}

    postos = session.query(Posto).filter(getattr(Posto, coluna_soro) == 1).all()

    filtrados = []
    for p in postos:
        municipio = p.municipio_nome or ""
        if normalizar(municipio) in cidades_norm:
            if p.latitude is not None and p.longitude is not None:
                filtrados.append(p)

    return filtrados


def calcular_distancias_postos_em_blocos(
    postos: list[Posto],
    origem_coords: tuple[float, float],
    modo_ors: str,
    api_key: str,
) -> list[dict]:
    if not postos:
        return []

    lat_origem, lon_origem = origem_coords
    resultados = []

    for i in range(0, len(postos), MAX_DESTINOS):
        bloco = postos[i:i + MAX_DESTINOS]

        locations = [[float(lon_origem), float(lat_origem)]]
        for p in bloco:
            locations.append([float(p.longitude), float(p.latitude)])

        url = f"https://api.openrouteservice.org/v2/matrix/{modo_ors}"
        headers = {"Authorization": api_key, "Content-Type": "application/json"}
        payload = {
            "locations": locations,
            "metrics": ["distance", "duration"],
            "units": "km",
            "sources": [0],
            "destinations": list(range(1, len(locations))),
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        distancias = (data.get("distances") or [[None]])[0]
        duracoes = (data.get("durations") or [[None]])[0]

        for posto, dist_km, dur_s in zip(bloco, distancias, duracoes):
            if dist_km is None:
                continue

            resultados.append({
                "id": posto.id,
                "ubs": posto.ubs,
                "endereco": posto.endereco,
                "municipio": posto.municipio_nome,
                "telefone": posto.telefone,
                "tipo_soro": posto.tipo_soro,
                "aberto_24h": posto.aberto_24h,
                "latitude": float(posto.latitude),
                "longitude": float(posto.longitude),
                "distancia_km": round(float(dist_km), 2),
                "tempo_min": round(float(dur_s) / 60, 1) if dur_s is not None else None,
            })

        time.sleep(SLEEP_TIME)

    return resultados