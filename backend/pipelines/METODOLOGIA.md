# Metodologia do pipeline de modelagem

Este documento descreve, de ponta a ponta, como o pipeline de modelagem em
`backend/pipelines/` funciona hoje: de onde vêm os dados, como as variáveis
são construídas, como os modelos são ajustados e como seus hiperparâmetros
são escolhidos, como a previsão (forecast) é gerada, e como tudo é
persistido e servido para o frontend.

O objetivo é prever, por município e por período (mês/trimestre/semestre/
ano), a **incidência de acidentes por 100 mil habitantes** (`incidencia_100k`)
para uma determinada categoria de animal (ex.: Serpente, Escorpião), um
período à frente.

> Arquivos centrais: `pipeline_modelagem.py` (orquestração + persistência) e
> `modelos_modelagem/ajuste_modelos_unificado.py` (núcleo de modelagem,
> usado por todas as periodicidades).

---

## 1. Visão geral do fluxo

```
Postgres (modelos.*)
   │  query_modelagem (SQL)
   ▼
painel mensal bruto (1 linha por município × mês)
   │  aggregate_period()            [se trimestre/semestre/ano]
   ▼
painel na periodicidade alvo (1 linha por município × período)
   │  feature engineering (y_t, y_next, periodo_sin/cos)
   ▼
split treino / teste / forecast (janelas fixas, por cadência)
   │
   ├─► seleção de variáveis (rolling window: Lasso + stepwise AIC)
   │
   ├─► ajuste dos modelos: OLS, GWR (fixo), GWR-Adaptativo, GTWR
   │        cada um com sua própria busca de hiperparâmetro via LOOCV
   │
   ├─► baselines: zero, persistência, média histórica municipal
   │
   ├─► métricas (MSE/RMSE/MAE/R²/ganho vs. baseline) + Índice de Moran
   │
   └─► forecast para o próximo período (fora da amostra de teste)
   │
   ▼
GeoJSONs (observado/predito/resíduo/forecast) + persistência em
modelos.bz_previsao
   │
   ▼
API FastAPI (`/api/modelo`) → frontend (mapas + métricas)
```

Tudo isso roda para **cada combinação (animal × periodicidade)**. Hoje o
`pipeline_modelagem.py` está configurado para rodar apenas para
`animais_para_processar = ["Serpente"]` (ajustável na própria variável) e
para as 4 periodicidades (`CADENCE_CONFIG`).

---

## 2. Fonte dos dados

A query `query_modelagem` (em `pipeline_modelagem.py`) monta, para um dado
animal, um painel **mensal completo**: um `CROSS JOIN` entre todos os 645
municípios (`modelos.sz_municipios`) e todos os meses entre `2022-01-01` e
hoje (`generate_series`), preenchido com:

- **Alvo**: contagem de ocorrências do animal naquele município/mês
  (`modelos.bz_sinan_ocorrencias`, `COALESCE(..., 0)` quando não há registro)
  e a incidência por 100 mil habitantes (`incidencia_100k`).
- **Atributos estáticos do município**: população, lat/long, IDHM (renda/
  saúde/educação), PIB, % área rural/urbana, % tipos de moradia, favelas,
  densidade populacional, altitude, vegetação, % homens, etc.
- **Clima mensal interpolado** por município
  (`modelos.sz_municipios_clima_interpolado`): temperatura, precipitação,
  umidade, pressão, radiação, dias de chuva/calor intenso, amplitudes e
  sequências máximas.
- **Features de tendência/sazonalidade mensal**: `mes_sin`/`mes_cos` e uma
  série de interações clima × tempo (`temp_x_tempo`, `dias_chuva_x_mes_sin`
  etc.) — construídas em SQL, mas usadas apenas quando a cadência é "mês"
  processada pela versão legada; o pipeline unificado (seção 3) descarta
  essas colunas e recalcula sazonalidade de forma genérica.

O grid é sempre completo (todo município tem uma linha por mês, mesmo sem
nenhuma ocorrência), então não há viés de seleção por ausência de dados —
zeros reais viram `0`, não `NULL`.

---

## 3. Unificação das periodicidades

