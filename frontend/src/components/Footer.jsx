import React from "react";
import styles from "./styles/Footer.module.css";

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.container}>
        <p className={styles.copy}>
          © 2025 <strong>ICMC</strong> — Todos os direitos reservados.
        </p>

        <div className={styles.links}>
          <a href="/privacidade" className={styles.link}>
            Política de Privacidade
          </a>
          <span className={styles.divider}>•</span>
          <a href="/contato" className={styles.link}>
            Contato
          </a>
        </div>
      </div>
    </footer>
  );
}
