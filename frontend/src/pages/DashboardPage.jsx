import React, { useEffect, useMemo, useRef, useState } from "react";

import Header from "../components/Header";
import Footer from "../components/Footer";
import UiSelect from "../components/UiSelect";
import UiMultiSelect from "../components/UiMultiSelect";
import styles from "./styles/DashboardPage.module.css";
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

const COLORS = [
  "#2563eb",
  "#16a34a",
  "#f97316",
  "#db2777",
  "#7c3aed",
  "#0891b2",
  "#64748b", // "Outros"
];

function formatListPreview(items, max = 3) {
  if (!items || items.length === 0) return "";
  const head = items.slice(0, max).join(", ");
  const rest = items.length - max;
  return rest > 0 ? `${head} +${rest}` : head;
}

export default function DashboardPage() {
  const [filters, setFilters] = useState({
    municipio: "",
    anos: [],
    animais: [],
  });

  // debounce para evitar “piscar”/fetch a cada clique rápido
  const [debouncedFilters, setDebouncedFilters] = useState(filters);
  const [refreshTick, setRefreshTick] = useState(0);

  const [metrics, setMetrics] = useState({
    totalCasos: 0,
    taxaObitos: 0,
    tempoAtendimento: 0,
  });

  const [chartData, setChartData] = useState([]);
  const [animalData, setAnimalData] = useState([]);
  const [severityData, setSeverityData] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [municipiosOptions, setMunicipiosOptions] = useState([]);
  const [anosOptions, setAnosOptions] = useState([]);
  const [animaisOptions, setAnimaisOptions] = useState([]);

  const [lastUpdated, setLastUpdated] = useState(null);

  // ---- formatadores (PT-BR)
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

  const filterRef = useRef(null);

  const scrollToFilters = () => {
    filterRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  useEffect(() => {
    const t = setTimeout(() => setDebouncedFilters(filters), 420);
    return () => clearTimeout(t);
  }, [filters]);

  const resetFilters = () => {
    setFilters({ municipio: "", anos: [], animais: [] });
  };

  const removeChip = (key) => {
    if (key === "mun") setFilters((p) => ({ ...p, municipio: "" }));
    if (key === "anos") setFilters((p) => ({ ...p, anos: [] }));
    if (key === "animais") setFilters((p) => ({ ...p, animais: [] }));
  };

  const activeChips = useMemo(() => {
    const chips = [];
    if (filters.municipio) {
      chips.push({
        key: "mun",
        label: `Município: ${filters.municipio}`,
      });
    }
    if (filters.anos.length > 0) {
      chips.push({
        key: "anos",
        label: `Anos: ${formatListPreview(filters.anos.map(String))}`,
      });
    }
    if (filters.animais.length > 0) {
      chips.push({
        key: "animais",
        label: `Animais: ${formatListPreview(filters.animais)}`,
      });
    }
    return chips;
  }, [filters]);

  const isEmpty =
    !loading &&
    !error &&
    Number(metrics.totalCasos ?? 0) === 0 &&
    (chartData?.length ?? 0) === 0;

  // ======== CHAMADA DE API: FILTROS ========
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
          label: String(item.ano),
          value: item.ano,
        }));
        const optionsAnimais = animaisData.map((a) => ({
          label: a.nome,
          value: a.nome,
        }));

        setMunicipiosOptions([{ label: "Todos", value: "" }, ...optionsMun]);
        setAnosOptions(optionsAno);
        setAnimaisOptions(optionsAnimais);
      } catch (e) {
        console.error(e);
      }
    };

    fetchFilters();
  }, []);

  // ======== BUSCAR MÉTRICAS / GRÁFICOS (com AbortController) ========
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

        const queryString = params.toString();
        const url = queryString
          ? `http://localhost:8000/dashboard/resumo?${queryString}`
          : "http://localhost:8000/dashboard/resumo";

        const res = await fetch(url, { signal: controller.signal });
        if (!res.ok) throw new Error("Falha ao buscar dados do dashboard");

        const data = await res.json();

        setMetrics({
          totalCasos: data.metrics.totalCasos,
          taxaObitos: data.metrics.taxaObitos,
          tempoAtendimento: data.metrics.tempoAtendimento,
        });

        setChartData(
          (data.casosPorAno ?? []).map((item) => ({
            name: String(item.ano),
            casos: item.total_acidentes,
          }))
        );

        // Top 5 + Outros
        const dist = (data.distAnimal ?? [])
          .map((item) => ({
            name: item.animal_tipo,
            value: item.total_acidentes,
          }))
          .sort((a, b) => b.value - a.value);

        if (dist.length > 6) {
          const top = dist.slice(0, 5);
          const rest = dist
            .slice(5)
            .reduce((acc, cur) => acc + (cur.value ?? 0), 0);
          setAnimalData([...top, { name: "Outros", value: rest }]);
        } else {
          setAnimalData(dist);
        }

        setSeverityData(
          (data.gravidade ?? []).map((item) => ({
            name: item.classificacao,
            casos: item.total_acidentes,
          }))
        );

        setLastUpdated(new Date());
      } catch (err) {
        if (err?.name === "AbortError") return; // troca de filtro rápida, cancela request anterior
        console.error(err);
        setError("Erro ao carregar dados. Tente novamente mais tarde.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    return () => controller.abort();
  }, [debouncedFilters, refreshTick]);

  // ======== HANDLERS ========
  const handleMunicipioChange = (e) => {
    setFilters((prev) => ({ ...prev, municipio: e.target.value }));
  };

  const handleAnosChange = (arg) => {
    const novosAnos = Array.isArray(arg) ? arg : arg?.target?.value ?? [];
    setFilters((prev) => ({ ...prev, anos: novosAnos }));
  };

  const handleAnimaisChange = (arg) => {
    const novosAnimais = Array.isArray(arg) ? arg : arg?.target?.value ?? [];
    setFilters((prev) => ({ ...prev, animais: novosAnimais }));
  };

  const handleRefresh = () => {
    setDebouncedFilters(filters); // busca imediata (sem esperar debounce)
    setRefreshTick((t) => t + 1);
  };

  const exportCsv = () => {
    // CSV simples (3 seções)
    const lines = [];
    lines.push("Resumo");
    lines.push(`Total de casos,${metrics.totalCasos ?? 0}`);
    lines.push(`Taxa de óbitos,${metrics.taxaObitos ?? 0}`);
    lines.push(`Tempo médio (h),${metrics.tempoAtendimento ?? 0}`);
    lines.push("");

    lines.push("Evolução anual");
    lines.push("Ano,Casos");
    chartData.forEach((r) => lines.push(`${r.name},${r.casos}`));
    lines.push("");

    lines.push("Por tipo de animal");
    lines.push("Animal,Casos");
    animalData.forEach((r) => lines.push(`${r.name},${r.value}`));
    lines.push("");

    lines.push("Gravidade dos casos");
    lines.push("Classificação,Casos");
    severityData.forEach((r) => lines.push(`${r.name},${r.casos}`));

    const csv = lines.join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "dashboard.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const tooltipProps = {
    contentStyle: { borderRadius: 12, border: "1px solid #e5e7eb" },
    labelStyle: { fontWeight: 600 },
    cursor: { fill: "transparent" },
  };

  const lastUpdatedText = useMemo(() => {
    if (!lastUpdated) return "—";
    return lastUpdated.toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }, [lastUpdated]);

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
                type="button"
                className={styles.secondaryButton}
                onClick={exportCsv}
                disabled={loading}
              >
                Exportar CSV
              </button>
              <button
                type="button"
                className={styles.primaryButton}
                onClick={handleRefresh}
                disabled={loading}
              >
                {loading ? "Atualizando..." : "Atualizar"}
              </button>
            </div>
          </header>

          {/* === FILTROS === */}
          <section className={styles.filterBar} ref={filterRef}>
            <div className={styles.filterTop}>
              <div className={styles.sectionTitle}>Filtros</div>

              <button
                type="button"
                className={styles.secondaryButton}
                onClick={resetFilters}
                disabled={loading || activeChips.length === 0}
              >
                Limpar tudo
              </button>
            </div>

            {activeChips.length > 0 && (
              <div className={styles.chipsRow} aria-label="Filtros ativos">
                {activeChips.map((chip) => (
                  <button
                    key={chip.key}
                    type="button"
                    className={styles.filterChip}
                    onClick={() => removeChip(chip.key)}
                    title="Remover filtro"
                  >
                    <span className={styles.chipLabel}>{chip.label}</span>
                    <span className={styles.chipX} aria-hidden="true">
                      ×
                    </span>
                  </button>
                ))}
              </div>
            )}

            <form className={styles.formBox}>
              <div className={styles.formGrid}>
                <div className={styles.fieldGroup}>
                  <UiSelect
                    label="Município"
                    name="municipio"
                    value={filters.municipio}
                    onChange={handleMunicipioChange}
                    placeholder={
                      municipiosOptions.length === 0
                        ? "Carregando municípios..."
                        : "Selecione o município"
                    }
                    options={municipiosOptions}
                  />
                </div>

                <div className={styles.fieldGroup}>
                  <UiMultiSelect
                    label="Anos"
                    name="anos"
                    options={anosOptions}
                    values={filters.anos}
                    onChange={handleAnosChange}
                    placeholder="Todos os anos"
                  />
                </div>

                <div className={styles.fieldGroup}>
                  <UiMultiSelect
                    label="Animais"
                    name="animais"
                    options={animaisOptions}
                    values={filters.animais}
                    onChange={handleAnimaisChange}
                    placeholder="Todos os animais"
                  />
                </div>
              </div>
            </form>
          </section>

          {/* === MÉTRICAS === */}
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
                  {nfInt.format(metrics.totalCasos ?? 0)}
                </div>
                <div className={styles.metricHint}>
                  acumulado no filtro atual
                </div>
              </div>

              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Taxa de óbitos</div>
                <div className={styles.metricValue}>
                  {nf2.format(metrics.taxaObitos ?? 0)}%
                </div>
                <div className={styles.metricHint}>
                  proporção no filtro atual
                </div>
              </div>

              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Tempo médio</div>
                <div className={styles.metricValue}>
                  {nf1.format(metrics.tempoAtendimento ?? 0)} h
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
            <section
              className={styles.emptyState}
              role="status"
              aria-live="polite"
            >
              <div className={styles.emptyIcon} aria-hidden="true">
                <FaFolderOpen />
              </div>

              <h3 className={styles.emptyTitle}>
                {activeChips.length > 0
                  ? "Nenhum caso com os filtros atuais"
                  : "Nenhum caso encontrado"}
              </h3>

              <p className={styles.emptyText}>
                {activeChips.length > 0
                  ? "Remova um filtro abaixo ou ajuste o recorte para encontrar resultados."
                  : "Selecione outro município ou anos para ver resultados."}
              </p>

              {activeChips.length > 0 && (
                <>
                  <div
                    className={styles.emptyChips}
                    aria-label="Filtros ativos"
                  >
                    {activeChips.map((chip) => (
                      <button
                        key={chip.key}
                        type="button"
                        className={styles.filterChip}
                        onClick={() => removeChip(chip.key)}
                        title="Remover filtro"
                      >
                        <span className={styles.chipLabel}>{chip.label}</span>
                        <span className={styles.chipX} aria-hidden="true">
                          ×
                        </span>
                      </button>
                    ))}
                  </div>

                  <p className={styles.emptyHint}>
                    Dica: clique em um filtro para removê-lo.
                  </p>
                </>
              )}

              <div className={styles.emptyActions}>
                <button
                  type="button"
                  className={styles.primaryButton}
                  onClick={resetFilters}
                  disabled={loading}
                >
                  Limpar tudo
                </button>

                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={scrollToFilters}
                  disabled={loading}
                >
                  Ajustar filtros
                </button>
              </div>
            </section>
          )}

          {!loading && !error && !isEmpty && (
            <section className={styles.chartsWrapper}>
              <div className={styles.sectionHeading}>
                <h2 className={styles.sectionHeadingTitle}>Análises</h2>
                <p className={styles.sectionHeadingSubtitle}>
                  Visão detalhada da evolução, distribuição e gravidade dos
                  casos.
                </p>
              </div>

              <div className={styles.chartsGrid}>
                <div className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3 className={styles.cardTitle}>Evolução anual</h3>
                    <p className={styles.cardSubtitle}>
                      Histórico de casos registrados por ano.
                    </p>
                  </div>

                  <div className={styles.cardBody}>
                    {chartData.length === 0 ? (
                      <div className={styles.inlineEmpty}>
                        Sem dados para este recorte.
                      </div>
                    ) : (
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
                          <CartesianGrid
                            strokeDasharray="3 3"
                            vertical={false}
                          />
                          <XAxis dataKey="name" tickMargin={8} />
                          <YAxis tickFormatter={(v) => nfInt.format(v)} />
                          <Tooltip
                            {...tooltipProps}
                            formatter={(v) => nfInt.format(v)}
                          />
                          <Area
                            type="monotone"
                            dataKey="casos"
                            stroke="#2563eb"
                            strokeWidth={2}
                            fillOpacity={1}
                            fill="url(#colorCasos)"
                            activeDot={{ r: 6 }}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>

                <div className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3 className={styles.cardTitle}>Por tipo de animal</h3>
                    <p className={styles.cardSubtitle}>
                      Quantidade de acidentes por espécie.
                    </p>
                  </div>

                  <div className={styles.cardBody}>
                    {animalData.length === 0 ? (
                      <div className={styles.inlineEmpty}>
                        Sem dados para este recorte.
                      </div>
                    ) : (
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
                                key={`cell-${index}`}
                                fill={COLORS[index % COLORS.length]}
                              />
                            ))}
                          </Pie>
                          <Tooltip
                            {...tooltipProps}
                            formatter={(v) => nfInt.format(v)}
                          />
                          <Legend
                            verticalAlign="bottom"
                            align="center"
                            iconType="circle"
                            wrapperStyle={{ paddingTop: 8 }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>

                {/* 3º gráfico: barras horizontais e largura total */}
                <div className={`${styles.card} ${styles.chartFull}`}>
                  <div className={styles.cardHeader}>
                    <h3 className={styles.cardTitle}>Gravidade dos casos</h3>
                    <p className={styles.cardSubtitle}>
                      Classificação clínica dos acidentes
                    </p>
                  </div>

                  <div className={styles.cardBody}>
                    {severityData.length === 0 ? (
                      <div className={styles.inlineEmpty}>
                        Sem dados para este recorte.
                      </div>
                    ) : (
                      <ResponsiveContainer width="100%" height={320}>
                        <BarChart
                          data={severityData}
                          layout="vertical"
                          margin={{ top: 6, right: 24, left: 24, bottom: 6 }}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            horizontal={false}
                          />
                          <XAxis
                            type="number"
                            tickFormatter={(v) => nfInt.format(v)}
                          />
                          <YAxis
                            type="category"
                            dataKey="name"
                            width={110}
                            tickMargin={8}
                          />
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
                    )}
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
