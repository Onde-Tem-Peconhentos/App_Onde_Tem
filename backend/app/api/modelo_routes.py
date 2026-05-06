from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, text
import json
import os

modelo_router = APIRouter(prefix="/api", tags=["modelo"])

DB_URI = os.getenv("DB_URI", "postgresql+psycopg2://etl_user:etl_pass@localhost:5432/etl_db")
engine = create_engine(DB_URI)

@modelo_router.get("/modelo")
def get_modelo(animal: str, metodo: str, periodo: str):

    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT geojson_observado, geojson_predito
            FROM modelos_previsao
            WHERE animal  = :animal
              AND metodo  = :metodo
              AND periodo = '2026-02'
            LIMIT 1;
        """), {
            "animal":  animal,
            "metodo":  metodo,
        }).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Modelo não encontrado: {animal}, {metodo}, {periodo}")

    def parse_geo(val):
        if isinstance(val, str):
            return json.loads(val)
        return val

    return {
        "geojson_observado": parse_geo(row[0]),
        "geojson_predito":   parse_geo(row[1]),
    }