// src/components/VariablesList.jsx
import React from "react";
import { TODAS_COVARIAVEIS } from "../data/constants";
import styles from "../pages/styles/Modelos.module.css";

export default function VariablesList({ variaveisSelecionadas }) {
  if (!variaveisSelecionadas || variaveisSelecionadas.length === 0) return null;

  return (
    <div className={styles.variableList}>
      {variaveisSelecionadas.map((sigla) => {
        const variavel = TODAS_COVARIAVEIS[sigla];
        
        // Se a sigla não existir no dicionário central, ignora
        if (!variavel) return null;

        return (
          <div key={variavel.sigla} className={styles.variableItem}>
            <span className={styles.variableCode}>{variavel.sigla}</span>
            <span className={styles.variableText}>
              é a variável <strong>{variavel.nome}</strong>, que representa a{" "}
              {variavel.descricao}
            </span>
          </div>
        );
      })}
    </div>
  );
}