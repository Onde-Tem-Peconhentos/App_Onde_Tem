// src/pages/ModelsPage.jsx
import React from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import UiSelect from "../components/UiSelect";
import ModelDetails from "../components/ModelDetails";
import { useModelsFilters } from "../hooks/useModelsFilters";
import styles from "./styles/Modelos.module.css";
import "katex/dist/katex.min.css";

export default function ModelsPage() {
  const {
    filters,
    handleFilterChange,
    modelosOptions,
    animaisOptions,
    temposOptions,
    selectedModel,
    isLoading,
  } = useModelsFilters();

  const filtersConfig = [
  {
    key: "modelo",
    label: "Modelo",
    options: modelosOptions,
    placeholder: "Selecione o modelo",
  },
  {
    key: "animal",
    label: "Animal",
    options: animaisOptions,
    placeholder: "Selecione o animal",
  },
  {
    key: "tempo",
    label: "Tempo",
    options: temposOptions,
    placeholder: "Selecione o período",
  },
];

  return (
    <>
      <Header />

      <main className={styles.main}>
        <div className={styles.container}>
          <header className={styles.pageHeader}>
            <h1 className={styles.title}>Modelos</h1>
            <p className={styles.subtitle}>
              
            </p>
          </header>

          <section className={styles.filterSection}>
            <div className={styles.filterBox}>
              <div className={styles.formGrid}>
                {filtersConfig.map((filter) => (
                  <UiSelect
                    key={filter.key}
                    label={filter.label}
                    value={filters[filter.key] || ""}
                    onChange={handleFilterChange(filter.key)}
                    options={filter.options}
                    placeholder={filter.placeholder}
                  />
                ))}
              </div>
            </div>
          </section>

          {isLoading ? (
            <div className={styles.loading}>
              <p>Carregando modelo...</p>
            </div>
          ) : (
            selectedModel && (
              <ModelDetails model={selectedModel} filters={filters} />
            )
          )}
        </div>
      </main>

      <Footer />
    </>
  );
}