"""Dicionário de dados da camada silver (variáveis usadas no projeto).

Gera reports/dicionario_dados.csv e reports/dicionario_dados.md com, para cada variável:
tabela, nome tratado, nome original na fonte, tipo, descrição, domínio e % de nulos.
Descrições e domínios de códigos seguem o layout dos microdados do INEP (Censo da Educação
Superior e ENADE) e do IBGE; intervalos numéricos e % de nulos são medidos na própria silver.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from limpeza import ROTULOS, PRESENCA  # noqa: E402

TABELAS = {
    "censo_cursos": ("Censo da Educação Superior (INEP) – 1 linha por curso × município × dimensão × ano",
                     f"read_parquet('{C.SILVER}/censo_cursos/*/*.parquet', hive_partitioning=true)"),
    "enade_desempenho": ("ENADE (INEP) – 1 linha por inscrito, enriquecida com atributos do curso",
                         f"read_parquet('{C.SILVER}/enade_desempenho/*/*.parquet', hive_partitioning=true)"),
    "enade_perfil_curso": ("ENADE (INEP) – perfil agregado por curso × ano (arquivos LGPD de sexo e idade)",
                           f"read_parquet('{C.SILVER}/enade_perfil_curso/*/*.parquet', hive_partitioning=true)"),
    "populacao_uf": ("IBGE – população residente por UF × ano", f"'{C.SILVER}/populacao_uf.parquet'"),
    "municipios": ("IBGE – tabela de municípios", f"'{C.SILVER}/municipios.parquet'"),
}

cod = lambda m: "; ".join(f"{k} = {v}" for k, v in m.items())  # noqa: E731

# ---------------------------------------------------------------- descrições (nome tratado → (original, descrição, domínio))
D = {
    # identificação / geografia
    "ano": ("NU_ANO_CENSO / NU_ANO", "Ano de referência do Censo ou do ENADE (partição)", None),
    "co_uf": ("CO_UF", "Código IBGE da UF de oferta do curso", "11–53 (código IBGE); 0 ou nulo = sem UF (EAD nível Brasil ou exterior)"),
    "sg_uf": ("SG_UF (recalculada)", "Sigla da UF, recalculada a partir do código IBGE", "27 siglas; EX = exterior; NI = não informado"),
    "no_uf": ("derivada", "Nome da UF", "27 UFs; Exterior; Não informado"),
    "no_regiao": ("derivada / CO_REGIAO_CURSO", "Grande região do IBGE", "Norte; Nordeste; Sudeste; Sul; Centro-Oeste (Censo também: Exterior; Não informado)"),
    "co_municipio": ("CO_MUNICIPIO", "Código IBGE (7 dígitos) do município de oferta; no EAD, município do polo", "código IBGE de 7 dígitos; 0 ou nulo = sem município"),
    "no_municipio": ("NO_MUNICIPIO", "Nome do município de oferta", None),
    "in_capital": ("IN_CAPITAL", "Indica se o município de oferta é capital", "0 = não; 1 = sim"),
    # curso / IES
    "tp_dimensao": ("TP_DIMENSAO", "Nível geográfico em que o curso é informado", cod(ROTULOS["tp_dimensao"])),
    "ds_dimensao": ("derivada", "Rótulo de tp_dimensao", None),
    "tp_organizacao_academica": ("TP_ORGANIZACAO_ACADEMICA", "Organização acadêmica da IES", cod(ROTULOS["tp_organizacao_academica"])),
    "ds_organizacao_academica": ("derivada", "Rótulo de tp_organizacao_academica", None),
    "tp_rede": ("TP_REDE", "Rede da IES (2013 derivada da categoria administrativa)", cod(ROTULOS["tp_rede"])),
    "ds_rede": ("derivada", "Rótulo da rede (pública/privada)", None),
    "tp_categoria_administrativa": ("TP_CATEGORIA_ADMINISTRATIVA", "Categoria administrativa da IES (códigos 6/8/9 de 2009 harmonizados)", cod(ROTULOS["tp_categoria_administrativa"])),
    "ds_categoria_administrativa": ("derivada", "Rótulo da categoria administrativa", None),
    "co_ies": ("CO_IES", "Código da instituição de ensino superior no INEP", None),
    "co_curso": ("CO_CURSO", "Código do curso no INEP (chave de ligação Censo × ENADE)", None),
    "no_curso": ("NO_CURSO", "Nome do curso informado pela IES", None),
    "co_cine_rotulo": ("CO_CINE_ROTULO", "Código do rótulo CINE Brasil do curso (aspas removidas)", "código alfanumérico de 7 caracteres (ex.: 0114E07)"),
    "no_cine_rotulo": ("NO_CINE_ROTULO", "Nome do rótulo CINE Brasil (classificação de cursos)", None),
    "co_cine_area_geral": ("CO_CINE_AREA_GERAL", "Código da área geral CINE", "00–10; 99 = área não informada"),
    "no_cine_area_geral": ("NO_CINE_AREA_GERAL", "Área geral CINE do curso", None),
    "co_cine_area_especifica": ("CO_CINE_AREA_ESPECIFICA", "Código da área específica CINE", None),
    "no_cine_area_especifica": ("NO_CINE_AREA_ESPECIFICA", "Área específica CINE do curso", None),
    "tp_grau_academico": ("TP_GRAU_ACADEMICO", "Grau acadêmico conferido", cod(ROTULOS["tp_grau_academico"]) + "; 0 = não aplicável (ABI)"),
    "ds_grau_academico": ("derivada", "Rótulo do grau acadêmico", None),
    "in_gratuito": ("IN_GRATUITO", "Curso gratuito (não coletado em 2009)", "0 = não; 1 = sim"),
    "tp_modalidade_ensino": ("TP_MODALIDADE_ENSINO", "Modalidade de ensino", cod(ROTULOS["tp_modalidade_ensino"])),
    "ds_modalidade_ensino": ("derivada", "Rótulo da modalidade (Censo)", None),
    "tp_nivel_academico": ("TP_NIVEL_ACADEMICO", "Nível acadêmico (sequenciais, código 2, foram removidos)", "1 = graduação"),
    "qt_curso": ("QT_CURSO", "Indicador de curso contabilizado na linha", "0–1"),
    "qt_vg_total": ("QT_VG_TOTAL", "Total de vagas oferecidas (EAD informa só na dimensão 3)", None),
    "qt_inscrito_total": ("QT_INSCRITO_TOTAL", "Total de inscritos nos processos seletivos (EAD só na dimensão 3)", None),
    # derivadas / flags
    "qt_ing_ppi": ("derivada", "Ingressantes pretos + pardos + indígenas", None),
    "qt_mat_ppi": ("derivada", "Matrículas de pretos + pardos + indígenas", None),
    "qt_ing_25_mais": ("derivada", "Ingressantes com 25 anos ou mais (soma das faixas 25–29 a 60+)", None),
    "quadrienio": ("derivada", "Agrupamento de anos", "2009–2012; 2013–2016; 2017–2020; 2021–2024"),
    "fl_conta_alunos": ("derivada", "Linha entra nas somas de alunos (dimensões 1, 2 e 4)", "true/false"),
    "fl_chave_duplicada": ("derivada", "Chave (ano, curso, município, dimensão) repetida", "true/false"),
    "fl_incons_sexo_ing": ("derivada", "Feminino + masculino ≠ total de ingressantes", "true/false"),
    "fl_incons_idade_mat": ("derivada", "Soma das faixas etárias ≠ total de matrículas", "true/false"),
    "fl_outlier_mat": ("derivada", "Matrículas acima de Q3 + 1,5·IQR em log1p, por modalidade", "true/false"),
    # ENADE
    "tp_pres": ("TP_PRES", "Situação de presença do inscrito na prova", cod(PRESENCA)),
    "tp_pr_ger": ("TP_PR_GER", "Situação da prova geral (mesmos códigos de TP_PRES)", "555 = prova válida; demais = ausência ou resultado desconsiderado"),
    "ds_presenca": ("derivada", "Rótulo de tp_pres", None),
    "nt_ger": ("NT_GER", "Nota bruta da prova geral (0,25·FG + 0,75·CE)", None),
    "nt_fg": ("NT_FG", "Nota bruta da formação geral", None),
    "nt_ce": ("NT_CE", "Nota bruta do componente específico", None),
    "fl_nota_valida": ("derivada", "Presente com prova geral válida e nota não nula (entra nas médias)", "true/false"),
    "co_grupo": ("CO_GRUPO", "Código da área de enquadramento do curso no ENADE", None),
    "co_modalidade_enade": ("CO_MODALIDADE", "Modalidade segundo o ENADE", "0 = EAD; 1 = presencial"),
    "ds_modalidade_enade": ("derivada", "Rótulo de co_modalidade_enade", None),
    "co_munic_curso": ("CO_MUNIC_CURSO", "Código IBGE do município do curso (ENADE)", None),
    "co_uf_curso": ("CO_UF_CURSO", "Código IBGE da UF do curso (ENADE)", "11–53"),
    "co_regiao_curso": ("CO_REGIAO_CURSO", "Código da região do curso (ENADE)", "1 = Norte; 2 = Nordeste; 3 = Sudeste; 4 = Sul; 5 = Centro-Oeste"),
    "n_inscritos_sexo": ("derivada (TP_SEXO)", "Inscritos do curso no arquivo de sexo", None),
    "pct_fem": ("derivada (TP_SEXO)", "Proporção de mulheres entre os inscritos do curso", "0–1"),
    "idade_media": ("derivada (NU_IDADE)", "Idade média dos inscritos do curso (idades 16–90)", None),
    "idade_mediana": ("derivada (NU_IDADE)", "Idade mediana dos inscritos do curso (idades 16–90)", None),
    # IBGE
    "populacao": ("V (SIDRA)", "População residente na UF", None),
    "origem": ("derivada", "Fonte do valor de população", "sidra_6579_estimativas; sidra_1378_censo2010; sidra_4709_censo2022; interpolação linear"),
}
# sobrescritas específicas por tabela
D_TAB = {
    ("enade_desempenho", "ds_rede"): ("Censo (via co_curso × ano)", "Rede da IES do curso, trazida do Censo", "Pública; Privada; nulo = curso não encontrado no Censo"),
    ("enade_desempenho", "no_regiao"): ("CO_REGIAO_CURSO", "Região do curso no ENADE", None),
    ("enade_desempenho", "co_ies"): ("CO_IES", "Código da IES no INEP", None),
    ("enade_desempenho", "ano"): ("NU_ANO", "Ano de aplicação do ENADE (partição)", None),
    ("enade_perfil_curso", "ano"): ("NU_ANO", "Ano de aplicação do ENADE (partição)", None),
    ("populacao_uf", "ano"): ("D3C (SIDRA)", "Ano de referência da população", None),
    ("populacao_uf", "co_uf"): ("D1C (SIDRA)", "Código IBGE da UF", "11–53"),
    ("populacao_uf", "sg_uf"): ("derivada", "Sigla da UF", "27 siglas"),
    ("populacao_uf", "no_regiao"): ("derivada", "Grande região do IBGE", "Norte; Nordeste; Sudeste; Sul; Centro-Oeste"),
    ("municipios", "co_municipio"): ("id (API Localidades)", "Código IBGE do município (7 dígitos)", "código IBGE de 7 dígitos"),
    ("municipios", "no_municipio"): ("nome (API Localidades)", "Nome do município", None),
    ("municipios", "co_uf"): ("UF.id (API Localidades)", "Código IBGE da UF do município", "11–53"),
    ("municipios", "sg_uf"): ("UF.sigla (API Localidades)", "Sigla da UF do município", "27 siglas"),
    ("municipios", "no_regiao"): ("UF.regiao.nome (API Localidades)", "Grande região do município", "Norte; Nordeste; Sudeste; Sul; Centro-Oeste"),
}
PUBLICO = {"ing": "Ingressantes", "mat": "Matrículas", "conc": "Concluintes"}
SUFIXO = {"fem": "do sexo feminino", "masc": "do sexo masculino", "diurno": "no turno diurno", "noturno": "no turno noturno",
          "enem": "que usaram o ENEM", "vestibular": "por vestibular", "branca": "de cor/raça branca", "preta": "de cor/raça preta",
          "parda": "de cor/raça parda", "amarela": "de cor/raça amarela", "indigena": "de cor/raça indígena",
          "cornd": "com cor/raça não declarada", "fies": "com FIES", "prounii": "com PROUNI integral", "prounip": "com PROUNI parcial",
          "reserva_vaga": "por reserva de vagas", "procescpublica": "que cursaram o ensino médio em escola pública",
          "procescprivada": "que cursaram o ensino médio em escola privada", "deficiente": "com deficiência"}
SIT = {"trancada": "trancada", "desvinculado": "desvinculada do curso", "transferido": "transferida para outro curso", "falecido": "encerrada por falecimento"}


def descrever(tabela, col):
    if (tabela, col) in D_TAB:
        return D_TAB[(tabela, col)]
    if col in D:
        return D[col]
    m = re.fullmatch(r"qt_(ing|mat|conc)(?:_(.+))?", col)
    if m:
        pub, suf = m.groups()
        if suf is None:
            return (col.upper(), f"Total de {PUBLICO[pub].lower()}", None)
        if re.fullmatch(r"\d+_\d+|60_mais", suf):
            faixa = suf.replace("_mais", " anos ou mais").replace("_", " a ") + ("" if "mais" in suf else " anos")
            return (col.upper(), f"{PUBLICO[pub]} na faixa de {faixa}", None)
        return (col.upper(), f"{PUBLICO[pub]} {SUFIXO.get(suf, suf)}", None)
    m = re.fullmatch(r"qt_sit_(.+)", col)
    if m:
        return (col.upper(), f"Matrículas em situação {SIT.get(m.group(1), m.group(1))} no ano", None)
    raise KeyError(f"sem descrição: {tabela}.{col}")


def main():
    con = duckdb.connect()
    con.execute("SET memory_limit = '4GB'")
    linhas = []
    for tabela, (desc_tab, src) in TABELAS.items():
        perfil = con.sql(f"summarize select * from {src}").df()
        tipos = dict(con.sql(f"describe select * from {src}").df()[["column_name", "column_type"]].values)
        for r in perfil.itertuples():
            orig, desc, dom = descrever(tabela, r.column_name)
            tipo = tipos[r.column_name]
            if dom is None:
                if tipo in ("TINYINT", "SMALLINT", "INTEGER", "BIGINT", "DOUBLE"):
                    lo, hi = r.min, r.max
                    if tipo == "DOUBLE":
                        lo, hi = f"{float(lo):.1f}", f"{float(hi):.1f}"
                    dom = f"{lo} – {hi}" if r.column_name.startswith(("qt_", "nt_", "idade", "populacao", "n_", "ano")) else f"identificador ({int(r.approx_unique):,} valores distintos)".replace(",", ".")
                else:
                    dom = f"texto ({int(r.approx_unique):,} valores distintos)".replace(",", ".")
            linhas.append(dict(tabela=tabela, variavel=r.column_name, variavel_original=orig, tipo=tipo,
                               descricao=desc, dominio=dom, pct_nulos=round(float(r.null_percentage), 2)))
    df = pd.DataFrame(linhas)
    df.to_csv(C.REPORTS / "dicionario_dados.csv", index=False)

    md = ["# Dicionário de dados (camada silver)", "",
          "Gerado por `src/dicionario.py`. Tipos e % de nulos medidos na silver; códigos conforme o layout dos microdados "
          "do INEP e do IBGE. Variáveis `ds_*`, `fl_*` e as marcadas como *derivada* foram criadas na limpeza "
          "(ver `reports/log_limpeza.csv`).", ""]
    for tabela, (desc_tab, _) in TABELAS.items():
        t = df[df.tabela == tabela]
        md += [f"## {tabela}", "", f"{desc_tab}. {len(t)} variáveis.", "",
               "| Variável | Original | Tipo | Descrição | Domínio | % nulos |", "|---|---|---|---|---|---|"]
        for r in t.itertuples():
            md.append(f"| `{r.variavel}` | {r.variavel_original} | {r.tipo} | {r.descricao} | {r.dominio} | {r.pct_nulos:g} |")
        md.append("")
    (C.REPORTS / "dicionario_dados.md").write_text("\n".join(md))
    print(f"{len(df)} variáveis em {df.tabela.nunique()} tabelas → reports/dicionario_dados.csv e .md")


if __name__ == "__main__":
    main()
