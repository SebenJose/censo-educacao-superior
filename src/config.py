"""Configurações centrais do projeto (caminhos, recorte e URLs das fontes)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
BRONZE = DATA / "bronze"
SILVER = DATA / "silver"
GOLD = DATA / "gold"
REPORTS = RAIZ / "reports"
FIGURAS = REPORTS / "figuras"
CERTS = RAIZ / "certs"

RAW_CENSO = BRONZE / "raw" / "censo"
RAW_ENADE = BRONZE / "raw" / "enade"
RAW_IBGE = BRONZE / "raw" / "ibge"

# ---------------------------------------------------------------- recorte
ANOS_CENSO = list(range(2009, 2025))          # 2009–2024 (16 anos)
ANOS_ENADE = [2017, 2018, 2019, 2021, 2023]   # 2020 e 2022 não têm microdados publicados

# ---------------------------------------------------------------- fontes
URL_CENSO = "https://download.inep.gov.br/microdados/microdados_censo_da_educacao_superior_{ano}.zip"
URL_ENADE = {
    2017: "https://download.inep.gov.br/microdados/microdados_enade_2017_LGPD.zip",
    2018: "https://download.inep.gov.br/microdados/microdados_enade_2018_LGPD.zip",
    2019: "https://download.inep.gov.br/microdados/microdados_enade_2019_LGPD.zip",
    2021: "https://download.inep.gov.br/microdados/microdados_enade_2021.zip",
    2023: "https://download.inep.gov.br/microdados/microdados_enade_2023.zip",
}
# Arquivos do ENADE usados (cada arquivo é um "bloco" de variáveis; por LGPD as linhas
# são embaralhadas entre arquivos, então a única chave comum é CO_CURSO).
ENADE_ARQUIVOS = {"arq1": "enade_curso", "arq3": "enade_desempenho", "arq5": "enade_sexo", "arq6": "enade_idade"}

# IBGE / SIDRA: população residente por UF
URL_SIDRA_ESTIMATIVAS = "https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/9324/p/all"   # estimativas anuais
URL_SIDRA_CENSO2022 = "https://apisidra.ibge.gov.br/values/t/4709/n3/all/v/93/p/2022"       # Censo 2022
URL_SIDRA_CENSO2010 = "https://apisidra.ibge.gov.br/values/t/1378/n3/all/v/93/p/2010/c1/0/c2/0/c287/0/c455/0"  # Censo 2010
URL_IBGE_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
URL_IBGE_MALHA_UF = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
                     "?formato=application/vnd.geo%2Bjson&qualidade=minima&intrarregiao=UF")

# O servidor download.inep.gov.br não envia o certificado intermediário (RNP ICPEdu,
# emitido pela GlobalSign). Baixamos o intermediário oficial pela URL AIA do próprio
# certificado e montamos um bundle — a verificação TLS continua ativa.
URL_CERT_INTERMEDIARIO = "http://secure.globalsign.com/cacert/rnpicpedugr46ovtlsca2025.crt"
CA_BUNDLE = CERTS / "inep_ca_bundle.pem"

UFS = {
    11: ("RO", "Rondônia", "Norte"), 12: ("AC", "Acre", "Norte"), 13: ("AM", "Amazonas", "Norte"),
    14: ("RR", "Roraima", "Norte"), 15: ("PA", "Pará", "Norte"), 16: ("AP", "Amapá", "Norte"),
    17: ("TO", "Tocantins", "Norte"), 21: ("MA", "Maranhão", "Nordeste"), 22: ("PI", "Piauí", "Nordeste"),
    23: ("CE", "Ceará", "Nordeste"), 24: ("RN", "Rio Grande do Norte", "Nordeste"),
    25: ("PB", "Paraíba", "Nordeste"), 26: ("PE", "Pernambuco", "Nordeste"), 27: ("AL", "Alagoas", "Nordeste"),
    28: ("SE", "Sergipe", "Nordeste"), 29: ("BA", "Bahia", "Nordeste"), 31: ("MG", "Minas Gerais", "Sudeste"),
    32: ("ES", "Espírito Santo", "Sudeste"), 33: ("RJ", "Rio de Janeiro", "Sudeste"),
    35: ("SP", "São Paulo", "Sudeste"), 41: ("PR", "Paraná", "Sul"), 42: ("SC", "Santa Catarina", "Sul"),
    43: ("RS", "Rio Grande do Sul", "Sul"), 50: ("MS", "Mato Grosso do Sul", "Centro-Oeste"),
    51: ("MT", "Mato Grosso", "Centro-Oeste"), 52: ("GO", "Goiás", "Centro-Oeste"),
    53: ("DF", "Distrito Federal", "Centro-Oeste"),
}