Historicamente existiam implementações separadas e divergentes por
periodicidade (`ajuste_modelos_mensal.py`, `ajuste_modelos_trimestral.py`,
`ajuste_modelos_anual.py`, além de uma tentativa genérica mais antiga,
`ajuste_modelos.py`) — só a mensal estava de fato conectada a um pipeline, e
cada uma usava um método de seleção de variáveis diferente. Isso foi
unificado em `modelos_modelagem/ajuste_modelos_unificado.py`
(`fit_periodo` + `aggregate_period`), que atende mês/trimestre/semestre/ano
com o **mesmo** método de seleção de variáveis e o **mesmo** conjunto de
modelos. As implementações antigas foram **mantidas no repositório**, sem
uso, como referência histórica.

### 3.1 Agregação (`aggregate_period`)

Para trimestre/semestre/ano, o painel mensal é agregado por
`(id_município, período)`:

| Grupo de coluna | Regra de agregação |
|---|---|
| `total_ocorrencias` | soma |
| Acumulados climáticos (precipitação total, dias de chuva, dias de calor intenso) | soma |
| Médias climáticas (temperatura, umidade, pressão, radiação, precipitação média) | média |
| Extremos (`temp_max`, `umid_max`, `max_seq_dias_chuva`, ...) | máximo |
| Extremos mínimos (`temp_min`, `umid_min`) | mínimo |
| Atributos estáticos do município (IDHM, PIB, altitude, % moradia, etc.) | máximo (constante, só "carrega adiante") |

`incidencia_100k` é **recalculada** após a agregação
(`soma(ocorrências) × 100000 / população`), nunca apenas somada/mediada
diretamente.

Identificador do período: `mes` → `AAAAMM`; `trimestre` → `AAAAT` (T=1-4,
mesmo formato que `ajuste_modelos_trimestral.py` já usava); `semestre` →
`AAAAS` (S=1-2); `ano` → `AAAA`. Também é guardado `periodo_fim_anomes`
(o último mês coberto pelo período, sempre em formato `AAAAMM`) — usado para
alimentar o kernel temporal do GTWR (que só entende esse formato).

### 3.2 Sazonalidade genérica

Em vez das colunas de interação clima × tempo específicas de mês (que não
fazem sentido em outra escala), é calculado `periodo_sin`/`periodo_cos`
usando o ciclo correto por cadência: 12 (mês), 4 (trimestre), 2 (semestre),
1 (ano — sem ciclo, a coluna fica constante e é descartada automaticamente
pela seleção de variáveis).

---

## 4. Alvo e split temporal

Dentro de `fit_periodo`, por município, o alvo de treino é sempre o
**próximo período**:

- `y_t` = incidência no período atual.
- `y_next` = incidência no período seguinte (`shift(-1)` por município) — é
  isso que todos os modelos realmente preveem.

O split é definido por **janelas fixas de período**, configuradas por
cadência em `CADENCE_CONFIG` (`pipeline_modelagem.py`):

| Cadência | Treino | Teste | Forecast |
|---|---|---|---|
| Mês | 2022-01 a 2025-12 | 2026-01 a 2026-04 | 2026-06 |
| Trimestre | 2022T1 a 2024T4 | 2025T1 a 2025T4 | 2026T2 |
| Semestre | 2022S1 a 2024S2 | 2025S1 a 2025S2 | 2026S2 |
| Ano | 2022 a 2023 | 2024 a 2025 | 2026 |

O forecast é sempre gerado para um período **existente no grid** (o grid
mensal vai até a data atual), mesmo que os dados climáticos daquele período
ainda não existam de verdade — nesse caso eles entram como `NaN` e são
imputados pela mediana do treino no momento da previsão, como em qualquer
extrapolação genuína para o futuro.

Cadências mais grossas (trimestre/semestre/ano) têm poucos períodos
disponíveis no histórico atual (2022–meados de 2026): 19 trimestres, 10
semestres, só 5 anos (2026 incompleto). Isso é uma limitação real dos
dados, não do código — resultados na cadência **anual** em particular devem
ser tratados como exploratórios (só 2 períodos de treino na configuração
atual).

---

## 5. Seleção de variáveis (hiperparâmetro: quais features entram no modelo)

Método único para todas as cadências, em
`utils_modelagem.fit_predict_lasso_base_models`:

