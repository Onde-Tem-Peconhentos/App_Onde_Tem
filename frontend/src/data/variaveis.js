export const COVARIAVEIS = {
  populacao: {
    sigla: "POP",
    descricao: "População residente no município."
  },
  
  altitude: {
    sigla: "ALT",
    descricao: "Altitude média do município, em metros (m)."
  },

  superficie_vegetal2020: {
    sigla: "SUPVEG",
    descricao: "Superfície coberta por vegetação em 2020."
  },

  vegetacao2020: {
    sigla: "VEG",
    descricao: "Tipo de vegetação predominante no município em 2020."
  },

  percentual_vegetacao: {
    sigla: "PERCVEG",
    descricao: "Percentual do território municipal coberto por vegetação."
  },

  area_km2: {
    sigla: "AREA",
    descricao: "Área total do município em quilômetros quadrados (km²)."
  },

  percentual_homens: {
    sigla: "PERCHOM",
    descricao: "Percentual da população masculina no município."
  },

  idhm_renda2010: {
    sigla: "IDHMREN",
    descricao: "Índice de Desenvolvimento Humano Municipal - Renda (2010)."
  },

  idhm_saude2010: {
    sigla: "IDHMSAU",
    descricao: "Índice de Desenvolvimento Humano Municipal - Saúde (2010)."
  },

  idhm_educacao2010: {
    sigla: "IDHMEDU",
    descricao: "Índice de Desenvolvimento Humano Municipal - Educação (2010)."
  },

  idhm_2010: {
    sigla: "IDHM",
    descricao: "Índice de Desenvolvimento Humano Municipal (2010)."
  },

  pop_rural: {
    sigla: "POPRUR",
    descricao: "População residente em zona rural."
  },

  pop_urbana: {
    sigla: "POPURB",
    descricao: "População residente em zona urbana."
  },

  pib2021: {
    sigla: "PIB",
    descricao: "Produto Interno Bruto do município em 2021."
  },

  n_favelas: {
    sigla: "NFVL",
    descricao: "Número de favelas no município."
  },

  pop_favelas: {
    sigla: "POPFVL",
    descricao: "População residente em favelas."
  },

  apartamento: {
    sigla: "APT",
    descricao: "Quantidade de domicílios do tipo apartamento."
  },

  casa: {
    sigla: "CSA",
    descricao: "Quantidade de domicílios do tipo casa."
  },

  vila_condominio: {
    sigla: "VILCOND",
    descricao: "Quantidade de domicílios do tipo vila/condomínio."
  },

  total_moradia: {
    sigla: "TOTMOR",
    descricao: "Total de domicílios particulares permanentes."
  },

  temp: {
    sigla: "TEMP",
    descricao: "Temperatura média mensal (°C)."
  },

  prec: {
    sigla: "PREC",
    descricao: "Precipitação acumulada mensal (mm)."
  },

  umid: {
    sigla: "UMID",
    descricao: "Umidade relativa média mensal (%)."
  },

  press: {
    sigla: "PRESS",
    descricao: "Pressão atmosférica média mensal (hPa)."
  },

  rad: {
    sigla: "RAD",
    descricao: "Radiação solar global média diária (MJ/m²/dia)."
  },

  tmax: {
    sigla: "TMAX",
    descricao: "Temperatura máxima média mensal (°C)."
  },

  tmin: {
    sigla: "TMIN",
    descricao: "Temperatura mínima média mensal (°C)."
  },

  umax: {
    sigla: "UMAX",
    descricao: "Umidade relativa máxima média mensal (%)."
  },

  umin: {
    sigla: "UMIN",
    descricao: "Umidade relativa mínima média mensal (%)."
  },

  tamp: {
    sigla: "TAMP",
    descricao: "Amplitude térmica média diária (°C)."
  },

  uamp: {
    sigla: "UAMP",
    descricao: "Amplitude da umidade relativa diária (%)."
  },

  log_prec: {
    sigla: "LOGPREC",
    descricao: "Logaritmo natural da precipitação acumulada mensal."
  },

  log_rad: {
    sigla: "LOGRAD",
    descricao: "Logaritmo natural da radiação solar global média."
  },

  // Lags de Precipitação
  prec_l1: {
    sigla: "PRECL1",
    descricao: "Precipitação acumulada no mês anterior (lag 1)."
  },
  prec_l2: {
    sigla: "PRECL2",
    descricao: "Precipitação acumulada dois meses antes (lag 2)."
  },
  prec_l3: {
    sigla: "PRECL3",
    descricao: "Precipitação acumulada três meses antes (lag 3)."
  },

  // Médias Móveis de Precipitação
  prec_m3: {
    sigla: "PRECM3",
    descricao: "Média móvel de 3 meses da precipitação acumulada."
  },
  prec_m6: {
    sigla: "PRECM6",
    descricao: "Média móvel de 6 meses da precipitação acumulada."
  },
  prec_m12: {
    sigla: "PRECM12",
    descricao: "Média móvel de 12 meses da precipitação acumulada."
  },

  // Diferenças de Precipitação
  prec_d1: {
    sigla: "PRECD1",
    descricao: "Diferença da precipitação em relação ao mês anterior."
  },
  prec_d3: {
    sigla: "PRECD3",
    descricao: "Diferença da precipitação em relação à média dos últimos 3 meses."
  },

  // Anomalias de Precipitação
  prec_ae: {
    sigla: "PRECAE",
    descricao: "Anomalia de precipitação em relação à média histórica do mês."
  },
  prec_ze: {
    sigla: "PREC",
    descricao: "Precipitação."
  },
  prec_ac: {
    sigla: "PRECAC",
    descricao: "Acumulado anual da precipitação."
  },

  // Log das versões de precipitação
  log_prec_l1: {
    sigla: "LOGPRECL1",
    descricao: "Logaritmo natural da precipitação acumulada no mês anterior."
  },
  log_prec_l2: {
    sigla: "LOGPRECL2",
    descricao: "Logaritmo natural da precipitação acumulada dois meses antes."
  },
  log_prec_l3: {
    sigla: "LOGPRECL3",
    descricao: "Logaritmo natural da precipitação acumulada três meses antes."
  },
  log_prec_m3: {
    sigla: "LOGPRECM3",
    descricao: "Logaritmo natural da média móvel de 3 meses da precipitação."
  },
  log_prec_m6: {
    sigla: "LOGPRECM6",
    descricao: "Logaritmo natural da média móvel de 6 meses da precipitação."
  },
  log_prec_m12: {
    sigla: "LOGPRECM12",
    descricao: "Logaritmo natural da média móvel de 12 meses da precipitação."
  },
  log_prec_d1: {
    sigla: "LOGPRECD1",
    descricao: "Logaritmo natural da diferença da precipitação em relação ao mês anterior."
  },
  log_prec_d3: {
    sigla: "LOGPRECD3",
    descricao: "Logaritmo natural da diferença da precipitação em relação à média dos últimos 3 meses."
  },
  log_prec_ae: {
    sigla: "LOGPRECAE",
    descricao: "Logaritmo natural da anomalia de precipitação."
  },
  log_prec_ze: {
    sigla: "LOGPRECZE",
    descricao: "Logaritmo natural do Z-score da precipitação."
  },
  log_prec_ac: {
    sigla: "LOGPRECAC",
    descricao: "Logaritmo natural do acumulado anual da precipitação."
  },

  // Lags de Temperatura
  temp_l1: {
    sigla: "TEMPL1",
    descricao: "Temperatura média no mês anterior (lag 1)."
  },
  temp_l2: {
    sigla: "TEMPL2",
    descricao: "Temperatura média dois meses antes (lag 2)."
  },
  temp_l3: {
    sigla: "TEMPL3",
    descricao: "Temperatura média três meses antes (lag 3)."
  },

  // Médias Móveis de Temperatura
  temp_m3: {
    sigla: "TEMPM3",
    descricao: "Média móvel de 3 meses da temperatura média."
  },
  temp_m6: {
    sigla: "TEMPM6",
    descricao: "Média móvel de 6 meses da temperatura média."
  },
  temp_m12: {
    sigla: "TEMPM12",
    descricao: "Média móvel de 12 meses da temperatura média."
  },

  // Diferenças de Temperatura
  temp_d1: {
    sigla: "TEMPD1",
    descricao: "Diferença da temperatura em relação ao mês anterior."
  },
  temp_d3: {
    sigla: "TEMPD3",
    descricao: "Diferença da temperatura em relação à média dos últimos 3 meses."
  },

  // Anomalias de Temperatura
  temp_ae: {
    sigla: "TEMPAE",
    descricao: "Anomalia de temperatura em relação à média histórica do mês."
  },
  temp_ze: {
    sigla: "TEMPZE",
    descricao: "Padronização Z-score da temperatura."
  },
  temp_ac: {
    sigla: "TEMPAC",
    descricao: "Acumulado anual da temperatura média."
  },

  // Médias de Temperatura Máxima
  tmax_m3: {
    sigla: "TMAXM3",
    descricao: "Média móvel de 3 meses da temperatura máxima média."
  },
  tmax_m6: {
    sigla: "TMAXM6",
    descricao: "Média móvel de 6 meses da temperatura máxima média."
  },
  tmax_ac: {
    sigla: "TMAXAC",
    descricao: "Acumulado anual da temperatura máxima média."
  },
  tmax_ae: {
    sigla: "TMAXAE",
    descricao: "Anomalia da temperatura máxima em relação à média histórica do mês."
  },

  // Médias de Temperatura Mínima
  tmin_m3: {
    sigla: "TMINM3",
    descricao: "Média móvel de 3 meses da temperatura mínima média."
  },
  tmin_m6: {
    sigla: "TMINM6",
    descricao: "Média móvel de 6 meses da temperatura mínima média."
  },
  tmin_ac: {
    sigla: "TMINAC",
    descricao: "Acumulado anual da temperatura mínima média."
  },
  tmin_ae: {
    sigla: "TMINAE",
    descricao: "Anomalia da temperatura mínima em relação à média histórica do mês."
  },

  // Amplitude Térmica
  tamp_l1: {
    sigla: "TAMPL1",
    descricao: "Amplitude térmica média no mês anterior (lag 1)."
  },
  tamp_l2: {
    sigla: "TAMPL2",
    descricao: "Amplitude térmica média dois meses antes (lag 2)."
  },
  tamp_l3: {
    sigla: "TAMPL3",
    descricao: "Amplitude térmica média três meses antes (lag 3)."
  },
  tamp_m3: {
    sigla: "TAMPM3",
    descricao: "Média móvel de 3 meses da amplitude térmica média."
  },
  tamp_m6: {
    sigla: "TAMPM6",
    descricao: "Média móvel de 6 meses da amplitude térmica média."
  },
  tamp_m12: {
    sigla: "TAMPM12",
    descricao: "Média móvel de 12 meses da amplitude térmica média."
  },
  tamp_d1: {
    sigla: "TAMPD1",
    descricao: "Diferença da amplitude térmica em relação ao mês anterior."
  },
  tamp_d3: {
    sigla: "TAMPD3",
    descricao: "Diferença da amplitude térmica em relação à média dos últimos 3 meses."
  },
  tamp_ae: {
    sigla: "TAMPAE",
    descricao: "Anomalia da amplitude térmica em relação à média histórica do mês."
  },
  tamp_ze: {
    sigla: "TAMPZE",
    descricao: "Padronização Z-score da amplitude térmica."
  },
  tamp_ac: {
    sigla: "TAMPAC",
    descricao: "Acumulado anual da amplitude térmica média."
  },

  // Umidade Relativa
  umid_l1: {
    sigla: "UMIDL1",
    descricao: "Umidade relativa média no mês anterior (lag 1)."
  },
  umid_l2: {
    sigla: "UMIDL2",
    descricao: "Umidade relativa média dois meses antes (lag 2)."
  },
  umid_l3: {
    sigla: "UMIDL3",
    descricao: "Umidade relativa média três meses antes (lag 3)."
  },
  umid_m3: {
    sigla: "UMIDM3",
    descricao: "Média móvel de 3 meses da umidade relativa média."
  },
  umid_m6: {
    sigla: "UMIDM6",
    descricao: "Média móvel de 6 meses da umidade relativa média."
  },
  umid_m12: {
    sigla: "UMIDM12",
    descricao: "Média móvel de 12 meses da umidade relativa média."
  },
  umid_d1: {
    sigla: "UMIDD1",
    descricao: "Diferença da umidade relativa em relação ao mês anterior."
  },
  umid_d3: {
    sigla: "UMIDD3",
    descricao: "Diferença da umidade relativa em relação à média dos últimos 3 meses."
  },
  umid_ae: {
    sigla: "UMIDAE",
    descricao: "Anomalia da umidade relativa em relação à média histórica do mês."
  },
  umid_ze: {
    sigla: "UMIDZE",
    descricao: "Padronização Z-score da umidade relativa."
  },
  umid_ac: {
    sigla: "UMIDAC",
    descricao: "Acumulado anual da umidade relativa média."
  },

  // Amplitude da Umidade Relativa
  uamp_l1: {
    sigla: "UAMPL1",
    descricao: "Amplitude da umidade relativa no mês anterior (lag 1)."
  },
  uamp_l2: {
    sigla: "UAMPL2",
    descricao: "Amplitude da umidade relativa dois meses antes (lag 2)."
  },
  uamp_l3: {
    sigla: "UAMPL3",
    descricao: "Amplitude da umidade relativa três meses antes (lag 3)."
  },
  uamp_m3: {
    sigla: "UAMPM3",
    descricao: "Média móvel de 3 meses da amplitude da umidade relativa."
  },
  uamp_m6: {
    sigla: "UAMPM6",
    descricao: "Média móvel de 6 meses da amplitude da umidade relativa."
  },
  uamp_m12: {
    sigla: "UAMPM12",
    descricao: "Média móvel de 12 meses da amplitude da umidade relativa."
  },
  uamp_d1: {
    sigla: "UAMPD1",
    descricao: "Diferença da amplitude da umidade relativa em relação ao mês anterior."
  },
  uamp_d3: {
    sigla: "UAMPD3",
    descricao: "Diferença da amplitude da umidade relativa em relação à média dos últimos 3 meses."
  },
  uamp_ae: {
    sigla: "UAMPAE",
    descricao: "Anomalia da amplitude da umidade relativa em relação à média histórica do mês."
  },
  uamp_ze: {
    sigla: "UAMPZE",
    descricao: "Padronização Z-score da amplitude da umidade relativa."
  },
  uamp_ac: {
    sigla: "UAMPAC",
    descricao: "Acumulado anual da amplitude da umidade relativa."
  },

  // Radiação Solar
  rad_l1: {
    sigla: "RADL1",
    descricao: "Radiação solar no mês anterior (lag 1)."
  },
  rad_m3: {
    sigla: "RAD_MM3",
    descricao: "Média móvel de 3 meses da radiação solar."
  },
  rad_m6: {
    sigla: "RAD_MM6",
    descricao: "Média móvel de 6 meses da radiação solar."
  },
  rad_ae: {
    sigla: "RAD_AE",
    descricao: "Anomalia da radiação solar em relação à média histórica do mês."
  },
  rad_ac: {
    sigla: "RAD_AC",
    descricao: "Acumulado anual da radiação solar."
  },

  // Log da Radiação Solar
  log_rad_l1: {
    sigla: "LOG_RAD_LAG1",
    descricao: "Logaritmo natural da radiação solar no mês anterior."
  },
  log_rad_m3: {
    sigla: "LOG_RAD_M3",
    descricao: "Logaritmo natural da média móvel de 3 meses da radiação solar."
  },
  log_rad_m6: {
    sigla: "LOG_RAD_M6",
    descricao: "Logaritmo natural da média móvel de 6 meses da radiação solar."
  },
  log_rad_ae: {
    sigla: "LOG_RAD_AE",
    descricao: "Logaritmo natural da anomalia da radiação solar."
  },
  log_rad_ac: {
    sigla: "LOG_RAD_AC",
    descricao: "Logaritmo natural do acumulado anual da radiação solar."
  },

  // Pressão Atmosférica
  press_l1: {
    sigla: "PRESS_LAG1",
    descricao: "Pressão atmosférica no mês anterior (lag 1)."
  },
  press_m3: {
    sigla: "PRESS_M3",
    descricao: "Média móvel de 3 meses da pressão atmosférica."
  },
  press_m6: {
    sigla: "PRESS_M6",
    descricao: "Média móvel de 6 meses da pressão atmosférica."
  },
  press_ae: {
    sigla: "PRESS_AE",
    descricao: "Anomalia da pressão atmosférica em relação à média histórica do mês."
  },
  press_ac: {
    sigla: "PRESS_AC",
    descricao: "Acumulado anual da pressão atmosférica."
  },

  // Variáveis Sazonais
  mes_sin: {
    sigla: "MES_SENO",
    descricao: "Seno do mês."
  },
  mes_cos: {
    sigla: "MES_COS",
    descricao: "Cosseno do mês."
  },

  // Variáveis Lagged do Target (Features do Modelo)
  y_lag1: {
    sigla: "YLAG1",
    descricao: "Número de ocorrências no mês anterior."
  },
  y_lag2: {
    sigla: "YLAG2",
    descricao: "Número de ocorrências dois meses antes."
  },

  // Médias Móveis do Target
  y_roll3: {
    sigla: "YMM3",
    descricao: "Média móvel de 3 meses do número de ocorrências."
  },
  y_roll6: {
    sigla: "YMM6",
    descricao: "Média móvel de 6 meses do número de ocorrências."
  },
  y_roll12: {
    sigla: "YMM12",
    descricao: "Média móvel de 12 meses do número de ocorrências."
  },

  // Média Histórica por Município
  media_hist_municipio: {
    sigla: "MEDIAHIST",
    descricao: "Média histórica de ocorrências para o município até o momento."
  },

  // ── Variáveis realmente usadas pelo pipeline unificado atual
  // (ajuste_modelos_unificado.py / pipeline_modelagem.py) — nomes de coluna
  // reais vindos do banco, TODOS padronizados em snake_case curto (a SQL
  // já entrega tudo assim agora; antes vinha misturado com MAIUSCULAS cru
  // da tabela sz_municipios, que caía direto no card sem descrição sempre
  // que o nome não combinava exatamente com uma entrada daqui — ex.: typo
  // "SUPERFICE_VEGETAL2020" no banco vs. "superficie_vegetal2020" aqui).
  // Mantidas separadas das entradas acima (que documentam um conjunto de
  // features mais antigo, não usado por este pipeline) em vez de
  // substituí-las.
  incidencia_100k: {
    sigla: "INC_ATUAL",
    descricao: "incidência do período atual (por 100 mil habitantes) — o próprio histórico recente do alvo."
  },
  id_municipio: {
    sigla: "ID_MUN",
    descricao: "identificador do município."
  },

  // Sociodemográficas / geográficas
  perc_pop_rural: { sigla: "POP_RUR", descricao: "percentual da população residente em zona rural." },
  perc_pop_urbana: { sigla: "POP_URB", descricao: "percentual da população residente em zona urbana." },
  perc_apartamento: { sigla: "APTO", descricao: "percentual de domicílios do tipo apartamento." },
  perc_casa: { sigla: "CASA", descricao: "percentual de domicílios do tipo casa." },
  perc_vila_condominio: { sigla: "VILA", descricao: "percentual de domicílios do tipo vila/condomínio." },
  perc_total_moradia: { sigla: "MORADIA", descricao: "razão entre domicílios e população do município." },
  dens_pop: { sigla: "DENS_POP", descricao: "densidade populacional do município (hab/km²)." },
  area_km2: { sigla: "AREA", descricao: "área total do município (km²)." },
  area_vegetal: { sigla: "AREA_VEG", descricao: "área coberta por vegetação em 2020 (km²)." },
  veg_tipo: { sigla: "VEG_TIPO", descricao: "tipo de vegetação predominante no município em 2020." },
  perc_veg: { sigla: "PERC_VEG", descricao: "percentual do território coberto por vegetação." },
  perc_homens: { sigla: "PERC_HOM", descricao: "percentual da população masculina." },
  idhm_renda: { sigla: "IDHM_R", descricao: "IDHM — dimensão renda (2010)." },
  idhm_saude: { sigla: "IDHM_S", descricao: "IDHM — dimensão saúde/longevidade (2010)." },
  idhm_educa: { sigla: "IDHM_E", descricao: "IDHM — dimensão educação (2010)." },
  idhm: { sigla: "IDHM", descricao: "Índice de Desenvolvimento Humano Municipal (2010)." },
  pib: { sigla: "PIB", descricao: "Produto Interno Bruto do município em 2021." },
  n_favelas: { sigla: "N_FAVELA", descricao: "número de favelas no município." },
  pop_favelas: { sigla: "POP_FAV", descricao: "população residente em favelas." },
  dist_capital_km: { sigla: "DIST_CAP", descricao: "distância até a capital (São Paulo), em km." },
  dist_litoral_km: { sigla: "DIST_LIT", descricao: "distância até o litoral mais próximo, em km." },
  log_pop: { sigla: "LOG_POP", descricao: "log da população residente — versão log de \"populacao\", lado a lado pra seleção escolher a mais linear." },
  log_dens_pop: { sigla: "LOG_DENS", descricao: "log da densidade populacional — versão log de \"dens_pop\"." },
  log_pib: { sigla: "LOG_PIB", descricao: "log do PIB municipal — versão log de \"pib\"." },

  // Climáticas (período atual)
  temp: { sigla: "TEMP", descricao: "temperatura média do ar no período (°C)." },
  prec: { sigla: "PREC", descricao: "precipitação total acumulada no período (mm)." },
  prec_med: { sigla: "PREC_MED", descricao: "precipitação média diária no período (mm)." },
  umid: { sigla: "UMID", descricao: "umidade relativa média do ar no período (%)." },
  press: { sigla: "PRESS", descricao: "pressão atmosférica média no período (hPa)." },
  rad: { sigla: "RAD", descricao: "radiação solar média no período (MJ/m²)." },
  tmax: { sigla: "TMAX", descricao: "temperatura máxima registrada no período (°C)." },
  tmin: { sigla: "TMIN", descricao: "temperatura mínima registrada no período (°C)." },
  umax: { sigla: "UMAX", descricao: "umidade relativa máxima registrada no período (%)." },
  umin: { sigla: "UMIN", descricao: "umidade relativa mínima registrada no período (%)." },
  amp_tmax: { sigla: "AMP_TMAX", descricao: "amplitude entre temperaturas máximas diárias no período (°C)." },
  amp_tmin: { sigla: "AMP_TMIN", descricao: "amplitude entre temperaturas mínimas diárias no período (°C)." },
  amp_t: { sigla: "AMP_T", descricao: "amplitude térmica média diária no período (°C)." },
  amp_umax: { sigla: "AMP_UMAX", descricao: "amplitude entre umidades máximas diárias no período (%)." },
  amp_u: { sigla: "AMP_U", descricao: "amplitude média de umidade diária no período (%)." },
  dias_chuva: { sigla: "D_CHUVA", descricao: "quantidade de dias com chuva no período." },
  dias_calor: { sigla: "D_CALOR", descricao: "quantidade de dias de calor intenso no período." },
  seq_chuva: { sigla: "SEQ_CHUVA", descricao: "maior sequência de dias consecutivos com chuva no período." },
  seq_calor: { sigla: "SEQ_CALOR", descricao: "maior sequência de dias consecutivos de calor intenso no período." },

  // Clima — engenharia nova: defasagem, termo quadrático, interação sazonal
  temp_l1: { sigla: "TEMP_L1", descricao: "temperatura média do período anterior (defasagem de 1)." },
  prec_l1: { sigla: "PREC_L1", descricao: "precipitação total do período anterior (defasagem de 1)." },
  temp2: { sigla: "TEMP²", descricao: "temperatura ao quadrado — captura janela ótima (frio ou calor demais reduzem a atividade, não é uma relação linear)." },
  prec2: { sigla: "PREC²", descricao: "precipitação ao quadrado — mesma lógica de janela ótima." },
  temp_x_sin: { sigla: "TEMP×SEN", descricao: "temperatura × componente sazonal (seno) — efeito da temperatura que muda conforme a época do ciclo anual." },
  temp_x_cos: { sigla: "TEMP×COS", descricao: "temperatura × componente sazonal (cosseno)." },
  prec_x_sin: { sigla: "PREC×SEN", descricao: "precipitação × componente sazonal (seno)." },
  prec_x_cos: { sigla: "PREC×COS", descricao: "precipitação × componente sazonal (cosseno)." },
  dias_calor_x_sin: { sigla: "DCAL×SEN", descricao: "dias de calor intenso × componente sazonal (seno)." },
  dias_calor_x_cos: { sigla: "DCAL×COS", descricao: "dias de calor intenso × componente sazonal (cosseno)." },
  dias_chuva_x_sin: { sigla: "DCHU×SEN", descricao: "dias de chuva × componente sazonal (seno)." },
  dias_chuva_x_cos: { sigla: "DCHU×COS", descricao: "dias de chuva × componente sazonal (cosseno)." },

  // Espacial / sazonal / alvo
  inc_viz: { sigla: "INC_VIZ", descricao: "incidência média dos municípios vizinhos mais próximos no mesmo período — sinal de contágio/clustering espacial." },
  inc_l1: { sigla: "INC_L1", descricao: "incidência observada no período anterior (defasagem de 1) — termo autorregressivo." },
  periodo_sin: { sigla: "PER_SEN", descricao: "seno da posição do período no ciclo anual (sazonalidade)." },
  periodo_cos: { sigla: "PER_COS", descricao: "cosseno da posição do período no ciclo anual (sazonalidade)." },
};

