import React, { Suspense, lazy } from "react";
import { BlockMath } from "react-katex";
import VariablesList from "./VariablesList";
import VariableCategoryChart from "./VariableCategoryChart";
import ModelMetrics from "./ModelMetrics";
import ModelComparisonTable from "./ModelComparisonTable";
import PrevisaoMunicipio from "./PrevisaoMunicipio";
import styles from "../pages/styles/Modelos.module.css";
import { useModeloGeo } from "../hooks/useModeloGeo";
import { COVARIAVEIS } from "../data/variaveis";
import { formatPeriodo } from "../utils/periodo";


const GeoPlot = lazy(() => import("./GeoPlot.jsx"));

function buildFormula(metodo, selectedFeatures = []) {
  // GWR-Adaptativo tem a mesma forma da GWR (só muda como o bandwidth é
  // escolhido — km fixo vs. k vizinhos), então usa a mesma notação.
  const isGWR = ["gwr", "gwr_adaptativo"].includes(metodo?.toLowerCase());
  const isGTWR = metodo?.toLowerCase() === "gtwr";

  if (!selectedFeatures.length) {
    if (isGWR) {
      return "\\hat{y}_i = \\beta_0(u_i,v_i) + \\sum_k \\beta_k(u_i,v_i)\\,X_{ik}";
    }

    if (isGTWR) {
      return "\\hat{y}_i = \\beta_0(u_i,v_i,t_i) + \\sum_k \\beta_k(u_i,v_i,t_i)\\,X_{ik}";
    }

    return "\\hat{y} = \\beta_0 + \\sum_k \\beta_k X_k";
  }

  const terms = selectedFeatures
    .map((sigla, i) => {
      const label = COVARIAVEIS[sigla]?.sigla || sigla;

      if (isGWR) {
        return `\\beta_{${i + 1}}(u_i,v_i)\\,\\cdot\\,\\text{${label.replace(/_/g, "\\_")}}`;
      }

      if (isGTWR) {
        return `\\beta_{${i + 1}}(u_i,v_i,t_i)\\,\\cdot\\,\\text{${label.replace(/_/g, "\\_")}}`;
      }

      return `\\beta_{${i + 1}}\\,\\cdot\\,\\text{${label.replace(/_/g, "\\_")}}`;
    })
    .join(" + ");

  if (isGWR) {
    return `\\hat{y}_i = \\beta_0(u_i,v_i) + ${terms}`;
  }

  if (isGTWR) {
    return `\\hat{y}_i = \\beta_0(u_i,v_i,t_i) + ${terms}`;
  }

  return `\\hat{y} = \\beta_0 + ${terms}`;
}