1. **LassoCV com dobras temporais** (`LassoCV`, padronizado via
   `StandardScaler`): descarta de saída qualquer variável cujo coeficiente
   vá a zero. As dobras de validação cruzada são temporais (treina em
   períodos passados, valida no período seguinte), não aleatórias — evita
   vazamento de informação futura.
2. **Stepwise bidirecional por AIC**: a partir das variáveis que sobraram do
   Lasso, adiciona a variável que mais reduz o AIC de um OLS; depois de cada
   adição, tenta remover alguma variável se isso reduzir o AIC ainda mais.
   Para no máximo `top_k` variáveis (padrão: 20).

### 5.1 Estabilidade via janela rolling

Isso não é feito uma única vez sobre todo o treino: `fit_periodo` percorre
o treino em **janelas rolling** (`rolling_window_periods` períodos de
histórico, mínimo `rolling_min_train_periods` para começar — configurados
por cadência) e roda a seleção acima em cada janela, contando quantas vezes
cada variável foi selecionada. As `top_k` variáveis mais frequentes viram os
candidatos finais; sobre elas, um último ajuste Lasso+stepwise (agora usando
todo o treino) decide o conjunto definitivo.

O resultado inclui uma tabela de **estabilidade** (`estabilidade_variaveis`
no retorno de `fit_periodo`, também impressa no log): para cada variável do
modelo final, em que fração das janelas rolling ela foi de fato selecionada.
Uma variável presente no modelo final mas selecionada em menos de 50% das
janelas é sinalizada explicitamente no log (`[!] ... tratar com cautela`) —
é um sinal de que ela pode estar entrando mais por acaso do que por sinal
real.

---

## 6. Modelos ajustados e seus hiperparâmetros

Todos os modelos preveem `y_next` a partir das variáveis selecionadas na
seção 5. Cada um é reavaliado do zero em cada `fit_periodo` (não há reuso de
hiperparâmetro entre chamadas, exceto onde indicado).

### 6.1 OLS Global (`statsmodels.OLS`)

Regressão linear única para o país inteiro — sem hiperparâmetro espacial,
serve de referência "sem heterogeneidade espacial".

### 6.2 GWR — Geographically Weighted Regression (`modelos_modelagem/gwr.py`)

Um conjunto de regressões ponderadas localmente: cada município tem seus
próprios coeficientes, estimados dando mais peso a municípios vizinhos
(kernel gaussiano sobre distância haversine).

- **Hiperparâmetro**: bandwidth (raio de influência). Dois modos:
  - **Fixo** (`GWR (Gaussiano)`): bandwidth em **km**, igual para o país
    todo. Busca por **grid search** (15 candidatos) via **LOOCV**
    (deixa-um-município-de-fora), numa amostra de 1 linha por município
    (o município na sua última observação de treino).
  - **Adaptativo** (`GWR-Adaptativo`): bandwidth = número **k** de
    municípios vizinhos mais próximos (raio varia por região, mais apertado
    onde há mais municípios perto). Busca por **golden section search**
    sobre `k`, também via LOOCV na mesma amostra de 1 linha/município.
- **Implementação**: reescrita em 2026-09-13 para rankear vizinhos sempre
  sobre coordenadas **distintas** de município (via `BallTree`), nunca sobre
  linhas duplicadas do painel (cada município tem uma linha por período de
  treino). Antes disso havia um bug de escala: o `k` validado por LOOCV
  (sobre a amostra de 1 linha/município) tinha um significado físico
  diferente do `k` de fato aplicado no ajuste final (sobre o painel
  completo, com várias linhas por município) — um `k=200` validado podia
  colapsar para ~4 municípios distintos reais. A classe antiga fica
  preservada como `GeographicallyWeightedRegressionLegacy` no mesmo
  arquivo, só para referência.

### 6.3 GTWR — Geographically & Temporally Weighted Regression (`modelos_modelagem/gtwr.py`)

Extensão do GWR: o peso de cada vizinho combina proximidade **espacial** e
proximidade **temporal** — `W = W_espacial × W_temporal`, com
`W_temporal = exp(-tau × dt²)` (`dt` = diferença em meses entre o período
da observação de referência e o período sendo previsto).

