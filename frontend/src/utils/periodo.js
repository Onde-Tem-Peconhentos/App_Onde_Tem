// src/utils/periodo.js

const MESES_ABREV = [
  "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
  "Jul", "Ago", "Set", "Out", "Nov", "Dez"
];

/**
 * Formata um identificador de período de acordo com a cadência
 * (tipo_periodo): "Mês" → AAAAMM, "Trimestre" → AAAAT, "Semestre" → AAAAS,
 * "Ano" → AAAA — mesmos formatos usados por ajuste_modelos_unificado.py no
 * backend.
 */
export function formatPeriodo(valor, tipoPeriodo) {
  if (valor === null || valor === undefined || valor === "") return "—";

  const str = String(valor);

  switch (tipoPeriodo) {
    case "Mês": {
      const ano = str.slice(0, 4);
      const mes = Number(str.slice(4, 6));
      return `${MESES_ABREV[mes - 1] ?? mes}/${ano}`;
    }
    case "Trimestre": {
      const ano = str.slice(0, 4);
      const trimestre = str.slice(4);
      return `${trimestre}º Trim/${ano}`;
    }
    case "Semestre": {
      const ano = str.slice(0, 4);
      const semestre = str.slice(4);
      return `${semestre}º Sem/${ano}`;
    }
    case "Ano":
    default:
      return str;
  }
}
