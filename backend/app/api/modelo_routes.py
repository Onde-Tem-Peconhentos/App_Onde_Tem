from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, text
import json
import os
from dotenv import load_dotenv

load_dotenv('/home/gabi/wkplace/ProjetoIC/App_Onde_Tem/backend/.env.example') # placeholder
DB_URI = os.getenv("DATABASE_URL")


modelo_router = APIRouter(prefix="/api", tags=["modelo"])

engine = create_engine(DB_URI)

@modelo_router.get("/modelo")
def get_modelo(animal: str, metodo: str, tipo_periodo: str):
    """
    Retorna os resultados do modelo mais recente com base em tipo_periodo.

    Parameters
    ----------
    animal       : Nome do animal (ex: "Serpente")
    metodo       : Método usado ("ols" ou "gwr")
    tipo_periodo : Tipo do período (ex: "mes")
    """
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT 
                forecast_month,
                data_processamento,
                geojson_observado,
                geojson_predito,
                geojson_residuo,
                geojson_forecast,
                mse,
                rmse,
                mae,
                r2,
                gain_vs_media_municipal,
                selected_features,
                gwr_bandwidth_km
            FROM modelos.previsao
            WHERE animal       = :animal
              AND metodo       = :metodo
              AND tipo_periodo = :tipo_periodo
            ORDER BY data_processamento DESC, forecast_month DESC
            LIMIT 1;
        """), {
            "animal":       animal,
            "metodo":       metodo.lower(),  # Garante lowercase
            "tipo_periodo": tipo_periodo,
        }).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Modelo não encontrado para animal='{animal}', metodo='{metodo}', tipo_periodo='{tipo_periodo}'"
        )

    def parse_geo(val):
        return json.loads(val) if isinstance(val, str) else val

    # Índices corretos conforme o SELECT
    raw_features = row[11]  # selected_features está na posição 11
    if isinstance(raw_features, str):
        selected_features = json.loads(raw_features)
    elif isinstance(raw_features, list):
        selected_features = raw_features
    else:
        selected_features = []

    return {
        "animal":               animal,
        "metodo":               metodo,
        "tipo_periodo":         tipo_periodo,
        "forecast_month":       str(row[0]) if row[0] else None,
        "data_processamento":   str(row[1]) if row[1] else None,

        "geojson_observado":    parse_geo(row[2]),
        "geojson_predito":      parse_geo(row[3]),
        "geojson_residuo":      parse_geo(row[4]),
        "geojson_forecast":     parse_geo(row[5]),

        "metrics": {
            "mse":                     row[6],
            "rmse":                    row[7],
            "mae":                     row[8],
            "r2":                      row[9],
            "gain_vs_media_municipal": row[10],
        },

        "hyperparams": {
            "gwr_bandwidth_km": row[12],  # posição 12
        },

        "meta": {
            "selected_features": selected_features,  # posição 11
        }
    }