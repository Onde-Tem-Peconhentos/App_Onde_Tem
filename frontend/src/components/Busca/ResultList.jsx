import styles from "../../pages/styles/BuscaPage.module.css";

export default function ResultList({ top }) {
  if (!top?.length) return null;

  return (
    <section className={styles.resultsSection}>
      <h2>Unidades mais próximas</h2>
      <div className={styles.resultsGrid}>
        {top.map((p) => (
          <div key={p.id} className={styles.resultCard}>
            <div className={styles.resultTitle}>{p.ubs || "Unidade"}</div>
            <div className={styles.resultLine}>{p.endereco}</div>
            <div className={styles.resultLine}>
              <b>{p.municipio}</b>
            </div>

            <div className={styles.resultMeta}>
              {p.tempo_min?.toFixed(0)} min • {p.distancia_km?.toFixed(1)} km
            </div>

            {p.telefone && (
              <div className={styles.resultPhone}>📞 {p.telefone}</div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
