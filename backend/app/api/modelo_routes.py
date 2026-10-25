from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, text
import json
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv('/home/gabi/wkplace/ProjetoIC/App_Onde_Tem/backend/.env.example') 
DB_URI = os.getenv("DATABASE_URL")

modelo_router = APIRouter(prefix="/api", tags=["modelo"])
engine = create_engine(DB_URI)

@modelo_router.get("/modelo")
def get_modelo(animal: str, metodo: str, tipo_periodo: str):
    """
    Retorna os resultados do modelo mais recente persistido no banco de dados.

    Parameters
    ----------
    animal       : Nome do animal (ex: "Serpente")
    metodo       : Método usado ("ols", "gwr", "gwr_adaptativo", "gtwr")
    tipo_periodo : Tipo do período (ex: "Mês")
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
                gwr_bandwidth_km,
                gwr_bandwidth_k,
                gtwr_bandwidth_s,
                gtwr_tau,
                moran_i_medio,
                moran_p_sim_medio,
                moran_meses_signif,
                train_month_inicio,
                train_month_fim,
                test_month_inicio,
                test_month_fim,
                test_last_month,
                coeficientes,
                estabilidade_variaveis
            FROM modelos.bz_previsao
            WHERE animal       = :animal
              AND metodo       = :metodo
              AND tipo_periodo = :tipo_periodo
            ORDER BY data_processamento DESC, forecast_month DESC
            LIMIT 1;
        """), {
            "animal":       animal,
            "metodo":       metodo.lower(),  # Garante lowercase para alinhar com o fit_mensal
            "tipo_periodo": tipo_periodo,
        }).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Modelo não encontrado para animal='{animal}', metodo='{metodo}', tipo_periodo='{tipo_periodo}'"
        )

    # Converte o row do SQLAlchemy para um dicionário seguro acessível por chaves
    row_dict = row._mapping if hasattr(row, '_mapping') else dict(row)

    def parse_geo(val):
        return json.loads(val) if isinstance(val, str) else val

    # Tratamento seguro da lista de features
    raw_features = row_dict["selected_features"]
    if isinstance(raw_features, str):
        selected_features = json.loads(raw_features)
    elif isinstance(raw_features, list):
        selected_features = raw_features
    else:
        selected_features = []

    return {
        "animal":              animal,
        "metodo":              metodo,
        "tipo_periodo":        tipo_periodo,
        "forecast_month":      str(row_dict["forecast_month"]) if row_dict["forecast_month"] else None,
        "data_processamento":  str(row_dict["data_processamento"]) if row_dict["data_processamento"] else None,

        # Mapas
        "geojson_observado":   parse_geo(row_dict["geojson_observado"]),
        "geojson_predito":     parse_geo(row_dict["geojson_predito"]),
        "geojson_residuo":     parse_geo(row_dict["geojson_residuo"]),
        "geojson_forecast":    parse_geo(row_dict["geojson_forecast"]),

        # Métricas de Erro e Dependência Espacial (Moran)
        "metrics": {
            "mse":                     row_dict["mse"],
            "rmse":                    row_dict["rmse"],
            "mae":                     row_dict["mae"],
            "r2":                      row_dict["r2"],
            "gain_vs_media_municipal": row_dict["gain_vs_media_municipal"],
            "moran_i_medio":           row_dict["moran_i_medio"],
            "moran_p_sim_medio":       row_dict["moran_p_sim_medio"],
            "moran_meses_signif":      row_dict["moran_meses_signif"],
        },

        # Parâmetros Estruturais Espaço-Temporais
        "hyperparams": {
            "gwr_bandwidth_km":    row_dict["gwr_bandwidth_km"],
            "gwr_bandwidth_k":     row_dict["gwr_bandwidth_k"],
            "gtwr_bandwidth_s":    row_dict["gtwr_bandwidth_s"],
            "gtwr_tau":            row_dict["gtwr_tau"],
        },

        "meta": {
            "selected_features": selected_features,
            # Limites do split temporal (mesmo formato de período usado por
            # tipo_periodo: AAAAMM/mês, AAAAT/trimestre, AAAAS/semestre, AAAA/ano).
            "train_period_inicio": row_dict["train_month_inicio"],
            "train_period_fim":    row_dict["train_month_fim"],
            "test_period_inicio":  row_dict["test_month_inicio"],
            "test_period_fim":     row_dict["test_month_fim"],
            "test_last_period":    row_dict["test_last_month"],
        },

        # Peso de cada variável: valor único (OLS) ou quartis entre
        # municípios/observações (modelos locais — GWR, GWR-Adaptativo,
        # GTWR). None para linhas gravadas antes desta coluna existir.
        "pesos_variaveis": parse_geo(row_dict["coeficientes"]),

        # Estabilidade de cada variável do modelo final: em quantas janelas
        # rolling de seleção ela apareceu. None para linhas antigas.
        "estabilidade_variaveis": parse_geo(row_dict["estabilidade_variaveis"]),
    }


