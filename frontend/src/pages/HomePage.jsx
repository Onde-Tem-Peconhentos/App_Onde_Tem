import React, { useState } from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import styles from "./styles/HomePage.module.css";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Clock, PhoneCall, MapPin } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const goToBusca = () => {
    const q = query.trim();
    navigate(q ? `/busca?q=${encodeURIComponent(q)}` : "/busca");
  };

  const onSubmit = (e) => {
    e.preventDefault();
    goToBusca();
  };

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

          {/* form p/ Enter funcionar */}
          <form className={styles.searchContainer} onSubmit={onSubmit}>
            <input
              type="text"
              placeholder="Digite sua cidade ou CEP"
              className={styles.input}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button type="submit" className={styles.button}>
              Buscar
            </button>
          </form>
        </div>
      </section>

      {/* INFORMAÇÕES IMPORTANTES */}
      <section className={styles.infoSection}>
        <span className={styles.topDivider} aria-hidden />

        <ul className={styles.list}>
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

          <li className={`${styles.emergency}`}>
            <span className={styles.bar} aria-hidden />
            <div className={styles.item}>
              <div className={`${styles.icon} ${styles.iconRed}`}>
                <PhoneCall size={28} />
              </div>
              <div className={styles.text}>
                <h4>Em Emergência</h4>
                <p>Ligue imediatamente para o SAMU</p>
              </div>
            </div>

            {/* já é link */}
            <a href="tel:192" className={styles.emergencyBtn}>
              Ligar 192
            </a>
          </li>

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
              {/* botão -> link */}
              <Link to="/busca" className={styles.primaryBtn}>
                Buscar
              </Link>

              {/* botão -> link */}
              <Link to="/dashboard" className={styles.secondaryBtn}>
                Ir para dashboard
              </Link>
            </div>
          </div>

          <div className={styles.mapBox}>
            <MapContainer
              center={[-23.5505, -46.6333]}
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
