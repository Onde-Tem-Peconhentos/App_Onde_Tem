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
  }
};