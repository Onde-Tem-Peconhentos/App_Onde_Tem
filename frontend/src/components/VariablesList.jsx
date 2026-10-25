// src/components/VariablesList.jsx

import React, { useState } from "react";
import { getCovariavel, classifyVariable, CATEGORIAS } from "../data/variaveis";
import styles from "../pages/styles/Modelos.module.css";

function fmtCoef(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toPrecision(3);
}

/** Bloco de estatística compacto (label + valor), usado tanto com dado real
 * quanto como "mockup" (placeholder em traço) quando ainda não há dado —
 * mantém o card com a mesma forma nos dois casos. */
function StatBlock({ label, children }) {
  return (
    <div className={styles.flipStat}>
      <span className={styles.flipStatLabel}>{label}</span>
      <span className={styles.flipStatValue}>{children}</span>
    </div>
  );
}

/**
 * Sinal da relação entre a variável e o alvo:
 *  - OLS (coeficiente único): sinal direto do coeficiente.
 *  - Modelos locais (GWR/GWR-Adaptativo/GTWR, quartis entre municípios):
 *    "positivo"/"negativo" só quando Q1 e Q3 têm o mesmo sinal (a relação é
 *    consistente entre municípios); quando os quartis têm sinais diferentes,
 *    a direção varia de município pra município — não dá pra resumir num
 *    único sentido, então marca como "misto" em vez de arredondar pra um lado.
 */
function sinalRelacao(pesos, nomeBruto) {
  const valor = pesos?.coeficientes?.[nomeBruto];
  if (valor === undefined || valor === null) return null;

  if (pesos.tipo === "quantis_locais") {
    const sq1 = Math.sign(valor.q1);
    const sq3 = Math.sign(valor.q3);
    if (sq1 === 0 || sq3 === 0 || sq1 !== sq3) return "misto";
    return sq1 > 0 ? "positivo" : "negativo";
  }

  const s = Math.sign(valor);
  if (s === 0) return "misto";
  return s > 0 ? "positivo" : "negativo";
}

function SetaSinal({ sinal }) {
  if (sinal === "positivo") {
    return <span className={`${styles.signArrow} ${styles.signArrowUp}`} title="Relação positiva com a incidência">▲</span>;
  }
  if (sinal === "negativo") {
    return <span className={`${styles.signArrow} ${styles.signArrowDown}`} title="Relação negativa com a incidência">▼</span>;
  }
  if (sinal === "misto") {
    return (
      <span className={`${styles.signArrow} ${styles.signArrowMixed}`} title="Direção varia entre municípios (Q1 e Q3 do coeficiente têm sinais diferentes)">
        ↕
      </span>
    );
  }
  return <span className={`${styles.signArrow} ${styles.signArrowMixed}`} title="Sem coeficiente disponível">—</span>;
}

function CoeficienteStats({ nomeBruto, pesos, sinal }) {
  const valor = pesos?.coeficientes?.[nomeBruto];

  if (!pesos || valor === undefined) {
    return <StatBlock label="Coeficiente">—</StatBlock>;
  }

  if (pesos.tipo === "quantis_locais") {
    return (
      <div className={styles.flipCoefGroup}>
        <StatBlock label="Coef. (mediana)">
          <SetaSinal sinal={sinal} /> {fmtCoef(valor.mediana)}
        </StatBlock>
        <StatBlock label="Q1">{fmtCoef(valor.q1)}</StatBlock>
        <StatBlock label="Q3">{fmtCoef(valor.q3)}</StatBlock>
      </div>
    );
  }

  return (
    <StatBlock label="Coeficiente (global)">
      <SetaSinal sinal={sinal} /> {fmtCoef(valor)}
    </StatBlock>
  );
}

function EstabilidadeStats({ nomeBruto, estabilidade }) {
  const dado = estabilidade?.[nomeBruto];

  if (!dado) {
    return <StatBlock label="Estabilidade">—</StatBlock>;
  }

  const { n_janelas_selecionada, n_janelas_total, frequencia } = dado;
  const percent = (frequencia * 100).toFixed(0);

  return (
    <StatBlock label="Estabilidade (% de janelas)">
      {percent}%
      <span className={styles.flipStatSub}> ({n_janelas_selecionada}/{n_janelas_total} janelas)</span>
      {frequencia < 0.5 && <span className={styles.flipCardWarning} title="Menos de 50% — tratar com cautela"> ⚠</span>}
    </StatBlock>
  );
}

export default function VariablesList({ metrics }) {
  const variaveis = metrics?.meta?.selected_features || [];
  const pesos = metrics?.pesos_variaveis;
  const estabilidade = metrics?.estabilidade_variaveis;
  const [viradas, setViradas] = useState(() => new Set());

  if (!variaveis || variaveis.length === 0) {
    return <p>Nenhuma variável selecionada para este modelo.</p>;
  }

  const toggleVirada = (nomeBruto) => {
    setViradas((prev) => {
      const next = new Set(prev);
      if (next.has(nomeBruto)) next.delete(nomeBruto);
      else next.add(nomeBruto);
      return next;
    });
  };

  return (
    <div className={styles.variableList}>
      {variaveis.map((nomeBruto) => {
        const variavel = getCovariavel(nomeBruto);
        const categoria = classifyVariable(nomeBruto);
        const { label: categoriaLabel, color: categoriaCor } = CATEGORIAS[categoria];
        const codigo = variavel?.sigla || nomeBruto;
        const virada = viradas.has(nomeBruto);
        const sinal = sinalRelacao(pesos, nomeBruto);

        return (
          <div
            key={nomeBruto}
            className={styles.flipCardOuter}
            onClick={() => toggleVirada(nomeBruto)}
            role="button"
            tabIndex={0}
            title="Clique para ver coeficiente e estabilidade"
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                toggleVirada(nomeBruto);
              }
            }}
          >
            <div className={`${styles.flipCardInner} ${virada ? styles.flipCardFlipped : ""}`}>
              <div className={`${styles.flipCardFace} ${styles.variableItem}`}>
                <span className={styles.variableCode}>{codigo}</span>
                <SetaSinal sinal={sinal} />
                <span
                  className={styles.categoryTag}
                  style={{ backgroundColor: `${categoriaCor}1a`, color: categoriaCor }}
                  title="Categoria da variável"
                >
                  {categoriaLabel}
                </span>
                <span className={styles.variableText}>
                  {variavel
                    ? <>É a {variavel.descricao}</>
                    : <>Coluna <code>{nomeBruto}</code> (sem descrição cadastrada ainda).</>}
                </span>
              </div>

              <div className={`${styles.flipCardFace} ${styles.flipCardBack}`}>
                <span className={styles.variableCode}>{codigo}</span>
                <CoeficienteStats nomeBruto={nomeBruto} pesos={pesos} sinal={sinal} />
                <EstabilidadeStats nomeBruto={nomeBruto} estabilidade={estabilidade} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
