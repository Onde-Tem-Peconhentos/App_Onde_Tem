"""
geospatial.py — Construção de GeoJSONs com escalas de cores.

Escalas disponíveis:
  - "incidence" : branco (baixa incidência) → vermelho (alta incidência),
                  escala baseada em casos por 100 mil habitantes,
                  compartilhada entre observado e predito.
  - "diverging" : azul (negativo) → branco (zero) → vermelho (positivo),
                  usada para resíduos (também em incidência por 100 mil).
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd


# ── Paletas de cores ──────────────────────────────────────────────────────────

def _lerp(a: int, b: int, t: float) -> int:
    """Interpolação linear inteira entre a e b."""
    return int(round(a + (b - a) * t))


def _color_incidence(x: float, vmin: float, vmax: float, alpha: int = 180) -> list[int]:
    """
    Escala sequencial por incidência (casos / 100 mil hab):
      branco (vmin) → vermelho escuro (vmax).
    Valores fora do intervalo são clampados.
    """
    if vmax <= vmin:
        return [255, 255, 255, alpha]
    t = max(0.0, min(1.0, (x - vmin) / (vmax - vmin)))
    r = _lerp(255, 220, t)
    g = _lerp(255, 20,  t)
    b = _lerp(255, 20,  t)
    return [r, g, b, alpha]


def _color_diverging(x: float, max_abs: float, alpha: int = 180) -> list[int]:
    """
    Escala divergente: azul (negativo) → branco (zero) → vermelho (positivo).
    """
    if max_abs < 1e-9:
        return [255, 255, 255, alpha]
    t = max(-1.0, min(1.0, x / max_abs))
    if t >= 0:
        r = _lerp(255, 220, t)
        g = _lerp(255, 20,  t)
        b = _lerp(255, 20,  t)
    else:
        t = abs(t)
        r = _lerp(255, 20,  t)
        g = _lerp(255, 20,  t)
        b = _lerp(255, 220, t)
    return [r, g, b, alpha]


# ── Helpers de GeoDataFrame ───────────────────────────────────────────────────

def _to_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    if "geometry" not in df.columns:
        raise ValueError("DataFrame precisa ter coluna 'geometry'.")
    geom = df["geometry"]
    if isinstance(geom.iloc[0], str):
        geom = gpd.GeoSeries.from_wkt(geom)
    gdf = gpd.GeoDataFrame(df.copy(), geometry=geom)
    gdf = gdf.set_crs("EPSG:4326") if gdf.crs is None else gdf.to_crs("EPSG:4326")
    gdf["geometry"] = gdf.geometry.simplify(tolerance=0.005, preserve_topology=True)
    return gdf


def _to_geojson_dict(gdf: gpd.GeoDataFrame) -> dict:
    d = gdf.__geo_interface__
    d["bbox"] = gdf.total_bounds.tolist()
    return d


# ── API pública ───────────────────────────────────────────────────────────────

_POP_BASE = 100_000  # casos por 100 mil habitantes


def _incidence(casos: pd.Series, populacao: pd.Series) -> pd.Series:
    """
    Taxa de incidência: casos / populacao * 100_000.
    Municípios com população <= 0 ou NaN recebem 0.
    """
    pop = populacao.replace(0, np.nan)
    return (casos / pop * _POP_BASE).fillna(0.0)


def build_geojsons(
    df_mun: pd.DataFrame,
    df_predicoes: pd.DataFrame,
    target: str,
    alpha: int = 180,
) -> tuple[str, str, str]:
    """
    Constrói três GeoJSONs (observado, predito, resíduos) a partir de:

    Parameters
    ----------
    df_mun : DataFrame com colunas [codigo, populacao, geometry, ...]
    df_predicoes : DataFrame com index=codigo e colunas [observado, predito]
    target : nome do target (usado como prefixo nas colunas do GeoJSON)
    alpha : opacidade RGBA (0–255)

    Returns
    -------
    (geojson_obs, geojson_pred, geojson_resid) — strings JSON
    """
    # ── Merge ────
    df_plot = df_mun.merge(
        df_predicoes.rename(columns={
            "observado": f"{target}_observado",
            "predito":   f"{target}_predito",
        }),
        left_on="codigo",
        right_index=True,
        how="left",
    )
    df_plot[f"{target}_observado"] = df_plot[f"{target}_observado"].fillna(0.0)
    df_plot[f"{target}_predito"]   = df_plot[f"{target}_predito"].fillna(0.0)
    df_plot[f"{target}_residuo"]   = (
        df_plot[f"{target}_observado"] - df_plot[f"{target}_predito"]
    )

    # ── Incidência por 100 mil hab ────
    pop = df_plot["populacao"].astype(float)

    col_obs  = f"{target}_observado"
    col_pred = f"{target}_predito"
    col_res  = f"{target}_residuo"

    col_inc_obs  = f"{target}_inc_obs"
    col_inc_pred = f"{target}_inc_pred"
    col_inc_res  = f"{target}_inc_res"

    df_plot[col_inc_obs]  = _incidence(df_plot[col_obs],  pop)
    df_plot[col_inc_pred] = _incidence(df_plot[col_pred], pop)
    # resíduo em incidência: diferença das incidências (mesma escala)
    df_plot[col_inc_res]  = df_plot[col_inc_obs] - df_plot[col_inc_pred]

    # ── Escala compartilhada observado/predito (incidência) ────
    vmin = min(df_plot[col_inc_obs].min(), df_plot[col_inc_pred].min())
    vmax = max(df_plot[col_inc_obs].max(), df_plot[col_inc_pred].max())

    # ── Escala divergente para resíduos (incidência) ────
    max_abs_res = max(
        abs(df_plot[col_inc_res].max()),
        abs(df_plot[col_inc_res].min()),
        1e-9,
    )

    # ── Aplicar cores ────
    gdf_obs  = _to_gdf(df_plot.copy())
    gdf_pred = _to_gdf(df_plot.copy())
    gdf_res  = _to_gdf(df_plot.copy())

    gdf_obs["fill_color"]  = gdf_obs[col_inc_obs].apply(
        lambda x: _color_incidence(x, vmin, vmax, alpha)
    )
    gdf_pred["fill_color"] = gdf_pred[col_inc_pred].apply(
        lambda x: _color_incidence(x, vmin, vmax, alpha)
    )
    gdf_res["fill_color"]  = gdf_res[col_inc_res].apply(
        lambda x: _color_diverging(x, max_abs_res, alpha)
    )

    return geojsons_to_str(
        _to_geojson_dict(gdf_obs),
        _to_geojson_dict(gdf_pred),
        _to_geojson_dict(gdf_res),
    )

def build_geojson_forecast(
    df_mun: pd.DataFrame,
    df_forecast: pd.DataFrame,
    target: str,
    alpha: int = 180,
) -> str:
    """
    Constrói um único GeoJSON de previsão (sem observado, sem resíduo),
    colorido por incidência (casos por 100 mil hab).

    Parameters
    ----------
    df_mun      : DataFrame com colunas [codigo, populacao, geometry, ...]
    df_forecast : DataFrame com index=id_municipio e coluna [predito]
    target      : nome do target (prefixo das colunas no GeoJSON)
    alpha       : opacidade RGBA (0–255)

    Returns
    -------
    str — GeoJSON serializado
    """
    col_pred     = f"{target}_predito"
    col_inc_pred = f"{target}_inc_pred"

    # ── Merge com malha municipal ─────────────────────────────────────────────
    df_plot = df_mun.merge(
        df_forecast[["predito"]].rename(columns={"predito": col_pred}),
        left_on="codigo",
        right_index=True,
        how="left",
    )
    df_plot[col_pred] = df_plot[col_pred].fillna(0.0)

    # ── Incidência por 100 mil hab ────────────────────────────────────────────
    pop = df_plot["populacao"].astype(float).replace(0, np.nan)
    df_plot[col_inc_pred] = (df_plot[col_pred] / pop * 100_000).fillna(0.0)

    # ── Escala de cor (sequencial, igual ao observado/predito do build_geojsons) ──
    vmin = df_plot[col_inc_pred].min()
    vmax = df_plot[col_inc_pred].max()

    gdf = _to_gdf(df_plot.copy())
    gdf["fill_color"] = gdf[col_inc_pred].apply(
        lambda x: _color_incidence(x, vmin, vmax, alpha)
    )

    geojson = _to_geojson_dict(gdf)
    return json.dumps(geojson, ensure_ascii=False)

def geojsons_to_str(
    geojson_obs: dict,
    geojson_pred: dict,
    geojson_resid: dict,
) -> tuple[str, str, str]:
    """Serializa os três GeoJSONs para string."""
    return (
        json.dumps(geojson_obs,   ensure_ascii=False),
        json.dumps(geojson_pred,  ensure_ascii=False),
        json.dumps(geojson_resid, ensure_ascii=False),
    )