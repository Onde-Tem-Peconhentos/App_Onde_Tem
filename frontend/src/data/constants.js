// src/data/constants.js
export const MODELOS = [
    { value: "", label: "Selecione um modelo" },
    {
    value: "ols",
    label: "Ordinary Least Squares",
    titulo: "Ordinary Least Squares",
    descricaoParagrafos: [
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
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
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
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
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
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
  { value: "Ano", label: "Ano" },
];