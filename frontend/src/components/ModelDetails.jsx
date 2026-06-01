import React, { Suspense, lazy } from "react";
import { BlockMath } from "react-katex";
import VariablesList from "./VariablesList";
import ModelMetrics from "./ModelMetrics";
import styles from "../pages/styles/Modelos.module.css";
import { useModeloGeo } from "../hooks/useModeloGeo";
import { COVARIAVEIS } from "../data/variaveis";


const GeoPlot = lazy(() => import("./GeoPlot.jsx"));

function buildFormula(metodo, selectedFeatures = []) {
  if (!selectedFeatures.length) return metodo === "gwr"
    ? "\\hat{y}_i = \\beta_0(u_i,v_i) + \\sum_k \\beta_k(u_i,v_i)\\, X_{ik}"
    : "\\hat{y} = \\beta_0 + \\sum_k \\beta_k X_k";

  const terms = selectedFeatures
    .map((sigla, i) => {
      const label = COVARIAVEIS[sigla]?.sigla || sigla;
      return `\\beta_{${i + 1}} \\cdot \\text{${label.replace(/_/g, "\\_")}}`;
    })
    .join(" + ");

  return metodo === "gwr"
    ? `\\hat{y}_i = \\beta_0(u_i,v_i) + ${terms}`
    : `\\hat{y} = \\beta_0 + ${terms}`;
}

function ModelDetails({ model, filters }) {
  if (!model) return null;

  const filtersReady = !!(filters.animal && filters.modelo && filters.tempo);

  const { observado, predito, residuo, metrics, loading, error } = useModeloGeo({
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

        <h2 className={styles.modelTitle}>Backtest</h2>
        
        <div style={{ position: 'relative', width: '100%' }}>
          <div
            style={{
              position: 'absolute',
              top: 10,
              left: 0,
              width: '100%',
              display: 'flex',
              justifyContent: 'space-between',
              padding: '0 20px',
              zIndex: 10,
              pointerEvents: 'none',
              fontFamily: 'sans-serif',
              fontWeight: 'bold',
              color: '#000'
            }}
          >
            <div>OBSERVADO</div>
            <div>PREDITO</div>
          </div>
                
          <div className={styles.mapsGrid}>
            <div className={styles.mapWrapper}>
              <Suspense fallback={<div className={styles.mapPlaceholder}>Carregando mapa 1...</div>}>
                <GeoPlot
                  data={observado}
                  target={filters.animal ? filters.animal.toUpperCase() : "observado"}
                  tempo={filters.tempo} 
                />
              </Suspense>
            </div>

            <div className={styles.mapWrapper}>
              <Suspense fallback={<div className={styles.mapPlaceholder}>Carregando mapa 2...</div>}>
                <GeoPlot
                  data={predito}
                  target={filters.animal ? filters.animal.toUpperCase() : "predito"}
                  tempo={filters.tempo} 
                />
              </Suspense>
            </div>
          </div>

          {/* Mapa de resíduos: abaixo, full-width */}
          <div className={styles.residuoMapSection}>
            <div className={styles.residuoMapWrapper}>
              <Suspense fallback={<div className={styles.mapPlaceholder}>Carregando mapa de resíduos...</div>}>
                <GeoPlot
                  data={residuo}
                  target="residuo"
                  title="Resíduos"
                  height="400px"
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
            <VariablesList metrics={metrics} metodo={filters.modelo} />
        </div>
      </div>
    </section>
  );
}

export default React.memo(ModelDetails);