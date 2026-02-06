import React, { useEffect, useMemo, useRef, useState } from "react";
import { FaFolderOpen } from "react-icons/fa";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  AreaChart,
  Area,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

import Header from "../components/Header";
import Footer from "../components/Footer";
import UiSelect from "../components/UiSelect";
import UiMultiSelect from "../components/UiMultiSelect";
import styles from "./styles/DashboardPage.module.css";

// --- Constantes e Helpers ---
const COLORS = [
  "#2563eb",
  "#16a34a",
  "#f97316",
  "#db2777",
  "#7c3aed",
  "#0891b2",
  "#64748b",
];

function formatListPreview(items, max = 3) {
  if (!items || items.length === 0) return "";
  const head = items.slice(0, max).join(", ");
  const rest = items.length - max;
  return rest > 0 ? `${head} +${rest}` : head;
}

export default function DashboardPage() {
  // --- Estados de Filtros e UI ---
  const [filters, setFilters] = useState({
    municipio: "",
    anos: [],
    animais: [],
  });
  const [debouncedFilters, setDebouncedFilters] = useState(filters);
  const [refreshTick, setRefreshTick] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // --- Estados de Dados ---
  const [metrics, setMetrics] = useState({
    totalCasos: 0,
    taxaObitos: 0,
    tempoAtendimento: 0,
  });
  const [chartData, setChartData] = useState([]);
  const [animalData, setAnimalData] = useState([]);
  const [severityData, setSeverityData] = useState([]);

  // --- Estados de Opções ---
  const [municipiosOptions, setMunicipiosOptions] = useState([]);
  const [anosOptions, setAnosOptions] = useState([]);
  const [animaisOptions, setAnimaisOptions] = useState([]);

  const filterRef = useRef(null);

  // --- Memoized Formatters ---
  const nfInt = useMemo(
    () => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }),
    []
  );
  const nf1 = useMemo(
    () =>
      new Intl.NumberFormat("pt-BR", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }),
    []
  );
  const nf2 = useMemo(
    () =>
      new Intl.NumberFormat("pt-BR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
    []
  );

  const tooltipProps = useMemo(
    () => ({
      contentStyle: { borderRadius: 12, border: "1px solid #e5e7eb" },
      labelStyle: { fontWeight: 600 },
      cursor: { fill: "transparent" },
    }),
    []
  );

  // --- Lógica de Chips e Empty State ---
  const activeChips = useMemo(() => {
    const chips = [];
    if (filters.municipio)
      chips.push({ key: "mun", label: `Município: ${filters.municipio}` });
    if (filters.anos.length > 0)
      chips.push({
        key: "anos",
        label: `Anos: ${formatListPreview(filters.anos.map(String))}`,
      });
    if (filters.animais.length > 0)
      chips.push({
        key: "animais",
        label: `Animais: ${formatListPreview(filters.animais)}`,
      });
    return chips;
  }, [filters]);

  const isEmpty =
    !loading &&
    !error &&
    Number(metrics.totalCasos ?? 0) === 0 &&
    (chartData?.length ?? 0) === 0;

  const lastUpdatedText = useMemo(() => {
    if (!lastUpdated) return "—";
    return lastUpdated.toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }, [lastUpdated]);

  // --- Effects ---
  useEffect(() => {
    const t = setTimeout(() => setDebouncedFilters(filters), 420);
    return () => clearTimeout(t);
  }, [filters]);

  useEffect(() => {
    const fetchFilters = async () => {
      try {
        const [resMun, resAno, resAnimal] = await Promise.all([
          fetch("http://localhost:8000/dashboard/municipios"),
          fetch("http://localhost:8000/dashboard/anos"),
          fetch("http://localhost:8000/dashboard/animal"),
        ]);

        if (!resMun.ok || !resAno.ok || !resAnimal.ok)
          throw new Error("Erro ao buscar filtros");

        const [munData, anosData, animaisData] = await Promise.all([
          resMun.json(),
          resAno.json(),
          resAnimal.json(),
        ]);

        setMunicipiosOptions([
          { label: "Todos", value: "" },
          ...munData.map((m) => ({ label: m.nome, value: m.nome })),
        ]);
        setAnosOptions(
          anosData.map((item) => ({ label: String(item.ano), value: item.ano }))
        );
        setAnimaisOptions(
          animaisData.map((a) => ({ label: a.nome, value: a.nome }))
        );
      } catch (e) {
        console.error(e);
      }
    };
    fetchFilters();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const params = new URLSearchParams();
        if (debouncedFilters.municipio)
          params.append("municipio", debouncedFilters.municipio);
        debouncedFilters.anos.forEach((ano) => params.append("anos", ano));
        debouncedFilters.animais.forEach((animal) =>
          params.append("animais", animal)
        );

        const res = await fetch(
          `http://localhost:8000/dashboard/resumo?${params.toString()}`,
          { signal: controller.signal }
        );
        if (!res.ok) throw new Error("Falha ao buscar dados do dashboard");

        const data = await res.json();

        setMetrics(data.metrics);
        setChartData(
          (data.casosPorAno ?? []).map((item) => ({
            name: String(item.ano),
            casos: item.total_acidentes,
          }))
        );
        setSeverityData(
          (data.gravidade ?? []).map((item) => ({
            name: item.classificacao,
            casos: item.total_acidentes,
          }))
        );

        const dist = (data.distAnimal ?? [])
          .map((item) => ({
            name: item.animal_tipo,
            value: item.total_acidentes,
          }))
          .sort((a, b) => b.value - a.value);
        if (dist.length > 6) {
          setAnimalData([
            ...dist.slice(0, 5),
            {
              name: "Outros",
              value: dist
                .slice(5)
                .reduce((acc, cur) => acc + (cur.value ?? 0), 0),
            },
          ]);
        } else {
          setAnimalData(dist);
        }

        setLastUpdated(new Date());
      } catch (err) {
        if (err?.name === "AbortError") return;
        setError("Erro ao carregar dados. Tente novamente mais tarde.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    return () => controller.abort();
  }, [debouncedFilters, refreshTick]);

  // --- Handlers ---
  const handleMunicipioChange = (e) =>
    setFilters((prev) => ({ ...prev, municipio: e.target.value }));
  const handleAnosChange = (arg) =>
    setFilters((prev) => ({
      ...prev,
      anos: Array.isArray(arg) ? arg : (arg?.target?.value ?? []),
    }));
  const handleAnimaisChange = (arg) =>
    setFilters((prev) => ({
      ...prev,
      animais: Array.isArray(arg) ? arg : (arg?.target?.value ?? []),
    }));
  const handleRefresh = () => {
    setDebouncedFilters(filters);
    setRefreshTick((t) => t + 1);
  };
  const resetFilters = () =>
    setFilters({ municipio: "", anos: [], animais: [] });
  const scrollToFilters = () =>
    filterRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });

  const removeChip = (key) => {
    if (key === "mun") setFilters((p) => ({ ...p, municipio: "" }));
    if (key === "anos") setFilters((p) => ({ ...p, anos: [] }));
    if (key === "animais") setFilters((p) => ({ ...p, animais: [] }));
  };

  const exportCsv = () => {
    const lines = [
      "Resumo",
      `Total de casos,${metrics.totalCasos}`,
      `Taxa de óbitos,${metrics.taxaObitos}`,
      `Tempo médio (h),${metrics.tempoAtendimento}`,
      "",
      "Evolução anual",
      "Ano,Casos",
      ...chartData.map((r) => `${r.name},${r.casos}`),
      "",
      "Por tipo de animal",
      "Animal,Casos",
      ...animalData.map((r) => `${r.name},${r.value}`),
      "",
      "Gravidade",
      "Classificação,Casos",
      ...severityData.map((r) => `${r.name},${r.casos}`),
    ];
    const blob = new Blob([lines.join("\n")], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "dashboard.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <Header />
      <main className={styles.main}>
        <div className={styles.container}>
          <header className={styles.pageHeader}>
            <div>
              <h1 className={styles.title}>Dashboard</h1>
              <p className={styles.subtitle}>
                Acompanhe os casos, perfil e gravidade na sua região.
              </p>
              <div className={styles.subMeta}>
                <span className={styles.metaLabel}>Atualizado às:</span>{" "}
                <span className={styles.metaValue}>{lastUpdatedText}</span>
              </div>
            </div>
            <div className={styles.headerActions}>
              <button
                className={styles.secondaryButton}
                onClick={exportCsv}
                disabled={loading}
              >
                Exportar CSV
              </button>
              <button
                className={styles.primaryButton}
                onClick={handleRefresh}
                disabled={loading}
              >
                {loading ? "Atualizando..." : "Atualizar"}
              </button>
            </div>
          </header>

          <section className={styles.filterBar} ref={filterRef}>
            <div className={styles.filterTop}>
              <div className={styles.sectionTitle}>Filtros</div>
              <button
                className={styles.secondaryButton}
                onClick={resetFilters}
                disabled={loading || activeChips.length === 0}
              >
                Limpar tudo
              </button>
            </div>
            {activeChips.length > 0 && (
              <div className={styles.chipsRow}>
                {activeChips.map((chip) => (
                  <button
                    key={chip.key}
                    className={styles.filterChip}
                    onClick={() => removeChip(chip.key)}
                  >
                    <span className={styles.chipLabel}>{chip.label}</span>
                    <span className={styles.chipX}>×</span>
                  </button>
                ))}
              </div>
            )}
            <form className={styles.formBox}>
              <div className={styles.formGrid}>
                <UiSelect
                  label="Município"
                  value={filters.municipio}
                  onChange={handleMunicipioChange}
                  options={municipiosOptions}
                  placeholder={
                    municipiosOptions.length === 0
                      ? "Carregando..."
                      : "Selecione o município"
                  }
                />
                <UiMultiSelect
                  label="Anos"
                  options={anosOptions}
                  values={filters.anos}
                  onChange={handleAnosChange}
                  placeholder="Todos os anos"
                />
                <UiMultiSelect
                  label="Animais"
                  options={animaisOptions}
                  values={filters.animais}
                  onChange={handleAnimaisChange}
                  placeholder="Todos os animais"
                />
              </div>
            </form>
          </section>

          <section className={styles.metricsSectionWrapper}>
            <div className={styles.sectionHeading}>
              <h2 className={styles.sectionHeadingTitle}>Indicadores</h2>
              <p className={styles.sectionHeadingSubtitle}>
                Resumo consolidado do recorte selecionado.
              </p>
            </div>
            <div className={styles.metricsSection}>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Total de casos</div>
                <div className={styles.metricValue}>
                  {nfInt.format(metrics.totalCasos)}
                </div>
                <div className={styles.metricHint}>
                  acumulado no filtro atual
                </div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Taxa de óbitos</div>
                <div className={styles.metricValue}>
                  {nf2.format(metrics.taxaObitos)}%
                </div>
                <div className={styles.metricHint}>
                  proporção no filtro atual
                </div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Tempo médio</div>
                <div className={styles.metricValue}>
                  {nf1.format(metrics.tempoAtendimento)} h
                </div>
                <div className={styles.metricHint}>atendimento (horas)</div>
              </div>
            </div>
          </section>

          {loading && (
            <section className={styles.skeletonGrid}>
              <div className={styles.skeletonCard} />
              <div className={styles.skeletonCard} />
              <div className={styles.skeletonCardWide} />
            </section>
          )}

          {error && <p className={styles.error}>{error}</p>}

          {isEmpty && (
            <section className={styles.emptyState}>
              <div className={styles.emptyIcon}>
                <FaFolderOpen />
              </div>
              <h3 className={styles.emptyTitle}>
                {activeChips.length > 0
                  ? "Nenhum caso com os filtros atuais"
                  : "Nenhum caso encontrado"}
              </h3>
              <p className={styles.emptyText}>
                Ajuste o recorte para encontrar resultados.
              </p>
              <div className={styles.emptyActions}>
                <button className={styles.primaryButton} onClick={resetFilters}>
                  Limpar tudo
                </button>
                <button
                  className={styles.secondaryButton}
                  onClick={scrollToFilters}
                >
                  Ajustar filtros
                </button>
              </div>
            </section>
          )}

          {!loading && !error && !isEmpty && (
            <section className={styles.chartsWrapper}>
              <div className={styles.chartsGrid}>
                <div className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3 className={styles.cardTitle}>Evolução anual</h3>
                  </div>
                  <div className={styles.cardBody}>
                    <ResponsiveContainer width="100%" height={380}>
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient
                            id="colorCasos"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="5%"
                              stopColor="#2563eb"
                              stopOpacity={0.22}
                            />
                            <stop
                              offset="95%"
                              stopColor="#2563eb"
                              stopOpacity={0}
                            />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" />
                        <YAxis tickFormatter={(v) => nfInt.format(v)} />
                        <Tooltip
                          {...tooltipProps}
                          formatter={(v) => nfInt.format(v)}
                        />
                        <Area
                          type="monotone"
                          dataKey="casos"
                          stroke="#2563eb"
                          fill="url(#colorCasos)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3 className={styles.cardTitle}>Por tipo de animal</h3>
                  </div>
                  <div className={styles.cardBody}>
                    <ResponsiveContainer width="100%" height={380}>
                      <PieChart>
                        <Pie
                          data={animalData}
                          cx="50%"
                          cy="50%"
                          innerRadius={84}
                          outerRadius={128}
                          paddingAngle={3}
                          dataKey="value"
                        >
                          {animalData.map((_, index) => (
                            <Cell
                              key={index}
                              fill={COLORS[index % COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          {...tooltipProps}
                          formatter={(v) => nfInt.format(v)}
                        />
                        <Legend verticalAlign="bottom" iconType="circle" />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className={`${styles.card} ${styles.chartFull}`}>
                  <div className={styles.cardHeader}>
                    <h3 className={styles.cardTitle}>Gravidade dos casos</h3>
                  </div>
                  <div className={styles.cardBody}>
                    <ResponsiveContainer width="100%" height={320}>
                      <BarChart data={severityData} layout="vertical">
                        <CartesianGrid
                          strokeDasharray="3 3"
                          horizontal={false}
                        />
                        <XAxis
                          type="number"
                          tickFormatter={(v) => nfInt.format(v)}
                        />
                        <YAxis type="category" dataKey="name" width={110} />
                        <Tooltip
                          {...tooltipProps}
                          formatter={(v) => nfInt.format(v)}
                        />
                        <Bar
                          dataKey="casos"
                          fill="#f97316"
                          radius={[0, 10, 10, 0]}
                          barSize={50}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </section>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}
