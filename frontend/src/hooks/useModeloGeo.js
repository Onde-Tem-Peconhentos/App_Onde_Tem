// src/hooks/useModeloGeo.js
import { useState, useEffect } from "react";

export function useModeloGeo({ animal, metodo, periodo }) {
  const [data, setData] = useState({ observado: null, predito: null, metrics: null });
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
            metrics: {
              mse: json.metrics.mse,
              rmse: json.metrics.rmse,
              mae: json.metrics.mae,
              r2: json.metrics.r2,
              gain_vs_media_municipal: json.metrics.gain_vs_media_municipal,
              meta: json.meta
          }});
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [animal, metodo, periodo]);

  return { ...data, loading, error };
}