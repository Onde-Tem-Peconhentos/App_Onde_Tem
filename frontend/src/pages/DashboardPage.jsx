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

  // ======== SIMULAÇÃO / CHAMADA DE API ========
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        await new Promise((res) => setTimeout(res, 800));
        const data = [
          { name: "2021", casos: 30 },
          { name: "2022", casos: 70 },
          { name: "2023", casos: 20 },
          { name: "2024", casos: 60 },
        ];

        setChartData(data);
        setMetrics({
          totalCasos: 100,
          taxaObitos: 2.5,
          tempoAtendimento: 45,
        });
      } catch (err) {
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
                placeholder="Selecione o município"
                options={[
                  { label: "São Paulo", value: "São Paulo" },
                  { label: "Campinas", value: "Campinas" },
                  { label: "Ribeirão Preto", value: "Ribeirão Preto" },
                ]}
              />
            </div>

            <div className={`${styles.fieldGroup} ${styles.ano}`}>
              <UiSelect
                label="Ano"
                name="ano"
                value={filters.ano}
                onChange={handleChange}
                placeholder="Selecione o ano"
                options={[
                  { label: "2023", value: "2023" },
                  { label: "2024", value: "2024" },
                ]}
              />
            </div>

            <div className={`${styles.fieldGroup} ${styles.animal}`}>
              <UiSelect
                label="Animal"
                name="animal"
                value={filters.animal}
                onChange={handleChange}
                placeholder="Selecione o animal"
                options={[
                  { label: "Serpente", value: "Serpente" },
                  { label: "Aranha", value: "Aranha" },
                  { label: "Escorpião", value: "Escorpião" },
                ]}
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
