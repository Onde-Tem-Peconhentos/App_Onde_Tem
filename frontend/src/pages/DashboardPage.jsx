import React, { useState, useEffect } from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import UiSelect from "../components/UiSelect";
import styles from "./styles/DashboardPage.module.css";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
  AreaChart,
  Area,
  ResponsiveContainer,
} from "recharts";

export default function DashboardPage() {
  // ======== ESTADOS ========
  const [filters, setFilters] = useState({
    municipio: "",
    ano: "",
    animal: "",
  });

  const [metrics, setMetrics] = useState({
    totalCasos: 0,
    taxaObitos: 0,
    tempoAtendimento: 0,
  });

  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // opções vindas do backend
  const [municipiosOptions, setMunicipiosOptions] = useState([]);
  const [anosOptions, setAnosOptions] = useState([]);
  const [animaisOptions, setAnimaisOptions] = useState([]);

  // ======== CHAMADA DE API ========
  useEffect(() => {
    const fetchFilters = async () => {
      try {
        const [resMun, resAno, resAnimal] = await Promise.all([
          fetch("http://localhost:8000/dashboard/municipios"),
          fetch("http://localhost:8000/dashboard/anos"),
          fetch("http://localhost:8000/dashboard/animal"),
        ]);

        if (!resMun.ok || !resAno.ok || !resAnimal.ok) {
          throw new Error("Erro ao buscar filtros");
        }

        const [munData, anosData, animaisData] = await Promise.all([
          resMun.json(),
          resAno.json(),
          resAnimal.json(),
        ]);

        const optionsMun = munData.map((mun) => ({
          label: mun.nome,
          value: mun.nome,
        }));

        const optionsAno = anosData.map((item) => ({
          label: item.ano,
          value: item.ano,
        }));

        const optionsAnimais = animaisData.map((a) => ({
          label: a.nome,
          value: a.nome,
        }));

        setMunicipiosOptions(optionsMun);
        setAnosOptions(optionsAno);
        setAnimaisOptions(optionsAnimais);
      } catch (e) {
        console.error(e);
      }
    };

    fetchFilters();
  }, []);

  // ======== BUSCAR MÉTRICAS / GRÁFICOS ========
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [
          resTotal,
          resTaxa,
          resTempo,
          resCasosAno,
          resDistAnimal,
          resGravidade,
        ] = await Promise.all([
          fetch("http://localhost:8000/dashboard/total_acidentes"),
          fetch("http://localhost:8000/dashboard/taxa_obitos"),
          fetch("http://localhost:8000/dashboard/tempo_medio_atendimento"),
          fetch("http://localhost:8000/dashboard/casos_por_ano"),
          fetch("http://localhost:8000/dashboard/distribuicao_por_tipo_animal"),
          fetch("http://localhost:8000/dashboard/gravidade_dos_casos"),
        ]);

        if (
          !resTotal.ok ||
          !resTaxa.ok ||
          !resTempo.ok ||
          !resCasosAno.ok ||
          !resDistAnimal.ok ||
          !resGravidade.ok
        ) {
          throw new Error("Falha ao buscar dados do dashboard");
        }

        const [
          dataTotal,
          dataTaxa,
          dataTempo,
          dataCasosAno,
          dataDistAnimal,
          dataGravidade,
        ] = await Promise.all([
          resTotal.json(),
          resTaxa.json(),
          resTempo.json(),
          resCasosAno.json(),
          resDistAnimal.json(),
          resGravidade.json(),
        ]);

        // usar casos por ano para o gráfico principal
        const chartAno = dataCasosAno.map((item) => ({
          name: item.ano,
          casos: item.total_acidentes,
        }));

        setChartData(chartAno);

        setMetrics({
          totalCasos: dataTotal.total_acidentes,
          taxaObitos: dataTaxa.taxa_obitos, // já vem em %
          tempoAtendimento: dataTempo.tempo_medio_atendimento_horas,
        });

        // você pode guardar dataDistAnimal e dataGravidade em states extras
      } catch (err) {
        console.error(err);
        setError("Erro ao carregar dados. Tente novamente mais tarde.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [filters]);

  // ======== HANDLERS ========
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  // ======== RENDER ========
  return (
    <>
      <Header />
      <main className={styles.main}>
        <h1 className={styles.title}>Dashboard</h1>
        <p className={styles.subtitle}>Veja informações sobre sua região</p>

        {/* === FILTROS === */}
        <form className={styles.formBox}>
          <div className={styles.formGrid}>
            <div className={`${styles.fieldGroup} ${styles.municipio}`}>
              <UiSelect
                label="Município"
                name="municipio"
                value={filters.municipio}
                onChange={handleChange}
                placeholder={
                  municipiosOptions.length === 0
                    ? "Carregando municípios..."
                    : "Selecione o município"
                }
                options={municipiosOptions}
              />
            </div>

            <div className={`${styles.fieldGroup} ${styles.ano}`}>
              <UiSelect
                label="Ano"
                name="ano"
                value={filters.ano}
                onChange={handleChange}
                placeholder={
                  municipiosOptions.length === 0
                    ? "Carregando anos..."
                    : "Selecione o ano"
                }
                options={anosOptions}
              />
            </div>

            <div className={`${styles.fieldGroup} ${styles.animal}`}>
              <UiSelect
                label="Animal"
                name="animal"
                value={filters.animal}
                onChange={handleChange}
                placeholder={
                  municipiosOptions.length === 0
                    ? "Carregando animais..."
                    : "Selecione o animal"
                }
                options={animaOptions}
              />
            </div>
          </div>
        </form>

        {/* === MÉTRICAS === */}
        <section className={styles.metricsSection}>
          <div className={styles.metricCard}>
            <h3>Total de casos</h3>
            <p>{metrics.totalCasos}</p>
          </div>
          <div className={styles.metricCard}>
            <h3>Taxa de Óbitos</h3>
            <p>{metrics.taxaObitos}%</p>
          </div>
          <div className={styles.metricCard}>
            <h3>Tempo Médio de Atendimento</h3>
            <p>{metrics.tempoAtendimento} min</p>
          </div>
        </section>

        {/* === LOADING / ERRO === */}
        {loading && <p className={styles.loading}>Carregando dados...</p>}
        {error && <p className={styles.error}>{error}</p>}

        {/* === GRÁFICOS === */}
        {!loading && !error && (
          <section className={styles.chartsGrid}>
            <div className={styles.chartCard}>
              <h3>Casos Por Ano</h3>
              <p>Quantidade total de casos registrados por ano</p>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="casos" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className={styles.chartCard}>
              <h3>Distribuição por Tipo de Animal</h3>
              <p>Distribuição de casos por tipo de animal</p>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Area dataKey="casos" fill="#3b82f6" stroke="#3b82f6" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className={styles.chartCard}>
              <h3>Gravidade dos Casos</h3>
              <p>Gravidade dos casos registrados (leve, moderado, grave)</p>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="casos" stroke="#3b82f6" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>
        )}
      </main>
      <Footer />
    </>
  );
}
