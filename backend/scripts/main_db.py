import sys
from pathlib import Path

from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from db.models import Base, engine
from pipelines.pipeline_municipios import importa_municipios
from pipelines.pipeline_acidentes import processa_todos_os_anos
from pipelines.pipeline_postos import importar_postos

def criar_resumos_dashboard():
    print("\nCriando tabelas resumo do dashboard (pré-agregação)...")

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS dashboard_metrics"))
        conn.execute(text("DROP TABLE IF EXISTS dashboard_casos_por_ano"))
        conn.execute(text("DROP TABLE IF EXISTS dashboard_por_animal"))
        conn.execute(text("DROP TABLE IF EXISTS dashboard_por_gravidade"))

        conn.execute(
            text(
                """
                CREATE TABLE dashboard_metrics (
                  totalCasos INTEGER,
                  totalObitos INTEGER,
                  taxaObitos DOUBLE PRECISION,
                  tempoAtendimento DOUBLE PRECISION
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE dashboard_casos_por_ano (
                  ano INTEGER,
                  total INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE dashboard_por_animal (
                  animal TEXT,
                  total INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE dashboard_por_gravidade (
                  classificacao TEXT,
                  total INTEGER
                )
                """
            )
        )

        conn.execute(
            text(
                """
                INSERT INTO dashboard_metrics(totalCasos, totalObitos, taxaObitos, tempoAtendimento)
                SELECT
                  totalCasos,
                  totalObitos,
                  CASE WHEN totalCasos > 0 THEN ROUND(totalObitos * 100.0 / totalCasos, 2) ELSE 0 END,
                  tempoAtendimento
                FROM (
                  SELECT
                    (SELECT COUNT(id) FROM acidentes) AS totalCasos,
                    (SELECT COALESCE(SUM(CASE WHEN evolucao IN ('2','3') THEN 1 ELSE 0 END),0) FROM acidentes) AS totalObitos,
                                        (SELECT ROUND(AVG(CAST(REPLACE(tempo_atendimento_desc, ',', '.') AS NUMERIC)), 2)
                       FROM acidentes
                      WHERE tempo_atendimento_desc IS NOT NULL
                        AND tempo_atendimento_desc NOT LIKE '%-%'
                        AND tempo_atendimento_desc NOT LIKE '%h%'
                        AND tempo_atendimento_desc NOT LIKE '%H%'
                    ) AS tempoAtendimento
                ) t
                """
            )
        )

        conn.execute(
            text(
                """
                INSERT INTO dashboard_casos_por_ano(ano, total)
                SELECT ano_dado, COUNT(id)
                FROM acidentes
                WHERE ano_dado IS NOT NULL
                GROUP BY ano_dado
                ORDER BY ano_dado
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO dashboard_por_animal(animal, total)
                SELECT animal_tipo_desc, COUNT(id)
                FROM acidentes
                WHERE animal_tipo_desc IS NOT NULL
                GROUP BY animal_tipo_desc
                ORDER BY animal_tipo_desc
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO dashboard_por_gravidade(classificacao, total)
                SELECT classificacao_final_desc, COUNT(id)
                FROM acidentes
                WHERE classificacao_final_desc IS NOT NULL
                GROUP BY classificacao_final_desc
                ORDER BY classificacao_final_desc
                """
            )
        )

    print("Tabelas resumo criadas.")


def criar_indices():
    print("\nCriando índices no banco (otimização de consultas)...")
    comandos = [
        "CREATE INDEX IF NOT EXISTS ix_acidentes_animal_desc ON acidentes (animal_tipo_desc);",
        "CREATE INDEX IF NOT EXISTS ix_acidentes_classificacao_desc ON acidentes (classificacao_final_desc);",
        "CREATE INDEX IF NOT EXISTS ix_acidentes_evolucao ON acidentes (evolucao);",
        "CREATE INDEX IF NOT EXISTS ix_municipios_nome ON municipios (nome);",
        "CREATE INDEX IF NOT EXISTS ix_acidentes_mun_ano ON acidentes (municipio_acidente, ano_dado);",
        "CREATE INDEX IF NOT EXISTS ix_acidentes_mun_ano_animal ON acidentes (municipio_acidente, ano_dado, animal_tipo_desc);",
    ]

    with engine.begin() as conn:
        for sql in comandos:
            conn.execute(text(sql))
        conn.execute(text("ANALYZE"))

    print("✅ Índices criados com sucesso.")


def recriar_banco():
    print("\nRecriando schema do banco...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Schema recriado com sucesso.")


def main():
    print("--- INICIANDO PROCESSO TOTAL ---\n")
    recriar_banco()

    print("\nImportando municípios...")
    importa_municipios()

    print("\nImportando acidentes...")
    processa_todos_os_anos()

    print("\nImportando postos...")
    importar_postos()

    criar_indices()
    criar_resumos_dashboard()

    print("\n PROCESSO CONCLUÍDO! TODOS OS DADOS IMPORTADOS. ")


if __name__ == "__main__":
    main()
