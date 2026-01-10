import os
import sys
import time
import sqlite3

ARQUIVO_DB = "sinan.db"

import sqlite3

def criar_resumos_dashboard():
    print("\nCriando tabelas resumo do dashboard (pré-agregação)...")
    conn = sqlite3.connect(ARQUIVO_DB)
    cur = conn.cursor()

    # apaga se existir (pra recriar limpo)
    cur.executescript("""
    DROP TABLE IF EXISTS dashboard_metrics;
    DROP TABLE IF EXISTS dashboard_casos_por_ano;
    DROP TABLE IF EXISTS dashboard_por_animal;
    DROP TABLE IF EXISTS dashboard_por_gravidade;
    """)

    # cria tabelas
    cur.executescript("""
    CREATE TABLE dashboard_metrics (
      totalCasos INTEGER,
      totalObitos INTEGER,
      taxaObitos REAL,
      tempoAtendimento REAL
    );

    CREATE TABLE dashboard_casos_por_ano (
      ano INTEGER,
      total INTEGER
    );

    CREATE TABLE dashboard_por_animal (
      animal TEXT,
      total INTEGER
    );

    CREATE TABLE dashboard_por_gravidade (
      classificacao TEXT,
      total INTEGER
    );
    """)

    # popula métricas (nota: tempoAtendimento segue sua regra atual de filtrar strings)
    cur.executescript("""
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
        (SELECT ROUND(AVG(CAST(REPLACE(tempo_atendimento_desc, ',', '.') AS REAL)), 2)
           FROM acidentes
          WHERE tempo_atendimento_desc IS NOT NULL
            AND tempo_atendimento_desc NOT LIKE '%-%'
            AND tempo_atendimento_desc NOT LIKE '%h%'
            AND tempo_atendimento_desc NOT LIKE '%H%'
        ) AS tempoAtendimento
    );
    """)

    # popula gráficos
    cur.executescript("""
    INSERT INTO dashboard_casos_por_ano(ano, total)
    SELECT ano_dado, COUNT(id)
    FROM acidentes
    WHERE ano_dado IS NOT NULL
    GROUP BY ano_dado
    ORDER BY ano_dado;

    INSERT INTO dashboard_por_animal(animal, total)
    SELECT animal_tipo_desc, COUNT(id)
    FROM acidentes
    WHERE animal_tipo_desc IS NOT NULL
    GROUP BY animal_tipo_desc
    ORDER BY animal_tipo_desc;

    INSERT INTO dashboard_por_gravidade(classificacao, total)
    SELECT classificacao_final_desc, COUNT(id)
    FROM acidentes
    WHERE classificacao_final_desc IS NOT NULL
    GROUP BY classificacao_final_desc
    ORDER BY classificacao_final_desc;
    """)

    conn.commit()
    conn.close()
    print("Tabelas resumo criadas.")

def criar_indices():
    print("\nCriando índices no banco (otimização de consultas)...")
    conn = sqlite3.connect(ARQUIVO_DB)
    cur = conn.cursor()

    comandos = [
        "CREATE INDEX IF NOT EXISTS ix_acidentes_animal_desc ON acidentes (animal_tipo_desc);",
        "CREATE INDEX IF NOT EXISTS ix_acidentes_classificacao_desc ON acidentes (classificacao_final_desc);",
        "CREATE INDEX IF NOT EXISTS ix_acidentes_evolucao ON acidentes (evolucao);",
        "CREATE INDEX IF NOT EXISTS ix_municipios_nome ON municipios (nome);",
        "CREATE INDEX IF NOT EXISTS ix_acidentes_mun_ano ON acidentes (municipio_acidente, ano_dado);",
        "CREATE INDEX IF NOT EXISTS ix_acidentes_mun_ano_animal ON acidentes (municipio_acidente, ano_dado, animal_tipo_desc);",
    ]

    for sql in comandos:
        cur.execute(sql)

    # Ajuda o SQLite a usar os índices melhor
    cur.execute("ANALYZE;")

    conn.commit()
    conn.close()
    print("✅ Índices criados com sucesso.")

def main():
    print("--- INICIANDO PROCESSO TOTAL ---\n")

    if os.path.exists(ARQUIVO_DB):
        print(f"  Removendo banco de dados antigo ({ARQUIVO_DB}) para garantir estrutura limpa...")
        try:
            os.remove(ARQUIVO_DB)
            print("✅ Banco antigo removido.")
        except Exception as e:
            print(f"Não foi possível remover o arquivo (ele pode estar aberto): {e}")

    scripts = [
        "models.py",
        "pipeline_municipios.py",
        "pipeline_acidentes.py",
        "pipeline_postos.py",
    ]

    for script in scripts:
        print(f"\n{'='*40}")
        print(f" RODANDO: {script}")
        print(f"{'='*40}")

        if not os.path.exists(script):
            print(f" ERRO: O arquivo '{script}' não foi encontrado nesta pasta.")
            sys.exit(1)

        codigo_erro = os.system(f'{sys.executable} {script}')

        if codigo_erro != 0:
            print(f"\nOcorreu um erro crítico no {script}. O processo foi interrompido.")
            sys.exit(1)
        else:
            print(f" {script} finalizado com sucesso.")
            time.sleep(1)

  
    criar_indices()
    criar_resumos_dashboard()

    print("\n PROCESSO CONCLUÍDO! TODOS OS DADOS IMPORTADOS. ")

if __name__ == "__main__":
    main()
