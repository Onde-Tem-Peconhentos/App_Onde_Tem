# pipeline_acidentes.py
import pandas as pd
import numpy as np
from pysus.online_data.SINAN import SINAN
from sqlalchemy.orm import sessionmaker
from models import engine 
from models import Municipio 

# ==========================================
# DICIONÁRIOS DE TRADUÇÃO
# ==========================================
# Estes dicionários traduzem os códigos numéricos do SINAN para texto legível.
# Baseado no Manual de Preenchimento do SINAN.
MAPS = {
    # Qual animal causou o acidente (TP_ACIDENT)
    "ANIMAL": {
        "1": "Serpente", "2": "Aranha", "3": "Escorpião", "4": "Lagarta",
        "5": "Abelha", "6": "Outro", "9": "Ignorado"
    },
    # Sexo do paciente (CS_SEXO)
    "SEXO": {
        "M": "Masculino", "F": "Feminino", "I": "Ignorado"
    },
    # Cor/Raça (CS_RACA) - Importante para análises sociodemográficas
    "RACA": {
        "1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda", 
        "5": "Indígena", "9": "Ignorado"
    },
    # Idade Gestacional (CS_GESTANT) - Define risco extra
    "GESTANTE": {
        "1": "1º Trimestre", "2": "2º Trimestre", "3": "3º Trimestre",
        "4": "IG Ignorada", "5": "Não", "6": "Não se aplica", "9": "Ignorado"
    },
    # Escolaridade (CS_ESCOL_N) - Indicador social
    "ESCOLARIDADE": {
        "0": "Analfabeto", "1": "1ª-4ª série inc.", "2": "4ª série comp.",
        "3": "5ª-8ª série inc.", "4": "EF completo", "5": "EM incompleto",
        "6": "EM completo", "7": "Sup. incompleto", "8": "Sup. completo",
        "9": "Ignorado", "10": "Não se aplica"
    },
    # Zona de Ocorrência (ID_ZONA) - Onde foi a picada
    # Nota: Muitos anos antigos não possuem esse dado preenchido.
    "ZONA": {
        "1": "Urbana", "2": "Rural", "3": "Periurbana", "9": "Ignorado"
    },
    # Acidente relacionado ao trabalho (TRA_REL)
    "TRABALHO": {
        "1": "Sim", "2": "Não", "9": "Ignorado"
    },
    # Recebeu soroterapia (CON_SOROTE) - Crucial para gestão de estoque
    "SOROTERAPIA": { 
        "1": "Sim", "2": "Não", "9": "Ignorado"
    },
    # Tempo entre a picada e o atendimento (TEMPO_CAP)
    # KPI CRÍTICO: Quanto maior o tempo, maior o risco de sequelas/óbito.
    "TEMPO": {
         "1": 0.5,
    "2": 2.0,
    "3": 4.5,
    "4": 9.0,
    "5": 18.0,
    "6": 24.0,
    "9": None,  # Ignorado
    },
    # Gravidade do caso (CLASSI_FIN)
    "CLASSIFICACAO": {
        "1": "Leve", "2": "Moderado", "3": "Grave", "4": "Óbito", "5": "Óbito"
    },
    # Desfecho do caso (EVOLUCAO)
    "EVOLUCAO": {
        "1": "Cura", "2": "Óbito p/ Agravo", "3": "Óbito Outras Causas", "9": "Ignorado"
    },
    # Local anatômico da picada (LOC_PICADA)
    "LOCAL_PICADA": {
        "1": "Cabeça", "2": "Braço", "3": "Antebraço", "4": "Mão",
        "5": "Dedo da Mão", "6": "Tronco", "7": "Coxa", "8": "Perna",
        "9": "Pé", "10": "Dedo do Pé", "99": "Ignorado"
    }
}

def extrai_idade_anos(cod: str):
    """
    Converte o código complexo de idade do SINAN para 'Anos' (Float).
    Lógica do SINAN:
    - Começa com 4: Idade em anos (Ex: 4030 = 30 anos)
    - Começa com 3: Idade em meses (Ex: 3009 = 9 meses = 0.75 anos)
    - Começa com 2: Idade em dias (Ex: 2020 = 20 dias)
    - Começa com 1: Idade em horas (Recém-nascido)
    """
    if pd.isna(cod): return pd.NA
    cod = str(cod).strip()
    if len(cod) < 2: return pd.NA
    try:
        unidade = cod[0]
        valor = int(cod[1:])
    except: return pd.NA
    
    if unidade == "4": return float(valor)
    elif unidade == "3": return round(valor / 12.0, 2)
    elif unidade == "2": return round(valor / 365.0, 2)
    elif unidade == "1": return round(valor / (24.0 * 365.0), 3)
    return pd.NA

