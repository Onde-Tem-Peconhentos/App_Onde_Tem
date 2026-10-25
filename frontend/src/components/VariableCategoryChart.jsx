// src/components/VariableCategoryChart.jsx
import React, { useMemo } from "react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { classifyVariable, getCovariavel, CATEGORIAS } from "../data/variaveis";
import styles from "../pages/styles/Modelos.module.css";

/**
 * Mostra a composição (por categoria) das variáveis que o modelo
 * efetivamente selecionou. Como a API não expõe a magnitude/coeficiente de
 * cada variável (só a lista de nomes selecionados), o gráfico reflete a
 * CONTAGEM de variáveis por categoria — uma proxy honesta de "em que tipo de
 * informação o modelo se apoiou mais", não uma decomposição de variância
 * explicada.
 */
function CategoryTooltip({ active, payload, total }) {
  if (!active || !payload?.length) return null;
  const { name, value, nomes, color } = payload[0].payload;
  return (
    <div className={styles.categoryChartTooltip}>
      <div className={styles.categoryChartTooltipHeader} style={{ color }}>
        {name} — {value} de {total}
      </div>
      <div className={styles.categoryChartTooltipList}>{nomes.join(", ")}</div>
    </div>
  );
}

export default function VariableCategoryChart({ metrics }) {
  const variaveis = metrics?.meta?.selected_features || [];

  const data = useMemo(() => {
    const porCategoria = {};
    for (const nomeBruto of variaveis) {
      const categoria = classifyVariable(nomeBruto);
      const variavel = getCovariavel(nomeBruto);
      (porCategoria[categoria] ||= []).push(variavel?.sigla || nomeBruto);
    }
    return Object.entries(porCategoria)
      .map(([categoria, nomes]) => ({
        categoria,
        name: CATEGORIAS[categoria].label,
        value: nomes.length,
        nomes,
        color: CATEGORIAS[categoria].color,
      }))
      .sort((a, b) => b.value - a.value);
  }, [variaveis]);

  if (!variaveis.length) return null;

  const total = variaveis.length;

  return (
    <div>
      <h4 className={styles.categoryChartTitle}>Composição das variáveis selecionadas</h4>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={62}
            outerRadius={95}
            paddingAngle={3}
            dataKey="value"
            nameKey="name"
          >
            {data.map((entry) => (
              <Cell key={entry.categoria} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CategoryTooltip total={total} />} />
          <Legend verticalAlign="bottom" iconType="circle" />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
