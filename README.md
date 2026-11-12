# Ensino superior no Brasil (2009–2024): Censo da Educação Superior + ENADE + IBGE

Projeto da Etapa 1: coleta → análise exploratória → limpeza/tratamento → visualizações, com base nos
microdados do INEP, integrados à população e à malha territorial do IBGE.

## Perguntas de pesquisa
1. Como evoluíram ingressantes e matrículas de graduação entre 2009 e 2024, e quanto desse crescimento veio do EAD?
2. Como o acesso (matrículas por 100 mil habitantes) varia entre UFs e regiões, e a desigualdade regional diminuiu?
3. Qual o peso da rede privada e dos programas federais (FIES, PROUNI) no acesso, e como isso mudou?
4. O perfil do ingressante mudou (sexo, cor/raça, idade 25+, escola pública)?
5. O desempenho no ENADE difere entre rede (pública × privada), modalidade (presencial × EAD) e área?

## Fontes
| Fonte | Conteúdo | Recorte | Acesso |
|---|---|---|---|
| INEP – Censo da Educação Superior | Cursos de graduação (vagas, inscritos, ingressantes, matrículas, concluintes, perfil) | 2009–2024 | [microdados](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior) |
| INEP – ENADE | Notas e presença por inscrito; perfil (sexo, idade) por curso | 2017, 2018, 2019, 2021, 2023 | [microdados](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enade) |
| IBGE – SIDRA | População residente por UF (estimativas 6579; Censos 2010 e 2022) | 2009–2024 | API SIDRA |
| IBGE – Localidades / Malhas | Tabela de municípios; malha das UFs (GeoJSON) | atual | API servicodados.ibge.gov.br |

Licença: dados abertos do Governo Federal, uso livre com citação da fonte.
Volume: cerca de 3,85 milhões de linhas de cursos no Censo e 2,42 milhões de inscritos no ENADE
(6,27 milhões de linhas analisadas; 13,6 milhões contando todos os arquivos coletados).

## Estrutura
```
data/
  bronze/   dados brutos convertidos para Parquet, particionados por ano (não versionado)
  silver/   base tratada, Parquet particionado por ano (não versionado)
  gold/     tabelas agregadas que respondem às perguntas (versionado, ~1,6 MB)
notebooks/
  censo_educacao_superior.ipynb   coleta, EDA, log de limpeza, visualizações e números-chave
src/
  config.py    caminhos, recorte e URLs
  coleta.py    download com repetição, verificação de arquivos já baixados, conversão para Parquet, metadados, benchmark
  limpeza.py   bronze → silver, gravando cada decisão em reports/log_limpeza.csv
  gold.py      silver → gold, com validação dos totais contra os números oficiais do INEP
  montar_notebook.py   gera o notebook: python src/montar_notebook.py . (depois executar com nbconvert)
reports/
  metadados_coleta.csv        URL, data, MD5, linhas/colunas, tamanho CSV × Parquet por arquivo
  benchmark_csv_parquet.csv   tempo de leitura e tamanho CSV × Parquet
  log_limpeza.csv             problema · decisão · justificativa · linhas afetadas
  relatorio.pdf               relatório final da Etapa 1 (máx. 10 páginas, padrão UTFPR)
  figuras/                    PNGs das visualizações
certs/       bundle de certificados para o download.inep.gov.br (ver abaixo)
```

## Como reproduzir
Requer Python 3.12 e cerca de 8 GB de RAM livre. O DuckDB é limitado a 4 GB e grava o excedente em `data/_duckdb_tmp`.
São cerca de 1 GB de download e 4 GB de disco durante a coleta.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python src/coleta.py --benchmark   # bronze + reports/metadados_coleta.csv + benchmark (≈ 15–30 min, depende da rede)
python src/limpeza.py              # silver + reports/log_limpeza.csv (≈ 3–5 min)
python src/gold.py                 # gold (segundos)
jupyter nbconvert --to notebook --execute --inplace notebooks/censo_educacao_superior.ipynb
```

Opções da coleta: `--so-download` só baixa os ZIPs; `--manter-csv` mantém os CSVs extraídos;
`--so-benchmark` refaz só o benchmark sobre CSVs mantidos; `--so-malha` baixa só a malha de UFs.
A coleta pula arquivos já baixados, então pode ser interrompida e retomada.

### Observação sobre o certificado do INEP
O servidor `download.inep.gov.br` não envia o certificado intermediário (RNP ICPEdu, emitido pela GlobalSign).
Em vez de desligar a verificação TLS, `coleta.py` baixa o intermediário oficial pela URL AIA do próprio
certificado e monta um bundle em `certs/`. A verificação continua ativa.

## Principais decisões de limpeza
Lista completa em `reports/log_limpeza.csv`.
- **EAD em duas dimensões geográficas**: as linhas "somente nível Brasil" (TP_DIMENSAO = 3) ficam fora das somas de alunos
  para evitar dupla contagem. Vagas e inscritos do EAD vêm justamente dessa dimensão.
- **Categoria administrativa de 2009** (6 particular, 8 comunitária, 9 confessional): cada IES herda a categoria que declarou em 2010.
  Mapear "particular" direto para "com fins lucrativos" criava uma queda falsa de 3,4 para 2,1 milhões de matrículas.
- **Rede vazia em 2013**: derivada da categoria administrativa, relação sem exceções nos demais anos.
- **Escola de origem**: em 2009 o campo vem zerado, porque não foi coletado, e vira NULL; o percentual usa só ingressantes com origem informada.
- **Cursos sequenciais** removidos (fora do escopo de graduação). Outliers de matrícula são mantidos e marcados (regra IQR em log1p).
- **ENADE**: ausentes e eliminados ficam marcados (`fl_nota_valida`) e fora das médias; notas com vírgula convertidas para número.
- **Integração**: Censo × população IBGE pela chave UF × ano (população de 2023 interpolada); ENADE × Censo pela chave curso × ano.

Validação: as matrículas e os ingressantes da silver coincidem com os totais divulgados pelo INEP para 2019, 2022 e 2023.
