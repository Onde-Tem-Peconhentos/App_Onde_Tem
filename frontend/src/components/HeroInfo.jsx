import styles from "./styles/HeroInfo.module.css";
const EMAIL = "contato@seudominio.com";
const SUBJECT = "Contato pelo site Onde Tem";
const BODY = "Olá, equipe!";
export default function HeroInfo({
  badgeText = "Projeto USP • ICMC",
  title = "Título Padrão",
  description = "",
  buttonText = "Saiba mais",
  onButtonClick = null,
  background = "default",
}) {
  return (
    <section
      className={`${styles.hero} ${
        background === "blue" ? styles.heroBlue : ""
      }`}
    >
      <div className={styles.heroInner}>
        {badgeText && <span className={styles.badge}>{badgeText}</span>}
        {title && <h1 className={styles.title}>{title}</h1>}
        {description && <p className={styles.lead}>{description}</p>}
        {buttonText && (
          <button
            className={styles.cta}
            aria-label="Enviar e-mail para a equipe"
            onClick={() => {
              const mailto = `mailto:${EMAIL}?subject=${encodeURIComponent(
                SUBJECT
              )}&body=${encodeURIComponent(BODY)}`;
              window.location.href = mailto;
            }}
          >
            Fale com a equipe
          </button>
        )}
      </div>
    </section>
  );
}