- **Hiperparâmetros**: `k_s` (nº de municípios vizinhos, mesmo papel do GWR-
  Adaptativo) e `tau` (taxa de decaimento temporal — quanto maior, mais o
  modelo "esquece" observações de períodos distantes).
- **Busca (2026-09-13, autônoma)**: as duas etapas são buscadas por golden
  search via LOOCV, em sequência — primeiro `tau` (com `k_s` num valor
  inicial), depois `k_s` (com o `tau` já encontrado). A busca roda apenas
  sobre os **12 períodos de treino mais recentes** (todos os 645 municípios
  mantidos — nunca o contrário, ver nota abaixo) para ficar rápida; o
  **ajuste final sempre usa o painel de treino completo**. A faixa de busca
  de `k_s` é ancorada em torno do `k` já validado pelo GWR-Adaptativo (±60%)
  em vez de uma faixa fixa pequena.
- **Bug corrigido (2026-09-13)**: a fórmula original dividia `dt` (meses)
  pelo bandwidth **espacial** em km antes de aplicar `tau` — unidades
  incompatíveis, que tornavam `tau` praticamente sem efeito em qualquer
  ponto prático de busca (variar `tau` em 3 ordens de grandeza mudava o
  MSE-LOOCV só na 6ª casa decimal). Sem sinal temporal real, a busca de
  `k_s` "às cegas" overfitava para a borda da faixa de busca. Corrigido
  removendo essa divisão indevida (classe antiga preservada como
  `GeographicallyTemporallyWeightedRegressionLegacy`).
- **Por que não subamostrar municípios na busca**: reduzir o número de
  municípios (em vez de períodos) mudaria o que "k vizinhos" significa
  fisicamente entre a busca e o ajuste final — exatamente o mesmo tipo de
  bug de escala corrigido no GWR (seção 6.2). Por isso a busca só encurta o
  eixo temporal, nunca o espacial.

### 6.4 Baselines (sem hiperparâmetro)

Sempre calculados para servir de referência:

- **Zero**: prevê sempre 0.
- **Persistência**: prevê que o próximo período repete o valor atual
  (`y_next = y_t`).
- **Média municipal**: prevê a média histórica de cada município no
  treino.

O `gain_vs_media_municipal` reportado em todas as métricas é sempre
relativo a esse último baseline — é o mínimo que qualquer modelo "de
verdade" deveria superar para ser considerado útil.

---

## 7. Métricas e diagnóstico espacial

Para cada modelo (incluindo baselines), calculado sobre o conjunto de
**teste** (nunca visto durante a seleção de variáveis nem durante a busca
de hiperparâmetro): MSE, RMSE, MAE, R² (`utils_modelagem.calc_metrics`) e
`gain_vs_media_municipal` = `(MSE_baseline − MSE_modelo) / MSE_baseline`.

