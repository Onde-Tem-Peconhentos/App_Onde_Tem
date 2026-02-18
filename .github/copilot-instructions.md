# Copilot instructions — App_Onde_Tem

## Visão geral (arquitetura)

- Monorepo com backend FastAPI + SQLite e frontend React/Vite.
- Backend expõe endpoints de dashboard em [backend/dashboard_routes.py](backend/dashboard_routes.py) (rota base `/dashboard`).
- Persistência via SQLAlchemy em [backend/models.py](backend/models.py); banco local `sinan.db` no diretório do backend.
- Pipeline de dados recria o banco e pré-agrega métricas: [backend/main_db.py](backend/main_db.py) orquestra `pipeline_municipios.py`, `pipeline_acidentes.py`, `pipeline_postos.py`, cria índices e tabelas resumo (`dashboard_*`).
- Frontend consome o backend via `fetch` direto em `http://localhost:8000` (ver [frontend/src/pages/DashboardPage.jsx](frontend/src/pages/DashboardPage.jsx)).

## Fluxos críticos

- **Recriar base** (apaga `sinan.db`): execute [backend/main_db.py](backend/main_db.py). Isso também gera tabelas `dashboard_metrics`, `dashboard_casos_por_ano`, `dashboard_por_animal`, `dashboard_por_gravidade` usadas como caminho rápido no resumo.
- **API**: FastAPI app em [backend/main.py](backend/main.py). O CORS já libera `localhost` em portas 5173–5177 e 8000.
- **Frontend**: Vite app em [frontend/package.json](frontend/package.json) (`npm run dev`, `npm run build`).

## Padrões e convenções do projeto

- **UI controls customizados**: `UiSelect`/`UiMultiSelect` em [frontend/src/components](frontend/src/components) simulam eventos com `onChange({ target: { name, value } })`. Ao criar novos filtros, siga esse contrato.
- **Filtros no dashboard**: strings/arrays são enviados como query params repetidos (`anos=2020&anos=2021`, `animais=...`). Mantenha esse padrão ao ampliar filtros (ver [frontend/src/pages/DashboardPage.jsx](frontend/src/pages/DashboardPage.jsx)).
- **Cache do resumo**: quando sem filtros, [backend/dashboard_routes.py](backend/dashboard_routes.py) usa cache em memória + invalidação por `mtime` do `sinan.db`, além de tabelas pré-agregadas. Evite mudar nomes dessas tabelas sem atualizar o script de criação.
- **Dados brutos**: pipelines leem CSVs em [backend/dados_brutos](backend/dados_brutos) com nomes específicos (`municipios_sp.csv`, `postos_organizados.csv`). Mantenha o working dir como `backend/` ao rodar scripts.

## Integrações e pontos de atenção

- **SINAN**: `pipeline_acidentes.py` usa PySUS/SINAN e faz tradução de códigos para textos (MAPS). Alterações nos campos devem manter coerência com as colunas do modelo em [backend/models.py](backend/models.py).
- **Leaflet**: mapas no frontend usam `react-leaflet` e CSS do Leaflet importado nas páginas (ex.: [frontend/src/pages/BuscaPage.jsx](frontend/src/pages/BuscaPage.jsx)).

## Onde olhar primeiro

- Backend API + cache: [backend/dashboard_routes.py](backend/dashboard_routes.py)
- Modelos/DB: [backend/models.py](backend/models.py)
- Orquestração do ETL: [backend/main_db.py](backend/main_db.py)
- Tela principal do dashboard: [frontend/src/pages/DashboardPage.jsx](frontend/src/pages/DashboardPage.jsx)
