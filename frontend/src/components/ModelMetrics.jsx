import React from "react";
import styles from "./styles/ModelMetrics.module.css";

// Formatação segura de números
function fmtNum(v, digits = 4) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(digits);
}

export default function ModelMetrics(props) {
  // Aceita o objeto completo da API passado na prop 'metrics' 
  // ou as propriedades desestruturadas separadamente (retrocompatibilidade)
  const data = props.metrics?.metrics ? props.metrics : props;
  
  const m = data.metrics || {};
  const hp = data.hyperparams || {};
  const metodo = data.metodo || "";

  if (!m || Object.keys(m).length === 0) {
    return <p>Sem métricas disponíveis.</p>;
  }

  // Helper para renderizar os cards condicionalmente
  // Se o valor for null/undefined (ex: bandwidth no OLS), o card nem é gerado.
  const MetricCard = ({ label, value, isInt = false, isPercent = false }) => {
    if (value === null || value === undefined) return null;
    
    let displayValue = "";
    if (isInt) {
      displayValue = Math.round(value).toString();
    } else if (isPercent) {
      displayValue = fmtNum(value * 100, 2) + "%";
    } else {
      displayValue = fmtNum(value, 4);
    }

    return (
      <div className={styles.card}>
        <span>{label}</span>
        <strong>{displayValue}</strong>
      </div>
    );
  };

  // Formata o nome do modelo para o Título
  const formatMethodName = (methodStr) => {
    const names = {
      ols: "OLS Global",
      gwr: "GWR (Gaussiano)",
      gwr_adaptativo: "GWR Adaptativo",
      gtwr: "GTWR (Espaço-Temporal)",
    };
    return names[methodStr?.toLowerCase()] || "Modelo";
  };

  return (
    <div className={styles.metricsContainer}>
      <h3 className={styles.title}>Resultados: {formatMethodName(metodo)}</h3>
      <p className={styles.subtitle}>
        Métricas calculadas sobre o conjunto de teste (nunca de treino).
      </p>

      <div className={styles.grid}>
        {/* 1. Métricas de Desempenho (Sempre aparecem) */}
        <MetricCard label="R² (Teste)" value={m.r2} />
        <MetricCard label="MSE (Teste)" value={m.mse} />
        <MetricCard label="Ganho vs Média Mun. (Teste)" value={m.gain_vs_media_municipal} isPercent={true} />

        {/* 2. Índice de Moran (Se o backend tiver calculado para este modelo) */}
        {/* <MetricCard label="Índice de Moran (Médio)" value={m.moran_i_medio} />
        <MetricCard label="P-valor Moran (Médio)" value={m.moran_p_sim_medio} />
        <MetricCard label="Moran: Meses Signif." value={m.moran_meses_signif} isInt={true} /> */}

        {/* 3. Hiperparâmetros (Renderização Mágica) 
            Só vai aparecer na tela o card que tiver valor !== null no banco */}
        <MetricCard label="Bandwidth Fixo (km)" value={hp.gwr_bandwidth_km} />
        <MetricCard label="Bandwidth Adaptativo (vizinhos)" value={hp.gwr_bandwidth_k} isInt={true} />
        <MetricCard label="Bandwidth Espacial GTWR (vizinhos)" value={hp.gtwr_bandwidth_s} isInt={true} />
        <MetricCard label="Razão Temporal GTWR (Tau)" value={hp.gtwr_tau} />
      </div>
    </div>
  );
}