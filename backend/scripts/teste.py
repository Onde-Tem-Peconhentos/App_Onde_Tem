import sys
from pathlib import Path

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from db.models import Acidente, Municipio, Posto, engine

Session = sessionmaker(bind=engine)
session = Session()


def imprimir_titulo(texto):
    print(f"\n{'='*50}")
    print(f"🧪 {texto}")
    print(f"{'='*50}")


def run_tests():
    # ---------------------------------------------------------
    # TESTE 1: Contagem Geral
    # ---------------------------------------------------------
    imprimir_titulo("TESTE 1: Visão Geral do Banco")

    qtd_cidades = session.query(Municipio).count()
    qtd_postos = session.query(Posto).count()
    qtd_acidentes = session.query(Acidente).count()

    print(f"🏙️  Total de Municípios: {qtd_cidades}")
    print(f"🏥 Total de Postos:     {qtd_postos}")
    print(f"🚑 Total de Acidentes:  {qtd_acidentes}")

    if qtd_postos == 0:
        print("❌ AVISO: A tabela de postos está vazia! Algo deu errado na importação.")
        return

    # ---------------------------------------------------------
    # TESTE 2: A Prova de Fogo (Múltiplos Postos)
    # Vamos buscar cidades que tenham mais de 1 posto para provar que o UNIQUE sumiu
    # ---------------------------------------------------------
    imprimir_titulo("TESTE 2: Relação 1-para-Muitos (Cidades com vários postos)")

    # Subquery para achar cidades com contagem > 1
    cidades_multiplas = (
        session.query(Municipio)
        .join(Posto)
        .group_by(Municipio.id)
        .having(func.count(Posto.id) > 1)
        .order_by(func.count(Posto.id).desc())
        .limit(3)
        .all()
    )

    if not cidades_multiplas:
        print("⚠️ Não encontrei cidades com múltiplos postos (pode ser normal se o CSV for pequeno).")
        # Fallback: Pega qualquer cidade com posto
        cidade_teste = session.query(Municipio).join(Posto).first()
        lista_cidades = [cidade_teste] if cidade_teste else []
    else:
        lista_cidades = cidades_multiplas

    for cidade in lista_cidades:
        print(f"\n📍 Cidade: {cidade.nome} (UF: {cidade.uf})")
        print(f"   Código IBGE: {cidade.cod_mun7}")
        print(f"   Quantidade de Postos: {len(cidade.postos)}")

        # Listar os postos dessa cidade
        for i, posto in enumerate(cidade.postos, 1):
            print(f"   ├─ Posto {i}: {posto.endereco}")
            status = "✅ Aberto 24h" if posto.aberto_24h else "🕒 Horário Comercial"
            print(f"   └─ {status}")

    # ---------------------------------------------------------
    # TESTE 3: Filtros Inteligentes (Quem tem soro para escorpião?)
    # ---------------------------------------------------------
    imprimir_titulo("TESTE 3: Buscando Postos com Soro Antiescorpiônico")

    postos_escorpiao = (
        session.query(Posto)
        .filter(Posto.escorpionico == 1)  # ou True, dependendo do banco
        .limit(5)
        .all()
    )

    for posto in postos_escorpiao:
        # Aqui testamos a relação REVERSA (acessar .municipio a partir do posto)
        nome_cidade = posto.municipio.nome if posto.municipio else "Desconhecido"
        print(f"🦂 {nome_cidade}: {posto.endereco}")

    # ---------------------------------------------------------
    # TESTE 4: Cruzando Dados (Acidentes x Postos)
    # ---------------------------------------------------------
    imprimir_titulo("TESTE 4: Integridade (Existe posto na cidade do acidente?)")

    # Pega um acidente qualquer
    acidente = session.query(Acidente).first()

    if acidente:
        print(f"Caso ID {acidente.id}: Acidente com {acidente.animal_tipo}")
        cidade_acidente = acidente.municipio

        if cidade_acidente:
            print(f"Ocorreu em: {cidade_acidente.nome}")
            num_postos = len(cidade_acidente.postos)
            print(f"Nesta cidade existem {num_postos} postos de atendimento cadastrados.")

            if num_postos > 0:
                print("✅ O paciente teria onde ser atendido nesta cidade!")
            else:
                print("⚠️ Alerta: Cidade sem postos cadastrados no sistema.")
        else:
            print("❌ Acidente sem município vinculado (chave estrangeira nula ou inválida).")
    else:
        print("Sem acidentes cadastrados para testar.")


if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n❌ Erro ao executar os testes: {e}")
        print("Dica: Verifique se o arquivo do banco de dados existe e se o db.py está configurado certo.")
