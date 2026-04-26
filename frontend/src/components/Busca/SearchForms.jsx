import React from "react";
import { Search, Trash2 } from "lucide-react";
import UiSelect from "../UiSelect";
import UiInput from "../UiInput";
import styles from "../../pages/styles/BuscaPage.module.css";

export default function SearchForms({
  form,
  onChange,
  onSubmit,
  onClear,
  onUseCurrentLocation,
  loading,
  loadingGeo,
  erro,
  municipiosOptions,
  animaisOptions,
}) {
  return (
    <div className={styles.formBox}>
      <div className={styles.formHeader}>
        <h3>Filtros de busca</h3>
        <button type="button" className={styles.secondaryButton} onClick={onClear} disabled={loading || Object.values(form).every(v => v === "")}>
          Limpar tudo
        </button>
      </div>

      <form onSubmit={onSubmit}>
        <div className={styles.formGrid}>
          {/* Campo CEP adicionado ao grid */}
          <div className={`${styles.fieldGroup} ${styles.cep}`}>
            <label>CEP</label>
            <UiInput
              name="cep"
              value={form.cep}
              onChange={onChange}
              placeholder="00000-000"
            />
          </div>

          <div className={`${styles.fieldGroup} ${styles.endereco}`}>
            <label>Endereço</label>
            <UiInput
              name="endereco"
              value={form.endereco}
              onChange={onChange}
              placeholder="Digite a rua"
            />
          </div>

          <div className={`${styles.fieldGroup} ${styles.numero}`}>
            <label>Nº</label>
            <UiInput
              name="numero"
              value={form.numero}
              onChange={onChange}
              placeholder="123"
            />
          </div>

          <div className={`${styles.fieldGroup} ${styles.bairro}`}>
            <label>Bairro</label>
            <UiInput
              name="bairro"
              value={form.bairro}
              onChange={onChange}
              placeholder="Bairro"
            />
          </div>

          <div className={`${styles.fieldGroup} ${styles.municipio}`}>
            <UiSelect
              label="Município"
              name="municipio"
              value={form.municipio}
              onChange={onChange}
              placeholder="Selecione"
              options={municipiosOptions}
            />
          </div>

          <div className={`${styles.fieldGroup} ${styles.transporte}`}>
            <UiSelect
              label="Transporte"
              name="transporte"
              value={form.transporte}
              onChange={onChange}
              placeholder="Selecione"
              options={[
                { label: "Carro", value: "Carro" },
                { label: "A pé", value: "A pé" },
                { label: "Bicicleta", value: "Bicicleta" },
              ]}
            />
          </div>

          <div className={`${styles.fieldGroup} ${styles.animal}`}>
            <UiSelect
              label="Animal / Soro"
              name="animal"
              value={form.animal}
              onChange={onChange}
              placeholder="Selecione"
              options={animaisOptions}
            />
          </div>
        </div>

        <div className={styles.actions}>
          <button type="submit" className={styles.primaryButton} disabled={loading}>
            {loading ? "Buscando..." : "Buscar Unidades"}
          </button>

          <button
            type="button"
            className={styles.secondaryButton}
            onClick={onUseCurrentLocation}
            disabled={loading || loadingGeo}
          >
            {loadingGeo ? "Obtendo localização..." : "Usar localização atual"}
          </button>
        </div>

        {erro && <div className={styles.errorBox}>{erro}</div>}
      </form>
    </div>
  );
}