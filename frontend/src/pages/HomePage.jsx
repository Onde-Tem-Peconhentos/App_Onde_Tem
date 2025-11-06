import React from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import styles from "./styles/HomePage.module.css";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Clock, PhoneCall, MapPin } from "lucide-react";

export default function HomePage() {
  return (
    <>
      <Header />
      <section className={styles.hero}>
        <div className={styles.content}>
          <h1 className={styles.title}>
            Encontre o posto de saúde <br /> mais próximo
          </h1>

          <p className={styles.subtitle}>
            Localize rapidamente hospitais com soro antiveneno no estado de São
            Paulo
          </p>

          <div className={styles.searchContainer}>
            <input
              type="text"
              placeholder="Digite sua cidade ou CEP"
              className={styles.input}
            />
            <button className={styles.button}>Buscar</button>
          </div>
        </div>
      </section>

      {/* INFORMAÇÕES IMPORTANTES */}
      <section className={styles.infoSection}>
        {/* linha decorativa superior */}
        <span className={styles.topDivider} aria-hidden />

        <ul className={styles.list}>
          {/* 1. Tempo é crucial */}
          <li className={styles.item}>
            <div className={`${styles.icon} ${styles.iconBlue}`}>
              <Clock size={28} />
            </div>
            <div className={styles.text}>
              <h4>Tempo é crucial</h4>
              <p>
                Quanto mais rápido o atendimento, melhor o resultado do
                tratamento
              </p>
            </div>
          </li>

          {/* 2. Em Emergência */}
          <li className={`${styles.emergency}`}>
            <span className={styles.bar} aria-hidden />
            <div className={`${styles.item} `}>
              <div className={`${styles.icon} ${styles.iconRed}`}>
                <PhoneCall size={28} />
              </div>
              <div className={styles.text}>
                <h4>Em Emergência</h4>
                <p>Ligue imediatamente para o SAMU</p>
              </div>
            </div>
            <a href="tel:192" className={styles.emergencyBtn}>
              Ligar 192
            </a>
          </li>

          {/* 3. Atendimento Gratuito */}
          <li className={styles.item}>
            <div className={`${styles.icon} ${styles.iconBlue}`}>
              <MapPin size={28} />
            </div>
            <div className={styles.text}>
              <h4>Atendimento Gratuito</h4>
              <p>Todos os hospitais listados oferecem atendimento pelo SUS</p>
            </div>
          </li>
        </ul>
      </section>

      {/* SEÇÃO MAPA */}
      <section className={styles.mapSection}>
        <div className={styles.mapContainer}>
          <div className={styles.mapText}>
            <h3>Veja os casos na sua região</h3>
            <p>
              Acompanhe a incidência semanal estimada com nowcasting e
              tendências locais.
            </p>
            <div className={styles.mapButtons}>
              <button className={styles.primaryBtn}>Buscar</button>
              <button className={styles.secondaryBtn}>Ir para dashboard</button>
            </div>
          </div>

          <div className={styles.mapBox}>
            <MapContainer
              center={[-23.5505, -46.6333]} // São Paulo
              zoom={11}
              scrollWheelZoom={false}
              className={styles.map}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <Marker position={[-23.5505, -46.6333]}>
                <Popup>São Paulo - Região central</Popup>
              </Marker>
            </MapContainer>
          </div>
        </div>
      </section>
      <Footer />
    </>
  );
}
