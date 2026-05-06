// src/components/ModelDetails.jsx
import React, { Suspense, lazy } from "react";
import { BlockMath } from "react-katex";
import VariablesList from "./VariablesList";
import ModelMetrics from "./ModelMetrics";
import styles from "../pages/styles/Modelos.module.css";
import { useModeloGeo } from "../hooks/useModeloGeo";

const GeoPlot = lazy(() => import("./GeoPlot.jsx"));

function ModelDetails({ model, filters }) {
  if (!model) return null;

  // Só faz a consulta se todos os filtros estiverem selecionados
  const filtersReady = !!(filters.animal && filters.modelo && filters.tempo);

  const { observado, predito, loading, error } = useModeloGeo({
    animal:  filtersReady ? filters.animal  : null,
    metodo:  filtersReady ? filters.modelo  : null,
    periodo: filtersReady ? filters.tempo   : null,
  });

  // Enquanto algum filtro não estiver selecionado, não exibe nada
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

        <h2 className={styles.modelTitle}>{model.titulo}</h2>
        
{/* CONTAINER RELATIVO */}
<div style={{ position: 'relative', width: '100%' }}>

  {/* HEADER SOBRE OS DOIS MAPAS */}
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
        
        
        {/* NOVO: Container Grid para os dois mapas lado a lado */}
        <div className={styles.mapsGrid}>
          {/* Mapa 1 */}
          <div className={styles.mapWrapper}>
            <Suspense fallback={<div className={styles.mapPlaceholder}>Carregando mapa 1...</div>}>
              <GeoPlot
                data={observado}
                target={filters.animal ? filters.animal.toUpperCase() : "observado"}
                tempo={filters.tempo} 
              />
            </Suspense>
          </div>

          {/* Mapa 2 (Cópia exata por enquanto) */}
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
        </div>

        <div> 
          <ModelMetrics target= "total_ocorrencias" />
        </div>

        <div className={styles.formulaWrapper}>
          <div className={styles.formulaLabel}>Especificação do modelo</div>
          <div className={styles.formulaCard}>
            <BlockMath math={model.formula} />
          </div>
        </div>

        <div className={styles.descriptionSection}>
          <h3 className={styles.sectionTitle}>Variáveis</h3>
          <VariablesList variaveisSelecionadas={model.variaveis} />
        </div>
      </div>
    </section>
  );
}

export default React.memo(ModelDetails);