import React, { useMemo, useState } from "react";
import { BlockMath } from "react-katex";
import "katex/dist/katex.min.css";

import Header from "../components/Header";
import Footer from "../components/Footer";
import UiSelect from "../components/UiSelect";
import styles from "./styles/Modelos.module.css";

const COVARIAVEIS = [
  {
    sigla: "POPFAV",
    nome: "POP_FAVELAS",
    descricao:
      "população residente em áreas classificadas como favelas no município.",
  },
  {
    sigla: "ALT",
    nome: "ALTITUDE",
    descricao: "altitude média do município, em metros.",
  },
  {
    sigla: "VEG",
    nome: "PERCENTUAL_VEGETACAO",
    descricao: "percentual de cobertura vegetal no território municipal.",
  },
  {
    sigla: "AREA",
    nome: "AREA_KM2",
    descricao: "área territorial do município, em quilômetros quadrados.",
  },
  {
    sigla: "PREC",
    nome: "PRECIPITACAO",
    descricao: "precipitação média observada na região.",
  },
];

const MODELOS = [
  {
    value: "gwr",
    label: "Geographically Weighted Regression",
    titulo: "Geographically Weighted Regression",
    descricaoParagrafos: [
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent gravida sit amet diam eget vehicula. Cras gravida ipsum vel tristique bibendum. Donec faucibus accumsan convallis. Suspendisse ullamcorper lacus tortor. Ut eget eros volutpat, auctor sapien in, tincidunt velit. Morbi bibendum metus in nisl molestie commodo. Proin sapien tellus, ullamcorper sit amet nisl vitae, luctus tempor tellus. Sed vel enim mollis dui tristique convallis eu sed ex. Pellentesque quis dapibus sem. Pellentesque eu hendrerit dolor.",
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Morbi bibendum metus in nisl molestie commodo. Proin sapien tellus, ullamcorper sit amet nisl vitae, luctus tempor tellus. Sed vel enim mollis dui tristique convallis eu sed ex. Pellentesque quis dapibus sem. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque eu hendrerit dolor. Integer mattis, ipsum sed posuere pellentesque, justo erat tincidunt nunc, vitae facilisis nibh metus vitae nisi.",
    ],
    formulaBasica: String.raw`y_i = \beta_0(u_i,v_i) + \sum_{k=1}^{p}\beta_k(u_i,v_i)x_{ik} + \varepsilon_i`,
    formula: String.raw`
      y_i =
      \beta_0(u_i,v_i)
      + \beta_1(u_i,v_i)\,POPFAV_i
      + \beta_2(u_i,v_i)\,ALT_i
      + \beta_3(u_i,v_i)\,VEG_i
      + \beta_4(u_i,v_i)\,AREA_i
      + \beta_5(u_i,v_i)\,PREC_i
      + \varepsilon_i
    `,
  },
  {
    value: "gtwr",
    label: "Geographically and Temporally Weighted Regression",
    titulo: "Geographically and Temporally Weighted Regression",
    descricaoParagrafos: [
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent gravida sit amet diam eget vehicula. Cras gravida ipsum vel tristique bibendum. Donec faucibus accumsan convallis. Suspendisse ullamcorper lacus tortor. Ut eget eros volutpat, auctor sapien in, tincidunt velit. Morbi bibendum metus in nisl molestie commodo. Proin sapien tellus, ullamcorper sit amet nisl vitae, luctus tempor tellus. Sed vel enim mollis dui tristique convallis eu sed ex. Pellentesque quis dapibus sem. Pellentesque eu hendrerit dolor.",
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Morbi bibendum metus in nisl molestie commodo. Proin sapien tellus, ullamcorper sit amet nisl vitae, luctus tempor tellus. Sed vel enim mollis dui tristique convallis eu sed ex. Pellentesque quis dapibus sem. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque eu hendrerit dolor. Integer mattis, ipsum sed posuere pellentesque, justo erat tincidunt nunc, vitae facilisis nibh metus vitae nisi.",
    ],
    formulaBasica: String.raw`y_i = \beta_0(u_i,v_i,t_i) + \sum_{k=1}^{p}\beta_k(u_i,v_i,t_i)x_{ik} + \varepsilon_i`,
    formula: String.raw`
      y_i =
      \beta_0(u_i,v_i,t_i)
      + \beta_1(u_i,v_i,t_i)\,POPFAV_i
      + \beta_2(u_i,v_i,t_i)\,ALT_i
      + \beta_3(u_i,v_i,t_i)\,VEG_i
      + \beta_4(u_i,v_i,t_i)\,AREA_i
      + \beta_5(u_i,v_i,t_i)\,PREC_i
      + \varepsilon_i
    `,
  },
  {
    value: "ols",
    label: "Ordinary Least Squares",
    titulo: "Ordinary Least Squares",
    descricaoParagrafos: [
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent gravida sit amet diam eget vehicula. Cras gravida ipsum vel tristique bibendum. Donec faucibus accumsan convallis. Suspendisse ullamcorper lacus tortor. Ut eget eros volutpat, auctor sapien in, tincidunt velit. Morbi bibendum metus in nisl molestie commodo. Proin sapien tellus, ullamcorper sit amet nisl vitae, luctus tempor tellus. Sed vel enim mollis dui tristique convallis eu sed ex. Pellentesque quis dapibus sem. Pellentesque eu hendrerit dolor.",
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Morbi bibendum metus in nisl molestie commodo. Proin sapien tellus, ullamcorper sit amet nisl vitae, luctus tempor tellus. Sed vel enim mollis dui tristique convallis eu sed ex. Pellentesque quis dapibus sem. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque eu hendrerit dolor. Integer mattis, ipsum sed posuere pellentesque, justo erat tincidunt nunc, vitae facilisis nibh metus vitae nisi.",
    ],
    formulaBasica: String.raw`y_i = \beta_0 + \sum_{k=1}^{p}\beta_k x_{ik} + \varepsilon_i`,
    formula: String.raw`
      y_i =
      \beta_0
      + \beta_1 POPFAV_i
      + \beta_2 ALT_i
      + \beta_3 VEG_i
      + \beta_4 AREA_i
      + \beta_5 PREC_i
      + \varepsilon_i
    `,
  },
];

