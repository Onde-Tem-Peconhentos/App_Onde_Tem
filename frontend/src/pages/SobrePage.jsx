import Header from "../components/Header";
import Footer from "../components/Footer";
import styles from "./styles/SobrePage.module.css";
import HeroInfo from "../components/HeroInfo";

export default function SobrePage() {
  return (
    <>
      <Header />
      <HeroInfo
        badgeText="Projeto USP • ICMC"
        title="Sobre o Projeto"
        description="Sistema de alerta precoce que combina dados epidemiológicos, clima e demografia para apoiar a resposta a emergências e a distribuição de soros antiveneno."
        buttonText="Fale com a equipe"
        onButtonClick={() => navigate("/contato")}
      />
      {/* CONTEÚDO */}
      <main className={styles.main}>
        <div className={styles.grid}>
          {/* Objetivo */}
          <section className={styles.card}>
            <h2>Objetivo da Pesquisa</h2>
            <p>
              O Brasil registra um elevado número de acidentes com animais
              peçonhentos. Investigamos a{" "}
              <strong>
                otimização da localização de postos com soros antiveneno
              </strong>
              , visando reduzir o tempo de resposta a emergências em São Paulo.
              Realizamos análises exploratórias com dados do{" "}
              <strong>SINAN</strong> e{" "}
              <strong>algoritmos de caminho mínimo</strong>. O próximo passo é
              modelar a <strong>redistribuição eficiente de soros</strong> via
              técnicas de otimização.
            </p>
          </section>

          {/* Universidade */}
          <section className={styles.card}>
            <h2>Universidade de São Paulo - ICMC</h2>
            <p>
              Projeto conduzido no{" "}
              <strong>
                Instituto de Ciências Matemáticas e de Computação (ICMC/USP)
              </strong>
              , referência nacional e internacional em computação, estatística e
              matemática aplicada.
            </p>

            <div className={styles.location}>
              <span className={styles.dot} />
              São Carlos — SP, Brasil
            </div>
          </section>

          {/* Fontes de dados */}
          <section className={styles.card}>
            <h2>De onde vêm os dados?</h2>

            <h3>Casos notificados</h3>
            <p>
              Doenças de notificação compulsória registradas por profissionais
              de saúde e consolidadas em níveis municipal, estadual e federal. A
              partir delas calculamos os{" "}
              <strong>indicadores de incidência</strong> do painel.
            </p>

            <h3>Dados climáticos</h3>
            <p>
              Temperatura e umidade de <strong>estações meteorológicas</strong>{" "}
              e <strong>imagens de satélite</strong>, pois o clima influencia a
              ocorrência de acidentes.
            </p>

            <h3>Dados demográficos</h3>
            <p>
              Estimativas populacionais do <strong>IBGE</strong> atualizadas
              anualmente para compor os indicadores epidemiológicos por
              município.
            </p>
          </section>

          {/* Nowcasting */}
          <section className={styles.card}>
            <h2>Previsão de casos (Nowcasting)</h2>
            <p>
              Para mitigar <strong>atrasos de notificação</strong>, empregamos
              um método de <strong>inferência Bayesiana</strong> que combina a
              distribuição de atrasos com padrões históricos para estimar o
              número esperado de casos semanais, conforme Bastos, Economou{" "}
              <em>et al.</em> (2019). O resultado é uma estimativa em tempo
              quase real que apoia decisões operacionais e comunicação de risco.
            </p>
          </section>

          {/* Implementação */}
          <section className={styles.card}>
            <h2>Implementação</h2>
            <p>
              Todo o código do Painel Onde Tem é desenvolvido em Python e
              disponibilizado publicamente.
            </p>
            <a
              className={styles.ghButton}
              href="https://github.com/"
              target="_blank"
              rel="noreferrer"
            >
              Ver repositório no GitHub
            </a>
          </section>

          {/* Relatórios */}
          <section className={styles.card}>
            <h2>Relatórios Técnicos</h2>
            <ul className={styles.list}>
              <li>
                Reflexões sobre o risco de Acidentes com Animais Peçonhentos em
                2024
              </li>
            </ul>
          </section>

          {/* Citação */}
          <section className={styles.card}>
            <h2>Como citar o Painel?</h2>
            <p className={styles.citation}>
              C. Codeço, F. Coelho, O. Cruz, S. Oliveira, T. Castro, L. Bastos,
              Infodengue: A nowcasting system for the surveillance of
              arboviruses in Brazil, Revue d’Epidémiologie et de Santé Publique,
              Vol 66, Suppl 5, 2018, p. S386. DOI:{" "}
              <strong>10.1016/j.respe.2018.05.408</strong>.
            </p>
          </section>

          {/* Contribuir */}
          <section className={`${styles.card} ${styles.center}`}>
            <h2>Quer contribuir com o Painel?</h2>
            <p>
              Entre em contato com um de nossos colaboradores pela aba{" "}
              <strong>Nosso Time</strong>. Parcerias em computação científica e
              saúde pública são bem-vindas.
            </p>
            <button className={styles.ctaLight}>Fale com a equipe</button>
          </section>
        </div>
      </main>

      <Footer />
    </>
  );
}
