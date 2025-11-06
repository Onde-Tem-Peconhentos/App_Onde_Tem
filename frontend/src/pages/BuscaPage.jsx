import React, { useState } from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import UiSelect from "../components/UiSelect";
import UiInput from "../components/UiInput";
import styles from "./styles/BuscaPage.module.css";
import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export default function BuscaPage() {
  const [form, setForm] = useState({
    endereco: "",
    numero: "",
    municipio: "",
    transporte: "",
    animal: "",
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <>
      <Header />
      <main className={styles.main}>
        <h1 className={styles.title}>Buscar Soros</h1>
        <p className={styles.subtitle}>Buscar unidade de saúde mais próxima</p>

        <form className={styles.formBox}>
          <div className={styles.formGrid}>
            <div className={`${styles.fieldGroup} ${styles.endereco}`}>
              <label>Endereço</label>
              <UiInput
                name="endereco"
                value={form.endereco}
                onChange={handleChange}
                placeholder="Digite a rua"
                autoComplete="address-line1"
              />
            </div>

            <div className={`${styles.fieldGroup} ${styles.numero}`}>
              <label>Número</label>
              <UiInput
                name="numero"
                value={form.numero}
                onChange={handleChange}
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
                onChange={handleChange}
                placeholder="Selecione o município"
                options={[
                  { label: "São Paulo", value: "São Paulo" },
                  { label: "Campinas", value: "Campinas" },
                  { label: "Ribeirão Preto", value: "Ribeirão Preto" },
                ]}
              />
            </div>

            <div className={`${styles.fieldGroup} ${styles.transporte}`}>
              <UiSelect
                label="Transporte"
                name="transporte"
                value={form.transporte}
                onChange={handleChange}
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
                onChange={handleChange}
                placeholder="Selecione o animal"
                options={[
                  { label: "Serpente", value: "Serpente" },
                  { label: "Aranha", value: "Aranha" },
                  { label: "Escorpião", value: "Escorpião" },
                ]}
              />
            </div>
          </div>
        </form>

        <section className={styles.mapSection}>
          <h2>Localização das unidades de soro</h2>
          <div className={styles.mapWrapper}>
            <MapContainer
              center={[-23.55, -46.63]}
              zoom={9}
              scrollWheelZoom={false}
              className={styles.map}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
            </MapContainer>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
