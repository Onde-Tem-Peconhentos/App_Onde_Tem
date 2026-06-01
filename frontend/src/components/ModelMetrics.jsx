import React from "react";
import styles from "./styles/ModelMetrics.module.css";

function fmtNum(v, digits = 4) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Number(v).toFixed(digits);
}

export default function ModelMetrics({ metrics, hyperparams, meta }) {
  // Aceita tanto:
  //  - metrics = response.metrics  (antigo / simplificado)
  //  - metrics = response (objeto completo retornado pelo endpoint)
  const m = metrics?.metrics ? metrics.metrics : metrics ?? {};

  // Procura chaves novas ou antigas (compatibilidade)
  const r2 = m?.r2 ?? m?.r2_test ?? null;
  const mse = m?.mse ?? m?.mse_test ?? null;
  const rmse = m?.rmse ?? m?.rmse_test ?? null;
  const mae = m?.mae ?? null;
  const mse_gain = m?.gain_vs_media_municipal ?? m?.mse_gain ?? null;

  // Hiperparâmetros e meta (podem vir separados ou dentro do response)
  const hp = hyperparams ?? (metrics?.hyperparams ? metrics.hyperparams : metrics?.hyperparams) ?? {};
  const metaObj = meta ?? metrics?.meta ?? {};

  const lassoAlpha = hp?.lasso_alpha ?? null;
  const gwrBw = hp?.gwr_bandwidth_km ?? null;
  const nFeatures = metaObj?.selected_features ? metaObj.selected_features.length : (metaObj?.n_features ?? null);
  const processedAt = metrics?.data_processamento ?? metrics?.data_processamento ?? null;

  if (!m || Object.keys(m).length === 0) return <p>Sem métricas disponíveis.</p>;

  return (
    <div className={styles.metricsContainer}>
      <h3 className={styles.title}>Métricas do Modelo</h3>
      <p className={styles.description}>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
      </p>

      <div className={styles.grid}>
        <div className={styles.card}>
          <span>R² (Teste)</span>
          <strong>{r2 !== null ? fmtNum(r2, 4) : "—"}</strong>
        </div>

        <div className={styles.card}>
          <span>MSE (Teste)</span>
          <strong>{mse !== null ? fmtNum(mse, 4) : "—"}</strong>
        </div>

        <div className={styles.card}>
          <span>RMSE</span>
          <strong>{rmse !== null ? fmtNum(rmse, 4) : "—"}</strong>
        </div>

        <div className={styles.card}>
          <span>MAE</span>
          <strong>{mae !== null ? fmtNum(mae, 4) : "—"}</strong>
        </div>

        <div className={styles.card}>
          <span>MSE Gain</span>
          <strong>{mse_gain !== null ? fmtNum(mse_gain, 4) : "—"}</strong>
        </div>

        {/* <div className={styles.card}>
          <span>Nº variáveis selecionadas</span>
          <strong>{nFeatures !== null ? nFeatures : "—"}</strong>
        </div> */}

        <div className={styles.card}>
          <span>GWR bandwidth (km)</span>
          <strong>{gwrBw !== null ? fmtNum(gwrBw, 4) : "—"}</strong>
        </div>

        {/* <div className={styles.card}>
          <span>Processado em</span>
          <strong>{processedAt ? new Date(processedAt).toLocaleString() : "—"}</strong>
        </div> */}
      </div>
    </div>
  );
}