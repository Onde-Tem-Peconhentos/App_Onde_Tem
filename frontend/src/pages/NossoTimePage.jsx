import Header from "../components/Header";
import Footer from "../components/Footer";
import HeroInfo from "../components/HeroInfo";
import TeamCard from "../components/TeamCard";
import styles from "./styles/NossoTimePage.module.css";
import avatar from "../assets/avatar.png";

// mock: você pode trocar por dados reais futuramente (API)
const TEAM = [
  {
    id: 1,
    name: "Maristela Oliveira dos Santos",
    role: "Doutora em …",
    avatar: avatar,
    tags: ["Otimização", "Pesquisa", "Saúde Pública"],
    social: { linkedin: "#", github: "#", site: "#" },
  },
  {
    id: 2,
    name: "Maristela Oliveira dos Santos",
    role: "Doutora em …",
    avatar: avatar,
    tags: ["Otimização", "Pesquisa", "Saúde Pública"],
    social: { linkedin: "#", github: "#", site: "#" },
  },
  {
    id: 3,
    name: "Maristela Oliveira dos Santos",
    role: "Doutora em …",
    avatar: avatar,
    tags: ["Otimização", "Pesquisa", "Saúde Pública"],
    social: { linkedin: "#", github: "#", site: "#" },
  },
  {
    id: 4,
    name: "Maristela Oliveira dos Santos",
    role: "Doutora em …",
    avatar: avatar,
    tags: ["Otimização", "Pesquisa", "Saúde Pública"],
    social: { linkedin: "#", github: "#", site: "#" },
  },
  {
    id: 5,
    name: "Maristela Oliveira dos Santos",
    role: "Doutora em …",
    avatar: avatar,
    tags: ["Otimização", "Pesquisa", "Saúde Pública"],
    social: { linkedin: "#", github: "#", site: "#" },
  },
  {
    id: 6,
    name: "Maristela Oliveira dos Santos",
    role: "Doutora em …",
    avatar: avatar,
    tags: ["Otimização", "Pesquisa", "Saúde Pública"],
    social: { linkedin: "#", github: "#", site: "#" },
  },
  {
    id: 7,
    name: "Maristela Oliveira dos Santos",
    role: "Doutora em …",
    avatar: avatar,
    tags: ["Otimização", "Pesquisa", "Saúde Pública"],
    social: { linkedin: "#", github: "#", site: "#" },
  },
  {
    id: 8,
    name: "Maristela Oliveira dos Santos",
    role: "Doutora em …",
    avatar: avatar,
    tags: ["Otimização", "Pesquisa", "Saúde Pública"],
    social: { linkedin: "#", github: "#", site: "#" },
  },
  {
    id: 9,
    name: "Maristela Oliveira dos Santos",
    role: "Doutora em …",
    avatar: avatar,
    tags: ["Otimização", "Pesquisa", "Saúde Pública"],
    social: { linkedin: "#", github: "#", site: "#" },
  },
];
const EMAIL = "contato@seudominio.com";
const SUBJECT = "Contato pelo site Onde Tem";
const BODY = "Olá, equipe!";

export default function TeamPage() {
  return (
    <>
      <Header />

      {/* HERO reutilizável com o fundo azul e recortes brancos */}
      <HeroInfo
        badgeText="Projeto USP • ICMC"
        title="Nossa Equipe"
        description="conheça os pesquisadores, professores e alunos que tornam este Painel possível, unindo ciência de dados, matemática aplicada e saúde pública."
        buttonText="Fale com a equipe"
        onButtonClick={() => window.open("#contato", "_self")}
        background="blue"
      />

      <main className={styles.main}>
        <h2 className={styles.sectionTitle}>Equipe de Pesquisa</h2>

        <section className={styles.grid}>
          {TEAM.map((p) => (
            <TeamCard key={p.id} {...p} />
          ))}
        </section>

        <section className={styles.callout}>
          <h3>Quer contribuir com o Painel?</h3>
          <p>
            Entre em contato com um de nossos colaboradores pela aba{" "}
            <strong>Equipe</strong>. Parcerias em computação científica e saúde
            pública são bem-vindas.
          </p>
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
        </section>
      </main>

      <Footer />
    </>
  );
}