@modelo_router.get("/modelo/comparativo")
def get_modelo_comparativo(tipo_periodo: str = "Semestre", animal: str | None = None):
    """
    Retorna, para todos os métodos (os 4 modelos reais e as 3 baselines), as
    métricas mais recentes persistidas para uma periodicidade — usado pela
    tabela comparativa da página Modelos. Se `animal` for informado, filtra
    só aquele animal (é assim que a página usa: tabela específica do
    animal/período escolhidos nos filtros, com o modelo do filtro em
    destaque); sem `animal`, retorna todos os animais.

    Para cada (animal, método), pega só a linha mais recente
    (maior data_processamento) — os dados nunca são sobrescritos no banco, só
    acumulados, então isso garante a última execução de cada combinação.
    """
    query = """
        SELECT DISTINCT ON (animal, metodo)
            animal, metodo, n_train, n_test,
            mse, rmse, mae, r2, gain_vs_media_municipal,
            gwr_bandwidth_km, gwr_bandwidth_k, gtwr_bandwidth_s, gtwr_tau,
            forecast_month, data_processamento
        FROM modelos.bz_previsao
        WHERE tipo_periodo = :tipo_periodo
    """
    params = {"tipo_periodo": tipo_periodo}
    if animal:
        query += " AND animal = :animal"
        params["animal"] = animal
    query += " ORDER BY animal, metodo, data_processamento DESC"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    resultados = []
    for row in rows:
        r = row._mapping if hasattr(row, "_mapping") else dict(row)
        resultados.append({
            "animal":                  r["animal"],
            "metodo":                  r["metodo"],
            "n_train":                 r["n_train"],
            "n_test":                  r["n_test"],
            "mse":                     r["mse"],
            "rmse":                    r["rmse"],
            "mae":                     r["mae"],
            "r2":                      r["r2"],
            "gain_vs_media_municipal": r["gain_vs_media_municipal"],
            "gwr_bandwidth_km":        r["gwr_bandwidth_km"],
            "gwr_bandwidth_k":         r["gwr_bandwidth_k"],
            "gtwr_bandwidth_s":        r["gtwr_bandwidth_s"],
            "gtwr_tau":                r["gtwr_tau"],
            "forecast_month":          str(r["forecast_month"]) if r["forecast_month"] else None,
            "data_processamento":      str(r["data_processamento"]) if r["data_processamento"] else None,
        })

    return {"tipo_periodo": tipo_periodo, "resultados": resultados}


@modelo_router.get("/modelo/resumo")
def get_modelo_resumo():
    """
    Desempenho médio de cada método, agregando a linha mais recente de cada
    (tipo_periodo, animal, metodo) — a mesma lógica usada em /modelo/comparativo,
    só que aqui a média é calculada no banco em vez de por filtro. Retorna um
    resumo geral (todas as cadências juntas) e um detalhado por cadência,
    usado pela tabela colapsável na página de Modelos (antes dos filtros).
    """
    query = """
        WITH latest AS (
            SELECT DISTINCT ON (tipo_periodo, animal, metodo)
                tipo_periodo, animal, metodo, mse, rmse, mae, r2, gain_vs_media_municipal
            FROM modelos.bz_previsao
            ORDER BY tipo_periodo, animal, metodo, data_processamento DESC
        ),
        ranked AS (
            SELECT *, RANK() OVER (PARTITION BY tipo_periodo, animal ORDER BY mse ASC) AS rk
            FROM latest
        )
        SELECT tipo_periodo, metodo,
            count(*) AS n,
            avg(r2) AS r2_medio,
            avg(gain_vs_media_municipal) AS gain_medio,
            avg(rmse) AS rmse_medio,
            avg(mae) AS mae_medio,
            count(*) FILTER (WHERE rk = 1) AS vitorias
        FROM ranked
        GROUP BY tipo_periodo, metodo
    """
    with engine.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(query))]

    def fmt(rows_subset):
        return [{
            "metodo": r["metodo"],
            "n": r["n"],
            "r2_medio": r["r2_medio"],
            "gain_medio": r["gain_medio"],
            "rmse_medio": r["rmse_medio"],
            "mae_medio": r["mae_medio"],
            "vitorias": r["vitorias"],
        } for r in rows_subset]

    geral = {}
    for r in rows:
        acc = geral.setdefault(r["metodo"], {
            "metodo": r["metodo"], "n": 0, "soma_r2": 0.0, "soma_gain": 0.0,
            "soma_rmse": 0.0, "soma_mae": 0.0, "vitorias": 0,
        })
        acc["n"] += r["n"]
        acc["soma_r2"] += (r["r2_medio"] or 0) * r["n"]
        acc["soma_gain"] += (r["gain_medio"] or 0) * r["n"]
        acc["soma_rmse"] += (r["rmse_medio"] or 0) * r["n"]
        acc["soma_mae"] += (r["mae_medio"] or 0) * r["n"]
        acc["vitorias"] += r["vitorias"]

    resumo_geral = sorted([{
        "metodo": acc["metodo"],
        "n": acc["n"],
        "r2_medio": acc["soma_r2"] / acc["n"] if acc["n"] else None,
        "gain_medio": acc["soma_gain"] / acc["n"] if acc["n"] else None,
        "rmse_medio": acc["soma_rmse"] / acc["n"] if acc["n"] else None,
        "mae_medio": acc["soma_mae"] / acc["n"] if acc["n"] else None,
        "vitorias": acc["vitorias"],
    } for acc in geral.values()], key=lambda r: r["gain_medio"] or -999, reverse=True)

    por_cadencia = {}
    for r in rows:
        por_cadencia.setdefault(r["tipo_periodo"], []).append(r)
    por_cadencia = {
        tp: sorted(fmt(lista), key=lambda r: r["gain_medio"] or -999, reverse=True)
        for tp, lista in por_cadencia.items()
    }

    return {"geral": resumo_geral, "por_cadencia": por_cadencia}