def buscar_valor(df, colunas_possiveis):
    """
    Detetive de Colunas: Como o SINAN muda o nome das colunas ao longo dos anos
    (Ex: ora chama 'TP_ACIDENT', ora 'ANT_TIP_AC'), essa função tenta achar
    a primeira opção válida na lista fornecida.
    """
    for col in colunas_possiveis:
        if col in df.columns:
            # Limpa o dado: converte pra string, remove espaços e sufixos '.0'
            return df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    return pd.Series(pd.NA, index=df.index)

def aplica_mapa(series, mapa_dict):
    """Aplica o dicionário de tradução. Se o código não existir, marca como 'Outros/Ignorado'."""
    return series.map(mapa_dict).fillna("Outros/Ignorado")

def padroniza_sinan_anim(df_raw: pd.DataFrame, ano: int, mapa_conversao: dict) -> pd.DataFrame:
    """
    Função Principal: Recebe os dados brutos e sujos do SINAN e devolve
    um DataFrame limpo, traduzido e pronto para o Banco de Dados.
    """
    df = df_raw.copy()
    df.columns = df.columns.str.upper().str.strip()
    out = pd.DataFrame(index=df.index)

    # ==========================================
    # 1. DADOS DO PACIENTE
    # ==========================================
    out["sexo"] = buscar_valor(df, ["CS_SEXO"])
    out["sexo_desc"] = aplica_mapa(out["sexo"], MAPS["SEXO"])
    
    out["raca"] = buscar_valor(df, ["CS_RACA", "CS_RACA_N"])
    out["raca_desc"] = aplica_mapa(out["raca"], MAPS["RACA"])
    
    out["escolaridade"] = buscar_valor(df, ["CS_ESCOL_N", "CS_ESCOL"])
    out["escolaridade_desc"] = aplica_mapa(out["escolaridade"], MAPS["ESCOLARIDADE"])
    
    out["gestante"] = buscar_valor(df, ["CS_GESTANT"])
    out["gestante_desc"] = aplica_mapa(out["gestante"], MAPS["GESTANTE"])
    
    col_idade = buscar_valor(df, ["NU_IDADE_N", "NU_IDADE"])
    out["idade_anos"] = col_idade.apply(extrai_idade_anos)

    # ==========================================
    # 2. DADOS TEMPORAIS
    # ==========================================
    # Tenta achar a data do acidente. Se não tiver, usa a data da notificação como fallback.
    col_data = buscar_valor(df, ["ANT_DT_ACI", "DT_ACID", "DT_NOTIFIC"])
    dts = pd.to_datetime(col_data, errors="coerce")
    out["data_acidente"] = dts.dt.date.where(dts.notna(), None)

    # ==========================================
    # 3. LOCAL E ZONA
    # ==========================================
    # Zona Urbana/Rural (Muitas vezes nulo em dados antigos)
    out["zona"] = buscar_valor(df, ["ANT_ZONA", "ID_ZONA", "ZONA_ACID"])
    out["zona_desc"] = aplica_mapa(out["zona"], MAPS["ZONA"])
    
    out["local_picada"] = buscar_valor(df, ["ANT_LOCA_1", "LOC_PICADA"])
    out["local_picada_desc"] = aplica_mapa(out["local_picada"], MAPS["LOCAL_PICADA"])

    # ==========================================
    # 4. MUNICÍPIO (CRÍTICO PARA MAPAS)
    # ==========================================
    # O SINAN usa IBGE de 6 dígitos, mas o padrão oficial (e nossa tabela) é 7.
    muni_raw = buscar_valor(df, ["ANT_MUNIC_", "ID_MUNICIP", "ANT_MUNIC"])
    muni_clean = muni_raw.str.replace(r"\D", "", regex=True)
    
    def traduzir_ibge(cod_str):
        # Converte 6 dígitos -> 7 dígitos usando o cache do banco
        if not cod_str or pd.isna(cod_str) or cod_str == 'nan': return None
        if len(cod_str) == 7: return mapa_conversao.get(cod_str)
        return mapa_conversao.get(cod_str[:6])
        
    out["municipio_acidente"] = muni_clean.apply(traduzir_ibge)

    # ==========================================
    # 5. O ACIDENTE (ANIMAL)
    # ==========================================
    out["animal_tipo"] = buscar_valor(df, ["TP_ACIDENT"])
    out["animal_tipo_desc"] = aplica_mapa(out["animal_tipo"], MAPS["ANIMAL"])
    
    out["acidente_trabalho"] = buscar_valor(df, ["DOENCA_TRA", "TRA_REL", "ANT_TRAB"])
    out["acidente_trabalho_desc"] = aplica_mapa(out["acidente_trabalho"], MAPS["TRABALHO"])

    # ==========================================
    # 6. CLÍNICA E TRATAMENTO
    # ==========================================
    # Paciente tomou soro?
    out["con_sorote"] = buscar_valor(df, ["CON_SOROTE", "ANT_SORO"]) 
    out["con_sorote_desc"] = aplica_mapa(out["con_sorote"], MAPS["SOROTERAPIA"]) 

    # Quanto tempo demorou para chegar no hospital?
    out["tempo_atendimento"] = buscar_valor(df, ["ANT_TEMPO_", "TEMPO_CAP", "ANT_TEMPO"])

