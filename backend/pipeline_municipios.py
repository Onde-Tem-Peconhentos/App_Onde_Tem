# pipeline_municipios.py
import pandas as pd
from models import engine

# ajuste o nome do arquivo se for diferente
CAMINHO_CSV_MUN = "dados_brutos/municipios_sp.csv"


def importa_municipios():
    # sep=None + engine="python" -> pandas tenta adivinhar o separador (vírgula, ponto-e-vírgula, etc)
    df = pd.read_csv(
        CAMINHO_CSV_MUN,
        sep=None,
        engine="python",
        dtype=str,
        encoding="utf-8",
    )

    print("Colunas encontradas no CSV de municípios:")
    print(df.columns)

    # CASO 1: veio tudo grudado em uma coluna só, tipo "Código Município Completo,Nome_Município"
    if (
        len(df.columns) == 1
        and "Código Município Completo" in df.columns[0]
        and "Nome_Município" in df.columns[0]
    ):
        col_unica = df.columns[0]
        # divide essa coluna em duas pelo primeiro separador (vírgula)
        df[["Código Município Completo", "Nome_Município"]] = df[col_unica].str.split(
            ",", n=1, expand=True
        )
        df = df[["Código Município Completo", "Nome_Município"]]

    # CASO 2: já vieram duas colunas bonitinhas -> só segue
    # renomeia para nomes mais simples
    df = df.rename(
        columns={
            "Código Município Completo": "cod_mun7",
            "Nome_Município": "nome",
        }
    )

    # garante que essas colunas existem
    if "cod_mun7" not in df.columns or "nome" not in df.columns:
        raise ValueError(
            f"Não encontrei. Colunas atuais: {df.columns}"
        )

    # mantém só o que importa
    df = df[["cod_mun7", "nome"]].copy()

    # deixa só dígitos e limita a 7 caracteres (código IBGE 7 dígitos)
    df["cod_mun7"] = df["cod_mun7"].str.replace(r"\D", "", regex=True).str[:7]

    # remove linhas sem código
    df = df.dropna(subset=["cod_mun7"])
    df = df[df["cod_mun7"] != ""]

    # converte para int
    df["cod_mun7"] = df["cod_mun7"].astype(int)

    # adiciona UF fixa SP
    df["uf"] = "SP"

    # grava no banco na tabela "municipios"
    df.to_sql(
        "municipios",
        con=engine,
        if_exists="append",  # se rodar de novo, vai tentar inserir de novo (cuidado com duplicados)
        index=False,
    )

    print(f"Importados {len(df)} municípios para a tabela 'municipios'.")


if __name__ == "__main__":
    importa_municipios()
