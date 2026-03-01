import styles from "./styles/TeamCard.module.css";
import { Linkedin, Github, Globe } from "lucide-react";

export default function TeamCard({
  name,
  role,
  avatar,
  tags = [],
  social = {},
}) {
  const initials = name
    ?.split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

  return (
    <article className={styles.card}>
      <div className={styles.avatar}>
        {avatar ? (
          <img src={avatar} alt={name} />
        ) : (
          <span className={styles.initials}>{initials}</span>
        )}
      </div>

      <h4 className={styles.name}>{name}</h4>
      <p className={styles.role}>{role}</p>

      <div className={styles.social}>
        {social.linkedin && (
          <a
            href={social.linkedin}
            aria-label="LinkedIn"
            target="_blank"
            rel="noreferrer"
          >
            <Linkedin size={16} />
          </a>
        )}
        {social.github && (
          <a
            href={social.github}
            aria-label="GitHub"
            target="_blank"
            rel="noreferrer"
          >
            <Github size={16} />
          </a>
        )}
        {social.site && (
          <a
            href={social.site}
            aria-label="Site"
            target="_blank"
            rel="noreferrer"
          >
            <Globe size={16} />
          </a>
        )}
      </div>

      <div className={styles.tags}>
        {tags.map((t, i) => (
          <span key={i} className={styles.tag}>
            {t}
          </span>
        ))}
      </div>
    </article>
  );
}
