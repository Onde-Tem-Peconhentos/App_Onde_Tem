import React, { useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import styles from "../../pages/styles/BuscaPage.module.css";

// Corrige ícone padrão do Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

export default function SearchMaps({ resultado, top }) {
  const mapCenter = useMemo(() => {
    if (resultado?.origem?.lat && resultado?.origem?.lon) {
      return [resultado.origem.lat, resultado.origem.lon];
    }
    return [-23.55, -46.63];
  }, [resultado]);

  const zoom = resultado ? 11 : 9;

  return (
    <section className={styles.mapSection}>
      <h2>Localização das unidades de soro</h2>

      <div className={styles.mapWrapper}>
        <MapContainer
          center={mapCenter}
          zoom={zoom}
          scrollWheelZoom={false}
          className={styles.map}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {resultado?.origem?.lat && resultado?.origem?.lon && (
            <Marker position={[resultado.origem.lat, resultado.origem.lon]}>
              <Popup>
                <b>Origem</b>
                <div>{resultado.origem.endereco}</div>
              </Popup>
            </Marker>
          )}

          {(top || []).map((p) => (
            <Marker key={p.id} position={[p.latitude, p.longitude]}>
              <Popup>
                <b>{p.ubs || "Unidade"}</b>
                <div>{p.endereco}</div>
                <div>{p.municipio}</div>
                <div>
                  {p.tempo_min?.toFixed?.(1)} min •{" "}
                  {p.distancia_km?.toFixed?.(2)} km
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </section>
  );
}
