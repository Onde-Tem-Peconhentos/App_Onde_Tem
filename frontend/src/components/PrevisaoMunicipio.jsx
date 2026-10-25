// src/components/PrevisaoMunicipio.jsx
import React, { Suspense, lazy, useEffect, useMemo, useState } from "react";
import styles from "../pages/styles/Modelos.module.css";

const GeoPlot = lazy(() => import("./GeoPlot.jsx"));

function fmtInt(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Math.round(Number(v)).toLocaleString("pt-BR");
}

function fmtInc(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtVariacao(pct) {
  if (pct === null || pct === undefined || Number.isNaN(Number(pct))) return "—";
  const sinal = pct > 0 ? "+" : "";
  return `${sinal}${Number(pct).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

/** Incidência anterior é derivada de `casos_periodo_anterior` (contagem
 * bruta) + população, já que o backend só persiste a contagem — e a
 * variação (%) entre essa incidência anterior e a prevista. Sem base de
 * comparação (período anterior = 0 casos mas previsão > 0) a variação
 * percentual não é definida, então retorna null em vez de "+Infinity%". */
function calcVariacaoIncidencia(incPred, casosAnterior, populacao) {
  if (casosAnterior === null || casosAnterior === undefined || !populacao) {
    return { incAnterior: null, pct: null };
  }
  const incAnterior = (Number(casosAnterior) / Number(populacao)) * 100_000;
  if (incAnterior === 0) {
    return { incAnterior, pct: incPred === 0 ? 0 : null };
  }
  return { incAnterior, pct: ((incPred - incAnterior) / incAnterior) * 100 };
}

function SetaVariacao({ pct }) {
  if (pct === null || pct === undefined) {
    return <span className={`${styles.signArrow} ${styles.signArrowMixed}`} title="Sem casos no período anterior para comparar">—</span>;
  }
  if (pct > 0) return <span className={`${styles.signArrow} ${styles.signArrowUp}`}>▲</span>;
  if (pct < 0) return <span className={`${styles.signArrow} ${styles.signArrowDown}`}>▼</span>;
  return <span className={`${styles.signArrow} ${styles.signArrowMixed}`}>▬</span>;
}

/**
 * Seção "Previsão (fora da amostra)": busca de município por nome, big
 * numbers (população, previsão de casos, incidência prevista, ranking por
 * incidência entre todos os municípios) e o mapa de previsão — tudo a
 * partir do GeoJSON de forecast (geojson_forecast), que antes era buscado
 * pela API mas nunca usado no frontend.
 */
export default function PrevisaoMunicipio({ data, forecastPeriodo }) {
  const [busca, setBusca] = useState("");
  const [listaAberta, setListaAberta] = useState(false);
  const [selecionadoCodigo, setSelecionadoCodigo] = useState(null);

  // Municípios ordenados por incidência prevista (desc) — dá o ranking e a
  // lista de busca de uma vez só.
  const ranking = useMemo(() => {
    if (!data?.features) return [];
    return [...data.features]
      .map((f) => f.properties)
      .filter((p) => p && p.municipio)
      .sort((a, b) => (b.casos_inc_pred ?? -Infinity) - (a.casos_inc_pred ?? -Infinity));
  }, [data]);

  // Seleciona automaticamente o município de maior incidência prevista
  // assim que os dados chegam (e ainda não há seleção).
  useEffect(() => {
    if (ranking.length > 0 && selecionadoCodigo === null) {
      setSelecionadoCodigo(ranking[0].codigo);
    }
  }, [ranking, selecionadoCodigo]);

  const resultadosBusca = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) return ranking.slice(0, 8);
    return ranking.filter((p) => p.municipio.toLowerCase().includes(termo)).slice(0, 8);
  }, [busca, ranking]);

  const selecionadoIndex = ranking.findIndex((p) => p.codigo === selecionadoCodigo);
  const selecionado = selecionadoIndex >= 0 ? ranking[selecionadoIndex] : null;
  const rank = selecionadoIndex >= 0 ? selecionadoIndex + 1 : null;

  const variacao = selecionado
    ? calcVariacaoIncidencia(selecionado.casos_inc_pred, selecionado.casos_periodo_anterior, selecionado.populacao)
    : { incAnterior: null, pct: null };

  const escolher = (p) => {
    setSelecionadoCodigo(p.codigo);
    setBusca("");
    setListaAberta(false);
  };

  if (!data) {
    return (
      <section className={styles.previsaoSection}>
        <h2 className={styles.modelTitle} style={{ marginBottom: 6 }}>Previsão (fora da amostra)</h2>
        <p className={styles.mapCaption}>Carregando previsão...</p>
      </section>
    );
  }

  return (
    <section className={styles.previsaoSection}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 8 }}>
        <h2 className={styles.modelTitle} style={{ marginBottom: 6 }}>Previsão (fora da amostra)</h2>
        <span className={styles.periodoInfoLabel} style={{ color: "#3b82f6" }}>
          Período: <strong style={{ color: "#1d4ed8" }}>{forecastPeriodo}</strong>
        </span>
      </div>
      <p className={styles.mapCaption}>
        Previsão para um período à frente do último dado observado — fora da
        amostra de teste, nunca comparado a um valor real. Busque um
        município para ver os números.
      </p>

      <div className={styles.buscaMunicipioWrapper}>
        <input
          type="text"
          className={styles.buscaMunicipioInput}
          placeholder="Buscar município pelo nome..."
          value={busca}
          onChange={(e) => { setBusca(e.target.value); setListaAberta(true); }}
          onFocus={() => setListaAberta(true)}
          onBlur={() => setTimeout(() => setListaAberta(false), 120)}
        />
        {listaAberta && resultadosBusca.length > 0 && (
          <ul className={styles.buscaMunicipioLista}>
            {resultadosBusca.map((p) => (
              <li
                key={p.codigo}
                className={styles.buscaMunicipioItem}
                onMouseDown={() => escolher(p)}
              >
                {p.municipio}
              </li>
            ))}
          </ul>
        )}
      </div>

      {selecionado && (
        <div className={styles.bigNumbersGrid}>
          <div className={styles.bigNumberCard}>
            <span className={styles.bigNumberLabel}>Município</span>
            <strong className={styles.bigNumberValueText}>{selecionado.municipio}</strong>
          </div>
          <div className={styles.bigNumberCard}>
            <span className={styles.bigNumberLabel}>População</span>
            <strong className={styles.bigNumberValue}>{fmtInt(selecionado.populacao)}</strong>
          </div>
          <div className={styles.bigNumberCard}>
            <span className={styles.bigNumberLabel}>Previsão (casos)</span>
            <strong className={styles.bigNumberValue}>{fmtInt(selecionado.casos_predito)}</strong>
          </div>
          <div
            className={styles.bigNumberCard}
            title={`Período anterior: ${fmtInc(variacao.incAnterior)} /100k hab.`}
          >
            <span className={styles.bigNumberLabel}>Incidência (/100k hab.)</span>
            <strong className={styles.bigNumberValue}>{fmtInc(selecionado.casos_inc_pred)}</strong>
          </div>
          <div
            className={styles.bigNumberCard}
            title={
              variacao.pct === null
                ? "Sem casos no período anterior para comparar"
                : `${fmtInc(variacao.incAnterior)} → ${fmtInc(selecionado.casos_inc_pred)} (/100k hab.)`
            }
          >
            <span className={styles.bigNumberLabel}>Variação da incidência</span>
            <strong className={styles.bigNumberValue}>
              <SetaVariacao pct={variacao.pct} /> {fmtVariacao(variacao.pct)}
            </strong>
          </div>
          <div className={`${styles.bigNumberCard} ${styles.bigNumberCardHighlight}`}>
            <span className={styles.bigNumberLabel}>Rank por incidência</span>
            <strong className={styles.bigNumberValue}>{rank}º <span className={styles.bigNumberValueSub}>de {ranking.length}</span></strong>
          </div>
        </div>
      )}

      <div className={styles.residuoMapWrapper} style={{ marginTop: 20 }}>
        <Suspense fallback={<div className={styles.mapPlaceholder}>Carregando mapa de previsão...</div>}>
          <GeoPlot data={data} target="previsao" title="Previsão" height="480px" />
        </Suspense>
      </div>
    </section>
  );
}