// ─────────────────────────────────────────────────────────────────────────
// Categorização das variáveis (sociodemográfica / climática / temporal) e
// helpers de consulta. Feita por classificação de padrão sobre o NOME da
// variável (normalizado para minúsculas) em vez de exigir uma entrada por
// variável em COVARIAVEIS — cobre tanto os nomes reais atuais (ex.:
// "ALTITUDE", "IDHM_RENDA2010", vindos do banco em maiúsculas) quanto os
// nomes do conjunto de features mais antigo documentado acima.
export const CATEGORIAS = {
  sociodemografica: { label: "Sociodemográfica", color: "#2563eb" },
  climatica: { label: "Climática", color: "#059669" },
  temporal: { label: "Temporal", color: "#d97706" },
};

const NOMES_SOCIODEMOGRAFICOS = new Set([
  "populacao", "altitude", "area_vegetal", "veg_tipo",
  "perc_veg", "area_km2", "perc_homens",
  "idhm_renda", "idhm_saude", "idhm_educa", "idhm",
  "pop_rural", "pop_urbana", "perc_pop_rural", "perc_pop_urbana",
  "pib", "n_favelas", "pop_favelas",
  "apartamento", "casa", "vila_condominio", "total_moradia",
  "perc_apartamento", "perc_casa", "perc_vila_condominio", "perc_total_moradia",
  "dens_pop", "latitude", "longitude", "id_municipio",
  "dist_capital_km", "dist_litoral_km",
  "log_pop", "log_dens_pop", "log_pib",
  // nomes antigos (conjunto de features legado, documentado no topo do
  // arquivo) — mantidos aqui pra não regredir a classificação caso algum
  // dado antigo persistido ainda use esses nomes.
  "superficie_vegetal2020", "vegetacao2020", "percentual_vegetacao",
  "percentual_homens", "idhm_renda2010", "idhm_saude2010", "idhm_educacao2010",
  "idhm_educa2010", "idhm_2010", "pib2021", "densidade_populacional",
]);