# tempo médio em horas usando o MAPS["TEMPO_MEDIO"]
    out["tempo_atendimento_desc"] = (
        out["tempo_atendimento"]
            .map(MAPS["TEMPO"])   # usa o dicionário que você criou
            .astype(float)
    )
    
    # Gravidade
    out["classificacao_final"] = buscar_valor(df, ["TRA_CLASSI", "CLASSI_FIN", "ANT_CLASS"])
    out["classificacao_final_desc"] = aplica_mapa(out["classificacao_final"], MAPS["CLASSIFICACAO"])
    
    # O paciente viveu ou morreu?
    out["evolucao"] = buscar_valor(df, ["EVOLUCAO", "ANT_EVOL"])
    out["evolucao_desc"] = aplica_mapa(out["evolucao"], MAPS["EVOLUCAO"])
    
    out["ano_dado"] = int(ano)

    # Definição final das colunas que vão para o SQLite
    colunas_finais = [
        "sexo", "sexo_desc", "idade_anos", "raca", "raca_desc", 
        "escolaridade", "escolaridade_desc", "gestante", "gestante_desc",
        "data_acidente", "municipio_acidente", 
        "zona", "zona_desc", "local_picada", "local_picada_desc",
        "animal_tipo", "animal_tipo_desc", "acidente_trabalho", "acidente_trabalho_desc",
        "con_sorote", "con_sorote_desc", 
        "tempo_atendimento", "tempo_atendimento_desc", 
        "classificacao_final", "classificacao_final_desc", 
        "evolucao", "evolucao_desc", "ano_dado"
    ]
    return out[colunas_finais]

def importar_df_anim_para_db(df: pd.DataFrame):
    """Insere o DataFrame tratado no banco, ignorando linhas sem município."""
    df_validos = df.dropna(subset=['municipio_acidente'])
    if not df_validos.empty:
        df_validos.to_sql("acidentes", con=engine, if_exists="append", index=False)

def processa_todos_os_anos():
    # 1. Carrega mapa de municípios para memória (Performance)
    print("--- Preparando Cache de Municípios ---")
    Session = sessionmaker(bind=engine)
    session = Session()
    mapa_ibge = {}
    try:
        todos = session.query(Municipio.cod_mun7).all()
        for (cod,) in todos:
            mapa_ibge[str(cod)[:6]] = cod # Chave de 6 digitos
            mapa_ibge[str(cod)] = cod     # Chave de 7 digitos
    except Exception as e:
        print(f"Erro no banco: {e}"); return
    finally: session.close()

    sinan = SINAN().load()
    # Range de anos a processar
    anos = range(2007, 2026) 

    print("\n--- Iniciando Pipeline---")
    for ano in anos:
        print(f"{ano}...", end=" ")
        try:
            files = sinan.get_files("ANIM", ano)
            if not files: print("Sem arq."); continue
            df_raw = sinan.download(files).to_dataframe()
        except: print("Falha."); continue

        df_raw.columns = df_raw.columns.str.upper().str.strip()
        
        # Filtra apenas ocorrências no estado de SP (Código 35)
        cond = pd.Series(False, index=df_raw.index)
        for c in ["SG_UF_NOT", "ANT_UF", "SG_UF"]: 
            if c in df_raw.columns: cond |= df_raw[c].astype(str).str.strip() == "35"
        for c in ["ANT_MUNIC_", "ID_MUNICIP"]:
            if c in df_raw.columns: cond |= df_raw[c].astype(str).str.strip().str.startswith("35")

        df_sp = df_raw[cond].copy()
        if df_sp.empty: print("Vazio."); continue

        # Processa e salva
        df_clean = padroniza_sinan_anim(df_sp, ano, mapa_ibge)
        importar_df_anim_para_db(df_clean)
        print(f"{len(df_clean)} regs.")

if __name__ == "__main__":
    processa_todos_os_anos()