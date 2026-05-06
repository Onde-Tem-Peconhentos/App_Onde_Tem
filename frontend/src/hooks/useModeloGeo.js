import { useState, useEffect } from "react";

export function useModeloGeo({ animal, metodo, periodo }) {
  const [data, setData] = useState({ observado: null, predito: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!animal || !metodo || !periodo) return;
    setLoading(true);
    setError(null);

    fetch(`http://localhost:8000/api/modelo?animal=${encodeURIComponent(animal)}&metodo=${encodeURIComponent(metodo)}&periodo=${encodeURIComponent(periodo)}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(json => {
        setData({ observado: json.geojson_observado, predito: json.geojson_predito });
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [animal, metodo, periodo]);

  return { ...data, loading, error };
}