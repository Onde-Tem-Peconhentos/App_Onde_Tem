// src/hooks/useModeloGeo.js
import { useState, useEffect } from "react";
import { buildRazaoGeoJson } from "../utils/razaoGeo";

export function useModeloGeo({ animal, metodo, periodo }) {
  const [data, setData] = useState({ observado: null, predito: null, razao: null, previsao: null, metrics: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!animal || !metodo || !periodo) return;

    setLoading(true);
    setError(null);

    const normalizedMetodo = metodo.toUpperCase();

    fetch(`http://localhost:8000/api/modelo?animal=${encodeURIComponent(animal)}&metodo=${encodeURIComponent(normalizedMetodo)}&tipo_periodo=${encodeURIComponent(periodo)}`)
      .then(r => {
        if (!r.ok) {
          if (r.status === 404) throw new Error("Modelo não encontrado");
          throw new Error(`Erro HTTP ${r.status}`);
        }
        return r.json();
      })
      .then(json => {
        setData({
          observado: json.geojson_observado,
          predito:   json.geojson_predito,
          residuo:   json.geojson_residuo,
          razao:     buildRazaoGeoJson(json.geojson_observado, json.geojson_predito),
          previsao:  json.geojson_forecast,
          metrics: {
            forecast_month: json.forecast_month,
            data_processamento: json.data_processamento,

            mse: json.metrics.mse,
            rmse: json.metrics.rmse,
            mae: json.metrics.mae,
            r2: json.metrics.r2,
            gain_vs_media_municipal: json.metrics.gain_vs_media_municipal,

            moran_i_medio: json.metrics.moran_i_medio,
            moran_p_sim_medio: json.metrics.moran_p_sim_medio,
            moran_meses_signif: json.metrics.moran_meses_signif,

            hyperparams: json.hyperparams,
            meta: json.meta,

            // Peso das variáveis (valor único no OLS, quartis nos modelos
            // locais) e estabilidade (freq. de seleção nas janelas rolling)
            // — null em linhas gravadas antes dessas colunas existirem.
            pesos_variaveis: json.pesos_variaveis,
            estabilidade_variaveis: json.estabilidade_variaveis,
          }
        });

        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [animal, metodo, periodo]);

  return { ...data, loading, error };
}