import React from "react";
import { 
  MapPin, 
  Building2, 
  Clock, 
  Navigation, 
  Phone, 
  ExternalLink, 
  LocateFixed 
} from "lucide-react"; // npm install lucide-react
import styles from "../../pages/styles/BuscaPage.module.css";

export default function ResultList({ top }) {
  // Se não houver resultados retornados pelo backend, o componente não renderiza
  if (!top || top.length === 0) return null;

  return (
    <section className={styles.resultsSection}>
      <h2>
        <LocateFixed size={24} />
        Unidades mais próximas
      </h2>
      
      <div className={styles.resultsGrid}>
        {top.map((item) => {
          // Gera o link dinâmico para o Google Maps com base na latitude e longitude
          const mapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${item.latitude},${item.longitude}`;
          
          return (
            <div 
              key={item.id} 
              id={`posto-${item.id}`} // ID fundamental para o scroll automático vindo do mapa
              className={styles.resultCard}
            >
              <div className={styles.resultHeader}>
                <div className={styles.resultTitle}>{item.ubs}</div>
                
                <div className={styles.resultLine}>
                  <Building2 size={18} />
                  <span>{item.endereco}</span>
                </div>
                
                <div className={styles.resultLine}>
                  <MapPin size={18} />
                  <span>{item.municipio}</span>
                </div>
              </div>

              {/* Badges com informações de tempo e distância calculadas via Matrix API */}
              <div className={styles.resultMeta}>
                <div className={styles.metaBadge}>
                  <Clock size={16} />
                  <span>{item.tempo_min?.toFixed(1)} min</span>
                </div>
                <div className={styles.metaBadge}>
                  <Navigation size={16} />
                  <span>{item.distancia_km?.toFixed(2)} km</span>
                </div>
              </div>

              <div className={styles.cardActions}>
                <a 
                  href={mapsUrl} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className={styles.mapsBtn}
                >
                  <ExternalLink size={18} />
                  Ver no Google Maps
                </a>

                {/* Exibe o botão de telefone apenas se houver o dado cadastrado no banco */}
                {item.telefone && (
                  <a 
                    href={`tel:${item.telefone}`} 
                    className={styles.phoneBtn} 
                    title={`Ligar para ${item.ubs}`}
                  >
                    <Phone size={20} />
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}