Além disso, para OLS/GWR/GWR-Adaptativo/GTWR, é calculado o **Índice de
Moran** dos resíduos em cada mês de teste (matriz de pesos gaussiana sobre
distância haversine, mesmo bandwidth do GWR fixo) — mede se ainda sobra
autocorrelação espacial não capturada pelo modelo. Um Moran's I
significativo (p<0.05) indica que o modelo está deixando estrutura espacial
na mesa; idealmente os resíduos de um bom modelo espacial devem ser
espacialmente aleatórios (Moran's I ≈ 0, não significativo).

---

## 8. Forecast e mapas

Depois do ajuste (seleção de variáveis + hiperparâmetros, tudo decidido só
com dados de treino/teste), cada modelo é usado para prever o
`forecast_period` configurado (seção 4) — um período fora da janela de
teste, geralmente o mais próximo do "agora" que o grid permite.

Os resultados (observado/predito/resíduo no teste, e predito no forecast)
são convertidos em GeoJSON por `modelos_modelagem/geospatial.py`
(`build_geojsons`, `build_geojson_forecast`), que junta com a geometria dos
municípios (`modelos.sz_municipios`) e aplica uma escala de cor:
sequencial (branco→vermelho) para incidência, divergente (azul→branco→
vermelho) para resíduos.

---

## 9. Persistência

`modelos_modelagem/persistencia.py` (`persist_results_periodo`) grava, para
cada método (`ols`, `gwr`, `gwr_adaptativo`, `gtwr` — os baselines **não**
são persistidos) e cada `tipo_periodo` (`Mês`, `Trimestre`, `Semestre`,
`Ano`), uma linha em `modelos.bz_previsao`: métricas, hiperparâmetros
(`gwr_bandwidth_km`, `gwr_bandwidth_k`, `gtwr_bandwidth_s`, `gtwr_tau`),
diagnóstico de Moran, lista de variáveis selecionadas, e os 4 GeoJSONs
(observado/predito/resíduo/forecast) como texto.

Cada execução gera uma nova leva de linhas (chave única inclui
`data_processamento`), então o histórico de execuções anteriores nunca é
sobrescrito — só se acumula. A função `persist_results_mes` (mais antiga,
usada apenas para a cadência mensal antes da unificação) continua no mesmo
arquivo, intacta, sem uso pelo pipeline atual.

> Nota de nomenclatura: as colunas `train_month_inicio`, `test_month_fim`
> etc. da tabela guardam o identificador de período (que pode ser um
> trimestre/semestre/ano, não necessariamente um mês) — o nome da coluna é
> um resquício da época em que só existia a cadência mensal; não foi
> renomeado para evitar uma migração de schema.

---

## 10. Como isso chega ao frontend

`backend/app/api/modelo_routes.py` expõe `GET /api/modelo?animal=&metodo=&
tipo_periodo=`, que busca em `modelos.bz_previsao` a linha mais recente para
essa combinação (`ORDER BY data_processamento DESC LIMIT 1`) e devolve
GeoJSONs + métricas + hiperparâmetros + variáveis selecionadas em JSON. O
hook `frontend/src/hooks/useModeloGeo.js` consome esse endpoint.

Hoje o frontend (`frontend/src/data/constants.js`, `TEMPOS`) só expõe "Mês"
e "Ano" como opção de periodicidade na interface — "Trimestre" e "Semestre"
já têm dados persistidos e a API já responde para eles, mas a opção ainda
não foi adicionada à interface.

---

## 11. Como executar

```bash
cd backend/pipelines
PYTHONPATH=$(pwd) ../.venv/bin/python pipeline_modelagem.py
```

Requer o Postgres local rodando (`docker-compose up -d` na raiz do
projeto) e as dependências do `backend/.venv` (mgwr, libpysal, esda,
geopandas, statsmodels, scikit-learn, joblib — não estão no
`requirements.txt`, que está desatualizado, mas já estão instaladas no
venv).

Para restringir quais animais/periodicidades rodam, edite
`animais_para_processar` e `CADENCE_CONFIG` no topo de
`pipeline_modelagem.py`.

---

## 12. Limitações conhecidas

- **Cadência anual é pobre em dados**: só 5 anos de histórico (2022–2026,
  o último incompleto), 2 usados para treino na configuração atual —
  resultados devem ser tratados como exploratórios.
- **GTWR ainda é o modelo mais instável dos quatro**, mesmo após a correção
  de 2026-09-13 — em algumas combinações (animal × cadência) ele perde para
  o baseline por uma margem pequena. Vale reavaliar depois de rodar para
  mais categorias de animal.
- **Sazonalidade/tendência mensal**: o pipeline unificado descarta as
  interações clima × tempo específicas de mês (`temp_x_tempo` etc.) em
  favor de `periodo_sin`/`periodo_cos` genéricos — isso torna as 4
  cadências comparáveis entre si, mas significa que a cadência "mês" do
  pipeline unificado não é bit-a-bit idêntica à antiga implementação
  `ajuste_modelos_mensal.fit_mensal` (as métricas ficam muito próximas, mas
  não idênticas).
- **Alvo é uma contagem rara/esparsa** (incidência de picadas por
  município-período): em cadências mais finas (mês) o sinal é fraco e
  ruidoso — todos os modelos, mesmo bem ajustados, tendem a ficar próximos
  do baseline de média histórica municipal. Um modelo de contagem
  (Poisson/GWPR — existe um esqueleto não conectado em `gwpr.py`) é
  provavelmente mais adequado a essa escala do que os modelos gaussianos
  atuais.