const NOMES_TEMPORAIS = new Set([
  "periodo_sin", "periodo_cos", "mes_sin", "mes_cos", "tempo_mes",
  "incidencia_100k", "media_hist_municipio", "inc_viz", "inc_l1",
]);

/**
 * Classifica uma variável em "sociodemografica" | "climatica" | "temporal".
 * Interações clima × tempo/sazonalidade (ex.: "temp_x_sin", "dias_chuva_x_cos",
 * e as antigas "_x_tempo"/"_x_mes_sin"/"_x_mes_cos") contam como temporais: o
 * que as distingue da variável climática "pura" (que já existe como feature
 * separada) é justamente a modulação ao longo do tempo. Qualquer coisa não
 * reconhecida cai em "climatica" por padrão — cobre de graça as variantes
 * novas de clima (lags "_l1", quadráticos "temp2"/"prec2") sem precisar
 * listar cada uma.
 */
export function classifyVariable(nomeBruto) {
  const nome = String(nomeBruto || "").toLowerCase();
  if (!nome) return "climatica";

  if (
    nome.includes("_x_tempo") || nome.includes("_x_mes_sin") || nome.includes("_x_mes_cos") ||
    nome.endsWith("_x_sin") || nome.endsWith("_x_cos")
  ) {
    return "temporal";
  }
  if (NOMES_TEMPORAIS.has(nome) || /^y_(lag|roll)\d+$/.test(nome)) {
    return "temporal";
  }
  if (NOMES_SOCIODEMOGRAFICOS.has(nome)) {
    return "sociodemografica";
  }
  return "climatica";
}

/** Busca em COVARIAVEIS ignorando maiúsculas/minúsculas (o banco guarda
 * nomes de coluna originais, ex.: "IDHM_RENDA2010", "ALTITUDE"). */
export function getCovariavel(nomeBruto) {
  const nome = String(nomeBruto || "").toLowerCase();
  return COVARIAVEIS[nome] || null;
}