function ModelDetails({ model, filters }) {
  if (!model) return null;

  const filtersReady = !!(filters.animal && filters.modelo && filters.tempo);

  const { razao, previsao, metrics, loading, error } = useModeloGeo({
    animal:  filtersReady ? filters.animal  : null,
    metodo:  filtersReady ? filters.modelo  : null,
    periodo: filtersReady ? filters.tempo   : null,
  });

  if (!filtersReady) return null;
  if (loading) return <div>Carregando dados do modelo...</div>;
  if (error)   return <div>Erro: {error}</div>;

  return (
    <section className={styles.modelSection}>
      <div className={styles.modelContent}>
        <h2 className={styles.modelTitle}>{model.titulo}</h2>

        <div className={styles.introBlock}>
          <div className={styles.introText}>
            <p className={styles.paragraph}>{model.descricaoParagrafos[0]}</p>
          </div>
          <aside className={styles.basicFormulaCard}>
            <div className={styles.basicFormulaLabel}>Formulação do método</div>
            <BlockMath math={model.formulaBasica} />
          </aside>
        </div>

        {model.descricaoParagrafos.slice(1).map((paragrafo, idx) => (
          <p key={idx} className={styles.paragraph}>{paragrafo}</p>
        ))}
        <br />

        <PrevisaoMunicipio
          data={previsao}
          forecastPeriodo={formatPeriodo(metrics?.forecast_month, filters.tempo)}
        />

        <h2 className={styles.modelTitle} style={{ marginTop: 36, marginBottom: 16 }}>
          Backtest
        </h2>

        <div className={styles.periodoInfoBar}>
          <div className={styles.periodoInfoItem}>
            <span className={styles.periodoInfoLabel}>Treino</span>
            <strong>
              {formatPeriodo(metrics?.meta?.train_period_inicio, filters.tempo)}
              {" – "}
              {formatPeriodo(metrics?.meta?.train_period_fim, filters.tempo)}
            </strong>
            <span className={styles.periodoInfoDesc}>
              Período usado pra ajustar o modelo e escolher as variáveis.
            </span>
          </div>

          <div className={styles.periodoInfoItem}>
            <span className={styles.periodoInfoLabel}>Teste</span>
            <strong>
              {formatPeriodo(metrics?.meta?.test_period_inicio, filters.tempo)}
              {" – "}
              {formatPeriodo(metrics?.meta?.test_period_fim, filters.tempo)}
            </strong>
            <span className={styles.periodoInfoDesc}>
              Nunca visto no ajuste — é onde as métricas abaixo são calculadas.
            </span>
          </div>

          <div className={styles.periodoInfoItem}>
            <span className={styles.periodoInfoLabel}>Previsão (fora da amostra)</span>
            <strong>{formatPeriodo(metrics?.forecast_month, filters.tempo)}</strong>
            <span className={styles.periodoInfoDesc}>
              Projeção pro período seguinte ao teste — ainda sem valor real pra comparar.
            </span>
          </div>
        </div>

        <div style={{ position: 'relative', width: '100%' }}>
          {/* Mapa único: razão predito/observado (substitui os antigos mapas
              lado a lado de observado e predito) */}
          <div className={styles.residuoMapSection}>
            <h3 className={styles.residuoMapTitle}>Razão Predito / Observado (teste)</h3>
            <p className={styles.mapCaption}>
              Acima de 1× (vermelho): o modelo superestimou. Abaixo de 1×
              (azul): o modelo subestimou. Cinza: município sem nenhum caso
              observado onde o modelo previu casos (razão não calculável).
            </p>
            <div className={styles.residuoMapWrapper}>
              <Suspense fallback={<div className={styles.mapPlaceholder}>Carregando mapa...</div>}>
                <GeoPlot
                  data={razao}
                  target={filters.animal ? `${filters.animal.toUpperCase()}_RAZAO` : "razao"}
                  height="480px"
                />
              </Suspense>
            </div>
          </div>
        </div>

        <div>
          <ModelMetrics metrics={metrics} />
        </div>

        <div className={styles.formulaWrapper}>
          <div className={styles.formulaLabel}>Especificação do modelo</div>
          <div className={styles.formulaCard}>
            <BlockMath math={buildFormula(filters.modelo, metrics?.meta?.selected_features)} />
          </div>
        </div>

        <div className={styles.descriptionSection}>
          <h3 className={styles.sectionTitle}>Variáveis Selecionadas</h3>
          <p className={styles.mapCaption}>
            Seleção por Lasso + stepwise bidirecional por AIC, repetida em
            janelas móveis dentro do treino; só entram aqui as variáveis mais
            frequentes entre essas janelas. Clique num card pra ver o
            coeficiente e a estabilidade de cada uma.
          </p>
          <VariablesList metrics={metrics} metodo={filters.modelo} />
          <div className={styles.categoryChartBelowList}>
            <VariableCategoryChart metrics={metrics} />
          </div>
        </div>

        <div className={styles.descriptionSection}>
          <ModelComparisonTable
            animal={filters.animal}
            tipoPeriodo={filters.tempo}
            metodoSelecionado={filters.modelo}
          />
        </div>
      </div>
    </section>
  );
}

export default React.memo(ModelDetails);