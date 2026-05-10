import React from "react";
import styles from "./styles/ModelMetrics.module.css";

export default function ModelMetrics({ target }) {
  if (!target) return null;

  const metricsMap = {
    smr: {
      AICc_train: 4489.6056,
      R2_train: 0.2136,
      MSE_test: 59.3739,
      Moran_I: 0.1639,
      Moran_p: 0.0010,
    },
    total_ocorrencias: {
      AICc_train: 5259.9593,
      R2_train: 0.3238       ,
      MSE_test: 166.3318,
      Moran_I: 0.0638,
      Moran_p: 0.0020,
    },
    incidencia: {
      AICc_train: 6386.2529,
      R2_train: 0.2135,
      MSE_test: 1123.8554,
      Moran_I: 0.1639,
      Moran_p: 0.0010,
    },
  };

  const m = metricsMap[target];
  if (!m) return null;

  return (
    <div className={styles.metricsContainer}>
      <h3 className={styles.title}>Métricas do Modelo</h3>
        <p>
            Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
        </p>

      <div className={styles.grid}>
        <div className={styles.card}>
          <span>AICc (treino)</span>
          <strong>{m.AICc_train.toFixed(2)}</strong>
        </div>

        <div className={styles.card}>
          <span>R² (treino)</span>
          <strong>{m.R2_train.toFixed(4)}</strong>
        </div>

        <div className={styles.card}>
          <span>MSE (teste)</span>
          <strong>{m.MSE_test.toFixed(2)}</strong>
        </div>

        <div className={styles.card}>
          <span>Moran's I</span>
          <strong>{m.Moran_I.toFixed(4)}</strong>
        </div>

        <div className={styles.card}>
          <span>p-valor (Moran)</span>
          <strong>{m.Moran_p.toFixed(4)}</strong>
        </div>
      </div>
    </div>
  );
}