const ANIMAIS = [
  { value: "", label: "Todos os animais" },
  { value: "escorpiao", label: "Escorpião" },
  { value: "serpente", label: "Serpente" },
  { value: "aranha", label: "Aranha" },
  { value: "abelha", label: "Abelha" },
  { value: "lagarta", label: "Lagarta" },
];

export default function ModelsPage() {
  const [filters, setFilters] = useState({
    modelo: "",
    animal: "",
  });

  const modelosOptions = useMemo(
    () => [
      { value: "", label: "Selecione o modelo" },
      ...MODELOS.map((item) => ({
        value: item.value,
        label: item.label,
      })),
    ],
    [],
  );

  const selectedModel =
    MODELOS.find((item) => item.value === filters.modelo) ?? MODELOS[0];

  const handleModeloChange = (e) => {
    setFilters((prev) => ({ ...prev, modelo: e.target.value }));
  };

  const handleAnimalChange = (e) => {
    setFilters((prev) => ({ ...prev, animal: e.target.value }));
  };

  const animalSelecionado = ANIMAIS.find(
    (a) => a.value === filters.animal,
  )?.label;

  return (
    <>
      <Header />

      <main className={styles.main}>
        <div className={styles.container}>
          <header className={styles.pageHeader}>
            <h1 className={styles.title}>Modelos</h1>
            <p className={styles.subtitle}>
              Veja informações sobre sua região
            </p>
          </header>

          <section className={styles.filterSection}>
            <div className={styles.filterBox}>
              <div className={styles.formGrid}>
                <UiSelect
                  label="Modelo"
                  value={filters.modelo}
                  onChange={handleModeloChange}
                  options={modelosOptions}
                  placeholder="Selecione o modelo"
                />

                <UiSelect
                  label="Animal"
                  value={filters.animal}
                  onChange={handleAnimalChange}
                  options={ANIMAIS}
                  placeholder="Selecione o animal"
                />
              </div>
            </div>
          </section>

          {selectedModel && (
            <section className={styles.modelSection}>
              <div className={styles.modelContent}>
                <h2 className={styles.modelTitle}>{selectedModel.titulo}</h2>

                <div className={styles.introBlock}>
                  <div className={styles.introText}>
                    <p className={styles.paragraph}>{selectedModel.descricaoParagrafos[0]}</p>
                  </div>

                  <aside className={styles.basicFormulaCard}>
                    <div className={styles.basicFormulaLabel}>Formulação do método</div>
                    <BlockMath math={selectedModel.formulaBasica} />
                  </aside>
                </div>

                {selectedModel.descricaoParagrafos.slice(1).map((paragrafo, idx) => (
                  <p key={idx} className={styles.paragraph}>
                    {paragrafo}
                  </p>
                ))}

                {filters.animal && (
                  <div className={styles.infoBadge}>
                    Animal selecionado:{" "}
                    <span className={styles.infoBadgeStrong}>
                      {animalSelecionado}
                    </span>
                  </div>
                )}

                <div className={styles.formulaWrapper}>
                  <div className={styles.formulaLabel}>Especificação do modelo</div>
                  <div className={styles.formulaCard}>
                    <BlockMath math={selectedModel.formula} />
                  </div>
                </div>

                <div className={styles.descriptionSection}>
                  <h3 className={styles.sectionTitle}>Variáveis</h3>

                  <div className={styles.variableList}>
                    {COVARIAVEIS.map((variavel) => (
                      <div key={variavel.nome} className={styles.variableItem}>
                        <span className={styles.variableCode}>
                          {variavel.sigla}
                        </span>
                        <span className={styles.variableText}>
                          é a variável <strong>{variavel.nome}</strong>, que
                          representa a {variavel.descricao}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </section>
          )}
        </div>
      </main>

      <Footer />
    </>
  );
}