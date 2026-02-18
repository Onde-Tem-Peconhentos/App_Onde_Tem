import React from "react";
import UiSelect from "../UiSelect";
import UiInput from "../UiInput";
import styles from "../../pages/styles/BuscaPage.module.css";

export default function SearchForms({
  form,
  onChange,
  onSubmit,
  onClear,
  loading,
  erro,
  municipiosOptions,
  animaisOptions,
}) {
  return (
    <form className={styles.formBox} onSubmit={onSubmit}>
      <div className={styles.formGrid}>
        <div className={`${styles.fieldGroup} ${styles.endereco}`}>
          <label>Endereço</label>
          <UiInput
            name="endereco"
            value={form.endereco}
            onChange={onChange}
            placeholder="Digite a rua"
            autoComplete="address-line1"
          />
        </div>

        <div className={`${styles.fieldGroup} ${styles.numero}`}>
          <label>Número</label>
          <UiInput
            name="numero"
            value={form.numero}
            onChange={onChange}
            placeholder="Digite o nº"
            type="text"
            autoComplete="address-line2"
          />
        </div>

        <div className={`${styles.fieldGroup} ${styles.municipio}`}>
          <UiSelect
            label="Município"
            name="municipio"
            value={form.municipio}
            onChange={onChange}
            placeholder="Selecione o município"
            options={municipiosOptions}
          />
        </div>

        <div className={`${styles.fieldGroup} ${styles.transporte}`}>
          <UiSelect
            label="Transporte"
            name="transporte"
            value={form.transporte}
            onChange={onChange}
            placeholder="Selecione o transporte"
            options={[
              { label: "Carro", value: "Carro" },
              { label: "Ambulância", value: "Ambulância" },
              { label: "A pé", value: "A pé" },
            ]}
          />
        </div>

        <div className={`${styles.fieldGroup} ${styles.animal}`}>
          <UiSelect
            label="Animal"
            name="animal"
            value={form.animal}
            onChange={onChange}
            placeholder="Selecione o animal"
            options={animaisOptions}
          />
        </div>
      </div>

      <div style={{ marginTop: 12, display: "flex", gap: 10 }}>
        <button type="submit" className={styles.primaryBtn} disabled={loading}>
          {loading ? "Buscando..." : "Buscar"}
        </button>

        <button
          type="button"
          className={styles.secondaryBtn}
          onClick={onClear}
          disabled={loading}
        >
          {" "}
          Limpar
        </button>
      </div>

      {erro && (
        <div style={{ marginTop: 10, padding: 10, background: "#ff000012" }}>
          {erro}
        </div>
      )}
    </form>
  );
}
