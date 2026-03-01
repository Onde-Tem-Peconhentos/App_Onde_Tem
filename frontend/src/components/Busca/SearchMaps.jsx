import React, { useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, Tooltip } from "react-leaflet";
import { Map as MapIcon, Navigation, Clock } from "lucide-react";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import styles from "../../pages/styles/BuscaPage.module.css";

// Correção de ícones padrão do Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const iconOrigem = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
});

const iconUnidade = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
});

export default function SearchMaps({ resultado, top }) {
  const mapCenter = useMemo(() => {
    if (resultado?.origem?.lat && resultado?.origem?.lon) {
      return [resultado.origem.lat, resultado.origem.lon];
    }
    return [-23.55, -46.63]; 
  }, [resultado]);

  // Função disparada apenas pelo botão do Popup
  const scrollToResult = (id) => {
    const element = document.getElementById(`posto-${id}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
      
      // Feedback visual no card
      element.style.outline = "3px solid #2563eb";
      element.style.outlineOffset = "4px";
      setTimeout(() => { element.style.outline = "none"; }, 2500);
    }
  };

  const zoom = resultado ? 12 : 9;

  return (
    <section className={styles.mapSection}>
      <h2>
        <MapIcon size={24} />
        Localização das unidades de soro
      </h2>

      <div className={styles.mapWrapper}>
        <MapContainer
          center={mapCenter}
          zoom={zoom}
          scrollWheelZoom={true}
          className={styles.map}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {resultado?.origem?.lat && (
            <Marker position={[resultado.origem.lat, resultado.origem.lon]} icon={iconOrigem}>
              <Tooltip direction="top" offset={[0, -30]}>
                <strong>Sua Localização</strong>
              </Tooltip>
            </Marker>
          )}

          {(top || []).map((p) => (
            <Marker 
              key={p.id} 
              position={[p.latitude, p.longitude]} 
              icon={iconUnidade}
              /* Removido o eventHandler de clique aqui para não subir a tela sozinho */
            >
              {/* Mostra o nome ao passar o mouse */}
              <Tooltip direction="top" offset={[0, -30]} sticky>
                <strong>{p.ubs}</strong>
              </Tooltip>

              <Popup className={styles.mapPopup}>
                <b>{p.ubs}</b>
                <div>{p.endereco}</div>
                
                <div style={{ marginTop: '10px', display: 'flex', gap: '10px', color: '#2563eb' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={14} /> {p.tempo_min?.toFixed(1)} min
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Navigation size={14} /> {p.distancia_km?.toFixed(2)} km
                  </span>
                </div>

                {/* Único gatilho para subir para a lista */}
                <button 
                  onClick={() => scrollToResult(p.id)}
                  style={{
                    marginTop: '12px', width: '100%', border: 'none', 
                    background: '#2563eb', color: '#fff', borderRadius: '8px', 
                    padding: '8px', cursor: 'pointer', fontWeight: '700',
                    fontSize: '0.85rem'
                  }}
                >
                  Ver na lista
                </button>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </section>
  );
}