export const MODELOS = [
  { value: "", label: "Selecione um modelo" },
  {
    value: "ols",
    label: "Ordinary Least Squares",
    titulo: "Regressão Linear Múltipla (OLS)",
    descricaoParagrafos: [
      "O modelo de regressão linear por Mínimos Quadrados Ordinários (Ordinary Least Squares – OLS) é um dos métodos mais tradicionais da análise estatística (Dobson e Barnett, 2018). Nele, a variável resposta é modelada como uma combinação linear de um conjunto de variáveis explicativas, sendo os coeficientes estimados de forma a minimizar a soma dos quadrados dos resíduos.",
      "O modelo assume que a relação entre as variáveis é constante em toda a área de estudo, ou seja, um único conjunto de coeficientes representa todas as observações. Essa característica torna o OLS adequado quando a relação entre as variáveis é estacionária, porém limita sua aplicação em fenômenos com heterogeneidade espacial, motivando o desenvolvimento de modelos como a Geographically Weighted Regression (Brunsdon et al., 1996).",
    ],
    formulaBasica: String.raw`y_i = \beta_0 + \sum_{k=1}^{p}\beta_k x_{ik} + \varepsilon_i`,
    formula: String.raw`y_i = \beta_0 + \beta_1 POPFAV_i + \beta_2 ALT_i + \beta_3 VEG_i + \beta_4 AREA_i + \beta_5 PREC_i + \varepsilon_i`,
    variaveis: ["POPFAV", "ALT", "VEG", "AREA", "PREC"],
  },
  {
    value: "GWR",
    label: "Geographically Weighted Regression",
    titulo: "Geographically Weighted Regression",
    descricaoParagrafos: [
      "A Geographically Weighted Regression (GWR) foi proposta por Brunsdon, Fotheringham e Charlton (1996) como uma extensão do modelo OLS para capturar relações espaciais não estacionárias. Em vez de estimar um único conjunto de coeficientes para toda a área de estudo, o modelo calcula coeficientes locais para cada localização geográfica.",
      "As estimativas locais são obtidas por meio de uma regressão ponderada, em que observações espacialmente próximas recebem pesos maiores do que observações distantes, conforme uma função kernel e um parâmetro de largura de banda (bandwidth). Dessa forma, o modelo permite identificar como a influência de cada variável explicativa varia ao longo do espaço, produzindo mapas de coeficientes locais e melhorando a interpretação de fenômenos espaciais.",
    ],
    formulaBasica: String.raw`y_i = \beta_0(u_i,v_i) + \sum_{k=1}^{p}\beta_k(u_i,v_i)x_{ik} + \varepsilon_i`,
    formula: String.raw`y_i = \beta_0(u_i,v_i) + \beta_1(u_i,v_i)\,POPFAV_i + \beta_2(u_i,v_i)\,ALT_i + \beta_3(u_i,v_i)\,VEG_i + \beta_4(u_i,v_i)\,AREA_i + \beta_5(u_i,v_i)\,PREC_i + \varepsilon_i`,
    variaveis: ["POPFAV", "ALT", "VEG", "AREA", "PREC"],
  },
  {
    value: "gwr_adaptativo",
    label: "GWR-Adaptativo",
    titulo: "Geographically Weighted Regression (Bandwidth Adaptativo)",
    descricaoParagrafos: [
      "Uma variante da GWR em que a largura de banda (bandwidth) não é uma distância fixa em quilômetros, e sim um número k de municípios vizinhos mais próximos. Isso faz com que o raio de influência se ajuste à densidade local: em regiões com muitos municípios próximos, a vizinhança considerada fica geograficamente menor; em regiões mais esparsas, ela se expande até reunir os k vizinhos mais próximos.",
      "O valor de k é escolhido por validação cruzada (leave-one-out), buscando o número de vizinhos que minimiza o erro de previsão. Por se adaptar à densidade espacial dos dados, esse modelo costuma ser mais robusto que a GWR de bandwidth fixo em áreas de estudo com distribuição heterogênea de municípios — caso do território brasileiro.",
    ],
    formulaBasica: String.raw`y_i = \beta_0(u_i,v_i) + \sum_{k=1}^{p}\beta_k(u_i,v_i)x_{ik} + \varepsilon_i`,
    formula: String.raw`y_i = \beta_0(u_i,v_i) + \beta_1(u_i,v_i)\,POPFAV_i + \beta_2(u_i,v_i)\,ALT_i + \beta_3(u_i,v_i)\,VEG_i + \beta_4(u_i,v_i)\,AREA_i + \beta_5(u_i,v_i)\,PREC_i + \varepsilon_i`,
    variaveis: ["POPFAV", "ALT", "VEG", "AREA", "PREC"],
  },
  {
    value: "GTWR",
    label: "Geographically and Temporally Weighted Regression",
    titulo: "Geographically and Temporally Weighted Regression",
    descricaoParagrafos: [
      "A Geographically and Temporally Weighted Regression (GTWR) foi proposta por Huang, Wu e Barry (2010) como uma extensão da GWR para incorporar simultaneamente a dependência espacial e temporal. Nesse modelo, os coeficientes passam a variar tanto no espaço quanto no tempo, permitindo representar processos cujas relações evoluem ao longo dos anos ou períodos analisados.",
      "Para estimar os coeficientes locais, o GTWR utiliza uma função de ponderação baseada em uma distância espaço-temporal, combinando a proximidade geográfica e a proximidade temporal em um único kernel. Assim, observações próximas tanto espacial quanto temporalmente exercem maior influência na estimação dos parâmetros locais, tornando o modelo especialmente adequado para dados em painel e séries espaço-temporais.",
    ],
    formulaBasica: String.raw`y_i = \beta_0(u_i,v_i,t_i) + \sum_{k=1}^{p}\beta_k(u_i,v_i,t_i)x_{ik} + \varepsilon_i`,
    formula: String.raw`y_i = \beta_0(u_i,v_i,t_i) + \beta_1(u_i,v_i,t_i)\,POPFAV_i + \beta_2(u_i,v_i,t_i)\,ALT_i + \beta_3(u_i,v_i,t_i)\,VEG_i + \beta_4(u_i,v_i,t_i)\,AREA_i + \beta_5(u_i,v_i,t_i)\,PREC_i + \varepsilon_i`,
    variaveis: ["POPFAV", "ALT", "VEG", "AREA", "PREC"],
  },
];

export const ANIMAIS = [
  { value: "", label: "Selecione um animal" },
  { value: "Escorpião", label: "Escorpião" },
  { value: "Serpente", label: "Serpente" },
  { value: "Aranha", label: "Aranha" },
  { value: "Abelha", label: "Abelha" },
  { value: "Lagarta", label: "Lagarta" },
];

export const TEMPOS = [
  { value: "", label: "Selecione a granularidade" },
  { value: "Mês", label: "Mês" },
  { value: "Trimestre", label: "Trimestre" },
  { value: "Semestre", label: "Semestre" },
  { value: "Ano", label: "Ano" },
];