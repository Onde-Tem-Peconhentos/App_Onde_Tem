// src/components/VariablesList.jsx

import React from "react";
import { COVARIAVEIS } from "../data/variaveis";
import styles from "../pages/styles/Modelos.module.css";

export default function VariablesList({ metrics }) {
  // Pegue selected_features dentro de metrics.meta
  const variaveis = metrics?.meta?.selected_features || [];

  if (!variaveis || variaveis.length === 0) {
    return <p>Nenhuma variável selecionada para este modelo.</p>;
  }

  return (
    <div className={styles.variableList}>
      {variaveis.map((sigla) => {
        const variavel = COVARIAVEIS[sigla];

        if (!variavel) return null;

        return (
          <div key={variavel.sigla} className={styles.variableItem}>
            <span className={styles.variableCode}>{variavel.sigla}</span>
            <span className={styles.variableText}>
              É a{" "}
              {variavel.descricao}
            </span>
          </div>
        );
      })}
    </div>
  );
}