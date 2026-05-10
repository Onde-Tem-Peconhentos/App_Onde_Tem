// src/hooks/useModelsFilters.js
import { useState, useMemo } from "react";
import { MODELOS, ANIMAIS, TEMPOS } from "../data/constants";

export function useModelsFilters() {
  const DEFAULT_MODELO = MODELOS.find((m) => m.value === "")?.value ?? MODELOS[0]?.value ?? "";
  const DEFAULT_ANIMAL = ANIMAIS.find((a) => a.value === "")?.value ?? ANIMAIS[0]?.value ?? "";
  const DEFAULT_TEMPO  = TEMPOS.find((t) => t.value === "")?.value ?? TEMPOS[0]?.value ?? "";

  const [filters, setFilters] = useState({
    modelo: DEFAULT_MODELO,
    animal: DEFAULT_ANIMAL,
    tempo:  DEFAULT_TEMPO,
  });

  const handleFilterChange = (field) => (e) => {
    setFilters((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const modelosOptions = useMemo(
      () =>
        MODELOS.map((item) => ({
          value: item.value,
          label: item.label,
        })),
      []
    );

  const selectedModel =
    MODELOS.find((item) => item.value === filters.modelo) ??
    MODELOS[0];

  return {
    filters,
    handleFilterChange,
    modelosOptions,
    animaisOptions: ANIMAIS,
    temposOptions: TEMPOS,
    selectedModel,
  };
}