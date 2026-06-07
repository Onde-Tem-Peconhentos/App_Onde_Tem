import requests
import datetime
import logging
import zipfile
import shutil
import io
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from typing import Tuple, List
import numpy as np
from sqlalchemy import create_engine, text
import psycopg2
import time
import os
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuração de Logs
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações de Banco
load_dotenv('/home/gabi/wkplace/ProjetoIC/App_Onde_Tem/backend/.env.example') # placeholder
DB_URI = os.getenv("DATABASE_URL")


class ETL_INMET:
    def __init__(self, start_year: int = None, end_year: int = None, delete_local: bool = False):
        self.start_time = time.time()
        self.delete_local = delete_local
        self.logger = logging.getLogger("ETL_INMET")
        self.base_dir = Path(f"./.temp_inmet")
        self.zip_dir = self.base_dir / "_zip"
        self.raw_dir = self.base_dir / "_raw"
        
        self.start_year = start_year
        self.end_year = end_year or datetime.datetime.now().year
        
        self.engine = create_engine(DB_URI)
        from urllib.parse import urlparse
        _u = urlparse(DB_URI)
        self._db_conn_params = dict(
            host=_u.hostname, port=_u.port or 5432,
            dbname=_u.path.lstrip('/'), user=_u.username, password=_u.password
        )

        for d in [self.zip_dir, self.raw_dir]: 
            d.mkdir(parents=True, exist_ok=True)

    def _normalize_col(self, name: str) -> str:
        import unicodedata
        nfkd = unicodedata.normalize('NFKD', str(name))
        return "".join([c for c in nfkd if not unicodedata.combining(c)]).upper().strip()

    def _init_db_schema(self):
        self.logger.info("Sincronizando tabelas nos schemas public e stg...")
        queries = [
            "CREATE SCHEMA IF NOT EXISTS stg;",
            "DROP TABLE IF EXISTS stg.stg_dados_inmet_horarios;",
            """CREATE TABLE IF NOT EXISTS public.dados_estacoes (
                "CODIGO" VARCHAR(20) PRIMARY KEY, "ESTACAO" VARCHAR(255),
                "LATITUDE" DOUBLE PRECISION, "LONGITUDE" DOUBLE PRECISION,
                "ALTITUDE" DOUBLE PRECISION, "DATA DE FUNDACAO" DATE
            );""",
            """CREATE TABLE IF NOT EXISTS public.dados_inmet_horarios (
                "DATA_HORA" TIMESTAMP, "CODIGO_ESTACAO" VARCHAR(20),
                "PRECIPITACAO" DOUBLE PRECISION, "PRESSAO_ATM" DOUBLE PRECISION,
                "RADIACAO" DOUBLE PRECISION, "TEMP_AR" DOUBLE PRECISION,
                "TEMP_MAX" DOUBLE PRECISION, "TEMP_MIN" DOUBLE PRECISION,
                "UMID_MAX" DOUBLE PRECISION, "UMID_MIN" DOUBLE PRECISION,
                "UMID_AR" DOUBLE PRECISION,
                PRIMARY KEY ("DATA_HORA", "CODIGO_ESTACAO")
            );""",
            """CREATE UNLOGGED TABLE stg.stg_dados_inmet_horarios (
                "PRECIPITACAO" TEXT, "PRESSAO_ATM" TEXT, "RADIACAO" TEXT, 
                "TEMP_AR" TEXT, "TEMP_MAX" TEXT, "TEMP_MIN" TEXT, 
                "UMID_MAX" TEXT, "UMID_MIN" TEXT, "UMID_AR" TEXT,
                "DATA_HORA" TEXT, "CODIGO_ESTACAO" TEXT
            );"""
        ]
        with self.engine.begin() as conn:
            for q in queries: conn.execute(text(q))

    # -----------------------------------------------------------------------
    # NOVO: Extração de Metadados das Estações (Cabeçalho do CSV)
    # -----------------------------------------------------------------------
    def _extract_metadata(self, year_dir: Path) -> pd.DataFrame:
        self.logger.info(f"Extraindo metadados das estações (Ano-Base: {year_dir.name})...")
        dfs = []
        csv_files = list(year_dir.rglob("*_SP_*.csv")) + list(year_dir.rglob("*_SP_*.CSV"))

        for path in csv_files:
            meta = []
            try:
                with open(path, "r", encoding="latin-1") as f:
                    for _ in range(8):
                        linha = f.readline().strip()
                        if ";" in linha: meta.append(linha)
            except Exception:
                with open(path, "r", encoding="cp1252") as f:
                    for _ in range(8):
                        linha = f.readline().strip()
                        if ";" in linha: meta.append(linha)

            dados = {}
            for linha in meta:
                # Divide apenas no primeiro ";" para não quebrar datas
                chave, valor = linha.split(";", 1)
                # Remove pontuações e acentos para padronizar
                chave = chave.replace(":", "").replace("Ç", "C").replace("Ã", "A").strip().upper()
                dados[chave] = valor.strip()

            dfs.append(pd.DataFrame([dados]))

        if not dfs:
            return pd.DataFrame()

        df_meta_all = pd.concat(dfs, ignore_index=True)

        # Renomeia para bater com o banco
        df_meta_all.rename(columns={'CODIGO (WMO)': 'CODIGO'}, inplace=True)
        
        cols_esperadas = ['ESTACAO', 'CODIGO', 'LATITUDE', 'LONGITUDE', 'ALTITUDE', 'DATA DE FUNDACAO']
        cols_presentes = [c for c in cols_esperadas if c in df_meta_all.columns]
        df_estacao = df_meta_all[cols_presentes].copy()

        # Limpeza numérica
        for col in ['LATITUDE', 'LONGITUDE', 'ALTITUDE']:
            if col in df_estacao.columns:
                df_estacao[col] = df_estacao[col].astype(str).str.replace(",", ".").apply(pd.to_numeric, errors='coerce')

        # Limpeza de Data
        if 'DATA DE FUNDACAO' in df_estacao.columns:
            df_estacao['DATA DE FUNDACAO'] = pd.to_datetime(df_estacao['DATA DE FUNDACAO'], errors='coerce', dayfirst=True)

        return df_estacao.drop_duplicates(subset=['CODIGO']).dropna(subset=['CODIGO'])

    def _parse_single_csv(self, path: Path) -> pd.DataFrame:
        cod = path.name.split('_')[3]
        try:
            df = pd.read_csv(path, encoding='latin-1', sep=';', skiprows=8).dropna(axis=1, how='all')
        except:
            df = pd.read_csv(path, encoding='cp1252', sep=';', skiprows=8).dropna(axis=1, how='all')

        cols_originais = df.columns.tolist()
        
        def find_col(keywords, exclude=None):
            for i, c in enumerate(cols_originais):
                c_norm = self._normalize_col(c)
                if all(k in c_norm for k in keywords):
                    if exclude and any(e in c_norm for e in exclude): continue
                    return i
            return None

        mapping = {
            "DATA_RAW": find_col(["DATA"]),
            "HORA_RAW": find_col(["HORA"]),
            "PRECIPITACAO": find_col(["PRECIPIT"]),
            "PRESSAO_ATM": find_col(["PRESSAO", "NIVEL"], exclude=["MAX", "MIN"]),
            "RADIACAO": find_col(["RADIACAO"]),
            "TEMP_AR": find_col(["TEMPERATURA", "BULBO"]),
            "TEMP_MAX": find_col(["TEMPERATURA", "MAX"]),
            "TEMP_MIN": find_col(["TEMPERATURA", "MIN"]),
            "UMID_MAX": find_col(["UMIDADE", "MAX"]),
            "UMID_MIN": find_col(["UMIDADE", "MIN"]),
            "UMID_AR": find_col(["UMIDADE", "RELATIVA"], exclude=["MAX", "MIN"]),
        }

        if mapping["DATA_RAW"] is None or mapping["HORA_RAW"] is None:
            return pd.DataFrame()

        valid_map = {k: v for k, v in mapping.items() if v is not None}
        df = df.iloc[:, list(valid_map.values())]
        df.columns = list(valid_map.keys())

        for col in df.columns:
            if col not in ["DATA_RAW", "HORA_RAW"]:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
                df.loc[df[col] <= -9999, col] = np.nan

        h_limpa = df["HORA_RAW"].astype(str).str.replace(r'[:\sUTC]', '', regex=True).str.zfill(4)
        df['DATA_HORA'] = pd.to_datetime(df["DATA_RAW"].astype(str) + ' ' + h_limpa, errors='coerce')
        
        mask = df['DATA_HORA'].isna()
        if mask.any():
            df.loc[mask, 'DATA_HORA'] = pd.to_datetime(
                df.loc[mask, "DATA_RAW"].astype(str) + ' ' + h_limpa.loc[mask], 
                dayfirst=True, errors='coerce'
            )

        df['CODIGO_ESTACAO'] = cod
        return df.drop(columns=["DATA_RAW", "HORA_RAW"]).dropna(subset=['DATA_HORA'])

    def _upsert_hourly(self, df: pd.DataFrame):
        cols_order = [
            "PRECIPITACAO", "PRESSAO_ATM", "RADIACAO", "TEMP_AR", "TEMP_MAX", 
            "TEMP_MIN", "UMID_MAX", "UMID_MIN", "UMID_AR", "DATA_HORA", "CODIGO_ESTACAO"
        ]
        for c in cols_order:
            if c not in df.columns: df[c] = np.nan
            
        df_copy = df[cols_order].copy()
        for c in df_copy.columns:
            df_copy[c] = df_copy[c].astype(str).replace(['nan', 'None', 'NaT'], None)

        conn = psycopg2.connect(**self._db_conn_params)
        try:
            with conn.cursor() as cur:
                cur.execute('SET search_path TO stg, public;')
                cur.execute('TRUNCATE TABLE stg_dados_inmet_horarios;')
                buf = io.StringIO()
                df_copy.to_csv(buf, index=False, header=False, sep='\t', na_rep='\\N')
                buf.seek(0)
                cur.copy_from(buf, 'stg_dados_inmet_horarios', sep='\t', null='\\N', columns=cols_order)
            conn.commit()
        finally: conn.close()

        update_cols = [c for c in cols_order if c not in ["DATA_HORA", "CODIGO_ESTACAO"]]
        update_stmt = ", ".join([f'"{c}" = EXCLUDED."{c}"' for c in update_cols])
        
        select_stmt = """
            "PRECIPITACAO"::DOUBLE PRECISION, "PRESSAO_ATM"::DOUBLE PRECISION, 
            "RADIACAO"::DOUBLE PRECISION, "TEMP_AR"::DOUBLE PRECISION, 
            "TEMP_MAX"::DOUBLE PRECISION, "TEMP_MIN"::DOUBLE PRECISION, 
            "UMID_MAX"::DOUBLE PRECISION, "UMID_MIN"::DOUBLE PRECISION, 
            "UMID_AR"::DOUBLE PRECISION, "DATA_HORA"::TIMESTAMP, "CODIGO_ESTACAO"::VARCHAR
        """

        upsert_query = f"""
            INSERT INTO public.dados_inmet_horarios ({", ".join([f'"{c}"' for c in cols_order])})
            SELECT {select_stmt} FROM stg.stg_dados_inmet_horarios
            ON CONFLICT ("DATA_HORA", "CODIGO_ESTACAO") DO UPDATE SET {update_stmt};
        """
        with self.engine.begin() as conn:
            conn.execute(text(upsert_query))

    def _download_and_unzip(self, year: int):
        zip_path = self.zip_dir / f"{year}.zip"
        url = f"https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip"
        if not zip_path.exists():
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            with open(zip_path, "wb") as f: f.write(r.content)
        
        # Ignora arquivos já extraídos
        target_dir = self.raw_dir / str(year)
        if not target_dir.exists():
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(target_dir)

    def run(self):
        self._init_db_schema()
        metadata_extracted = False
        
        for year in range(self.start_year, self.end_year + 1):
            try:
                self.logger.info(f"Processando Ano: {year}")
                self._download_and_unzip(year)
                year_dir = self.raw_dir / str(year)
                
                # --- NOVO: Extrai estações apenas do último ano da fila ---
                if not metadata_extracted and year == self.end_year:
                    df_estacoes = self._extract_metadata(year_dir)
                    if not df_estacoes.empty:
                        self.logger.info(f"Carregando metadados de {len(df_estacoes)} estações no banco...")
                        
                        # Limpa tabela mantendo a estrutura e insere novos dados
                        with self.engine.begin() as conn:
                            conn.execute(text("TRUNCATE TABLE dados_estacoes CASCADE;"))
                        df_estacoes.to_sql("dados_estacoes", self.engine, if_exists="append", index=False)
                        
                    metadata_extracted = True
                # ---------------------------------------------------------

                csv_files = list(year_dir.rglob("*_SP_*.csv")) + list(year_dir.rglob("*_SP_*.CSV"))
                
                all_dfs = []
                for f in tqdm(csv_files, desc=f"Lendo CSVs {year}"):
                    df_tmp = self._parse_single_csv(f)
                    if not df_tmp.empty: all_dfs.append(df_tmp)
                
                if all_dfs:
                    final_year_df = pd.concat(all_dfs, ignore_index=True)
                    self._upsert_hourly(final_year_df)
                    self.logger.info(f"Carregadas {len(final_year_df):,} linhas de clima em {year}")
                
                shutil.rmtree(year_dir)
            except Exception as e:
                self.logger.error(f"Erro no ano {year}: {e}")

        if self.delete_local: shutil.rmtree(self.base_dir)

if __name__ == "__main__":
    # Ajuste o range de anos conforme necessidade do projeto.
    etl = ETL_INMET(start_year=2007, end_year=2026, delete_local=True)
    etl.run()