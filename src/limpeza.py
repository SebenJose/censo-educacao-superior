"""Etapa 3 – Limpeza e tratamento (bronze → silver).

Cada problema encontrado na EDA recebe uma decisão; o efeito (linhas afetadas) é medido
e gravado em reports/log_limpeza.csv (problema · decisão · justificativa · linhas afetadas).

Saídas (Parquet particionado por ano em data/silver):
  censo_cursos/        – Censo da Educação Superior, cursos de graduação, 2009–2024
  enade_desempenho/    – ENADE, 1 linha por inscrito (notas), enriquecido com dados do curso
  enade_perfil_curso/  – ENADE, perfil por curso (sexo e idade agregados – arquivos LGPD)
  populacao_uf.parquet – IBGE, população residente por UF e ano (2009–2024)
  municipios.parquet   – IBGE, tabela de municípios
"""
from __future__ import annotations

import re
import shutil
import sys
import unicodedata
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

LOG: list[dict] = []


def registrar(etapa, problema, decisao, justificativa, linhas_afetadas, linhas_antes=None, linhas_depois=None):
    LOG.append(dict(etapa=etapa, problema=problema, decisao=decisao, justificativa=justificativa,
                    linhas_afetadas=int(linhas_afetadas),
                    linhas_antes=None if linhas_antes is None else int(linhas_antes),
                    linhas_depois=None if linhas_depois is None else int(linhas_depois)))
    print(f"  [{etapa}] {problema}: {int(linhas_afetadas):,} linhas → {decisao}")


def snake(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_").lower()
    return s


def q1(con, sql):
    return con.execute(sql).fetchall()[0][0]


# ======================================================================= dicionários de decodificação
ROTULOS = {
    "tp_rede": {1: "Pública", 2: "Privada"},
    "tp_categoria_administrativa": {1: "Pública Federal", 2: "Pública Estadual", 3: "Pública Municipal",
                                    4: "Privada com fins lucrativos", 5: "Privada sem fins lucrativos",
                                    7: "Especial"},
    "tp_organizacao_academica": {1: "Universidade", 2: "Centro Universitário", 3: "Faculdade",
                                 4: "Instituto Federal", 5: "CEFET"},
    "tp_grau_academico": {1: "Bacharelado", 2: "Licenciatura", 3: "Tecnológico", 4: "Bacharelado e Licenciatura"},
    "tp_modalidade_ensino": {1: "Presencial", 2: "EAD"},
    "tp_dimensao": {1: "Presencial – Brasil", 2: "EAD – por município de oferta",
                    3: "EAD – somente nível Brasil", 4: "EAD – oferta no exterior"},
}
REGIAO = {1: "Norte", 2: "Nordeste", 3: "Sudeste", 4: "Sul", 5: "Centro-Oeste"}

# colunas do bronze mantidas na silver (as demais seguem disponíveis no bronze)
COLS_ID = ["NU_ANO_CENSO", "CO_REGIAO", "CO_UF", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "IN_CAPITAL",
           "TP_DIMENSAO", "TP_ORGANIZACAO_ACADEMICA", "TP_REDE", "TP_CATEGORIA_ADMINISTRATIVA", "CO_IES",
           "NO_CURSO", "CO_CURSO", "NO_CINE_ROTULO", "CO_CINE_ROTULO", "CO_CINE_AREA_GERAL",
           "NO_CINE_AREA_GERAL", "CO_CINE_AREA_ESPECIFICA", "NO_CINE_AREA_ESPECIFICA",
           "TP_GRAU_ACADEMICO", "IN_GRATUITO", "TP_MODALIDADE_ENSINO", "TP_NIVEL_ACADEMICO"]
FAIXAS = ["0_17", "18_24", "25_29", "30_34", "35_39", "40_49", "50_59", "60_MAIS"]
CORES = ["BRANCA", "PRETA", "PARDA", "AMARELA", "INDIGENA", "CORND"]
COLS_QT = (["QT_CURSO", "QT_VG_TOTAL", "QT_INSCRITO_TOTAL"]
           + [f"QT_{x}_{s}" for x in ("ING", "MAT", "CONC") for s in ("FEM", "MASC", "DIURNO", "NOTURNO")]
           + ["QT_ING", "QT_MAT", "QT_CONC", "QT_ING_ENEM", "QT_ING_VESTIBULAR"]
           + [f"QT_{x}_{f}" for x in ("ING", "MAT", "CONC") for f in FAIXAS]
           + [f"QT_{x}_{c}" for x in ("ING", "MAT", "CONC") for c in CORES]
           + ["QT_ING_FIES", "QT_ING_PROUNII", "QT_ING_PROUNIP", "QT_MAT_FIES", "QT_MAT_PROUNII", "QT_MAT_PROUNIP",
              "QT_ING_RESERVA_VAGA", "QT_MAT_RESERVA_VAGA", "QT_ING_PROCESCPUBLICA", "QT_ING_PROCESCPRIVADA",
              "QT_MAT_DEFICIENTE", "QT_SIT_TRANCADA", "QT_SIT_DESVINCULADO", "QT_SIT_TRANSFERIDO", "QT_SIT_FALECIDO"])
INTEIROS_PEQ = {"CO_REGIAO", "CO_UF", "IN_CAPITAL", "TP_DIMENSAO", "TP_ORGANIZACAO_ACADEMICA", "TP_REDE",
                "TP_CATEGORIA_ADMINISTRATIVA", "TP_GRAU_ACADEMICO", "IN_GRATUITO", "TP_MODALIDADE_ENSINO",
                "TP_NIVEL_ACADEMICO"}


def nulo(col):
    """Trata '' e '.' (marcador INEP de 'não aplicável') como ausente."""
    return f"nullif(nullif(trim({col}), ''), '.')"


# ======================================================================= CENSO
def limpar_censo(con):
    print("\n[Censo – cursos]")
    con.execute(f"""create or replace view bronze_cursos as
        select * from read_parquet('{C.BRONZE}/censo_cursos/*/*.parquet', hive_partitioning=true,
                                   union_by_name=true)""")
    n0 = q1(con, "select count(*) from bronze_cursos")
    disponiveis = {r[0] for r in con.execute("describe bronze_cursos").fetchall()}

    # ---- 1. nomes e tipos
    sel = []
    falhas_cast = {}
    for c in COLS_ID + COLS_QT:
        alvo = snake(c)
        if c not in disponiveis:
            sel.append(f"null::integer as {alvo}")
            continue
        if c.startswith("QT_"):
            sel.append(f"try_cast({nulo(c)} as integer) as {alvo}")
        elif c in INTEIROS_PEQ:
            sel.append(f"try_cast({nulo(c)} as tinyint) as {alvo}")
        elif c in ("NU_ANO_CENSO",):
            sel.append(f"cast({c} as smallint) as ano")
        elif c in ("CO_MUNICIPIO", "CO_IES", "CO_CURSO"):
            sel.append(f"try_cast({nulo(c)} as integer) as {alvo}")
        elif c == "CO_CINE_ROTULO":
            sel.append(f"nullif(replace({nulo(c)}, '\"', ''), '') as {alvo}")
        else:
            sel.append(f"{nulo(c)} as {alvo}")
    con.execute(f"create or replace table t as select {', '.join(sel)} from bronze_cursos")
    registrar("censo", "Nomes de colunas em MAIÚSCULAS com prefixos INEP", "Padronizados para snake_case "
              f"sem acento; {len(disponiveis) - 1}→{len(COLS_ID + COLS_QT)} colunas mantidas (demais seguem no bronze)",
              "Legibilidade e consistência entre anos; colunas não usadas nas perguntas reduzem memória",
              n0, n0, n0)

    for c in COLS_QT + ["CO_CURSO", "CO_IES", "CO_MUNICIPIO"]:
        if c in disponiveis:
            falhas_cast[c] = q1(con, f"select count(*) from bronze_cursos where {nulo(c)} is not null "
                                     f"and try_cast({nulo(c)} as integer) is null")
    total_falhas = sum(falhas_cast.values())
    registrar("censo", "Tipos: tudo VARCHAR no bronze", "Cast para TINYINT/SMALLINT/INTEGER com try_cast",
              f"Inteiros de tamanho adequado reduzem memória; valores não numéricos viram nulo "
              f"(falhas de conversão: {total_falhas})", total_falhas)
    n_aspas = q1(con, "select count(*) from bronze_cursos where CO_CINE_ROTULO like '%\"%'")
    registrar("censo", "CO_CINE_ROTULO com aspas duplicadas (ex.: \"\"\"0011A09\"\"\")",
              "Removidas as aspas", "Padroniza o código CINE para junções e decodificação", n_aspas)

    n_ponto = q1(con, "select count(*) from bronze_cursos where trim(QT_MAT) = '.' or trim(QT_ING) = '.'")
    registrar("censo", "Marcador '.' (não aplicável) em campos numéricos", "Convertido para NULL",
              "No layout INEP '.' significa 'não se aplica', não zero", n_ponto)

    # ---- 2. nível acadêmico: só graduação
    n_seq = q1(con, "select count(*) from t where tp_nivel_academico = 2")
    con.execute("delete from t where tp_nivel_academico = 2")
    registrar("censo", "Cursos sequenciais de formação específica (TP_NIVEL_ACADEMICO=2)", "Removidos",
              "O escopo é graduação; sequenciais não entram nas estatísticas oficiais de graduação do INEP",
              n_seq, n0, n0 - n_seq)
    n1 = n0 - n_seq

    # ---- 3. duplicados
    n_dup_exato = q1(con, "select count(*) - (select count(*) from (select distinct * from t)) from t")
    if n_dup_exato:
        con.execute("create or replace table t as select distinct * from t")
    registrar("censo", "Linhas duplicadas exatas", "Removidas", "Repetição pura não carrega informação",
              n_dup_exato, n1, n1 - n_dup_exato)
    n1 -= n_dup_exato
    n_dup_chave = q1(con, """select coalesce(sum(n-1),0) from (select count(*) n from t
                          group by ano, co_curso, co_municipio, tp_dimensao having count(*) > 1)""")
    con.execute("""create or replace table t as select *, count(*) over
                   (partition by ano, co_curso, co_municipio, tp_dimensao) > 1 as fl_chave_duplicada from t""")
    registrar("censo", "Chave (ano, curso, município, dimensão) repetida com conteúdo diferente",
              "Mantidas e marcadas (fl_chave_duplicada)",
              "Sem critério objetivo para escolher a linha correta; somar ambas preserva os totais INEP",
              n_dup_chave)

    # ---- 4. dimensão geográfica (evita dupla contagem do EAD)
    n_dim3 = q1(con, "select count(*) from t where tp_dimensao = 3")
    registrar("censo", "TP_DIMENSAO=3: EAD 'somente nível Brasil' repete o curso EAD sem alunos por município",
              "Mantidas e marcadas (fl_conta_alunos=false); excluídas de somas de ingressantes/matrículas",
              "Somar dimensões 2 e 3 contaria o mesmo curso EAD duas vezes; vagas/inscritos EAD só existem na dim. 3",
              n_dim3)
    n_dim4 = q1(con, "select count(*) from t where tp_dimensao = 4")
    registrar("censo", "TP_DIMENSAO=4: EAD ofertado no exterior (sem UF)",
              "Mantidas; UF = 'Exterior' em análises regionais", "São alunos de IES brasileiras; entram no total Brasil",
              n_dim4)

    # ---- 5. harmonização entre anos: categoria administrativa 2009
    # A categoria 6 ("particular em sentido estrito") de 2009 NÃO equivale a "com fins lucrativos":
    # cruzando por CO_IES, ~54% das matrículas dessas IES foram declaradas com fins lucrativos em 2010 e
    # ~46% sem fins lucrativos. Por isso a categoria de 2009 é herdada da própria IES em 2010.
    n_cat = q1(con, "select count(*) from t where tp_categoria_administrativa in (6, 8, 9)")
    con.execute("""create or replace table cat2010 as
        select co_ies, any_value(tp_categoria_administrativa) as cat10 from t
        where ano = 2010 and tp_categoria_administrativa in (1, 2, 3, 4, 5, 7) group by 1""")
    n_cat_ies = q1(con, """select count(*) from t join cat2010 using (co_ies)
                           where tp_categoria_administrativa in (6, 8, 9)""")
    con.execute("""update t set tp_categoria_administrativa = coalesce(
                       (select cat10 from cat2010 where cat2010.co_ies = t.co_ies),
                       case t.tp_categoria_administrativa when 6 then 4 when 8 then 5 when 9 then 5 end)
                   where tp_categoria_administrativa in (6, 8, 9)""")
    registrar("censo", "Categorias administrativas 6/8/9 (particular/comunitária/confessional) existem só em 2009",
              f"Herdada a categoria declarada pela mesma IES em 2010 ({n_cat_ies:,} linhas); sem IES em 2010: "
              "6→4 (com fins lucrativos), 8/9→5 (sem fins lucrativos)",
              "Mapear 6→4 em bloco criava queda artificial de 3,4 mi → 2,1 mi matrículas 'com fins lucrativos' "
              "entre 2009 e 2010: 46% das matrículas 'particulares' eram de IES sem fins lucrativos", n_cat)

    # rede (pública/privada) é função determinística da categoria: em 2010–2024 (exceto 2013) as categorias
    # 1, 2, 3 e 7 são sempre TP_REDE=1 e 4, 5 (e 6, 8, 9 de 2009) sempre TP_REDE=2, sem exceção.
    n_rede = q1(con, "select count(*) from t where tp_rede is null")
    con.execute("""update t set tp_rede = case when tp_categoria_administrativa in (1, 2, 3, 7) then 1
                                              when tp_categoria_administrativa in (4, 5) then 2 end
                   where tp_rede is null""")
    registrar("censo", "TP_REDE ausente (praticamente todo o ano de 2013)",
              "Derivada da categoria administrativa (1, 2, 3, 7 → Pública; 4, 5 → Privada)",
              "Nos demais anos a relação categoria→rede é determinística (0 exceções); sem isso a série "
              "pública × privada some em 2013", n_rede)

    # ---- 6. UF/região: preencher a partir do código IBGE e padronizar
    n_sem_uf = q1(con, "select count(*) from t where co_uf is null and tp_dimensao in (1, 2)")
    registrar("censo", "UF ausente em cursos presenciais/EAD por município",
              "Mantidas como 'Não informado'", "Não há como inferir a UF sem o município", n_sem_uf)
    uf_df = pd.DataFrame([(k, v[0], v[1], v[2]) for k, v in C.UFS.items()],
                         columns=["co_uf", "sg_uf_ibge", "no_uf", "no_regiao"])
    con.register("uf_df", uf_df)
    n_uf_div = q1(con, "select count(*) from t join uf_df using (co_uf) where t.sg_uf <> uf_df.sg_uf_ibge")
    con.execute("""create or replace table t as
        select t.* exclude (sg_uf, co_regiao),
               coalesce(u.sg_uf_ibge, case when t.tp_dimensao = 4 then 'EX' else 'NI' end) as sg_uf,
               coalesce(u.no_uf, case when t.tp_dimensao = 4 then 'Exterior' else 'Não informado' end) as no_uf,
               coalesce(u.no_regiao, case when t.tp_dimensao = 4 then 'Exterior' else 'Não informado' end) as no_regiao
        from t left join uf_df u using (co_uf)""")
    registrar("censo", "Sigla de UF divergente do código IBGE", "Sigla/região recalculadas a partir de CO_UF",
              "O código IBGE é a chave canônica", n_uf_div)

    # ---- 7. valores fora do domínio / inconsistências
    n_neg = q1(con, f"select count(*) from t where {' or '.join(f'{snake(c)} < 0' for c in COLS_QT)}")
    registrar("censo", "Contagens negativas", "Seriam convertidas para NULL", "Contagem não pode ser negativa", n_neg)
    n_sexo = q1(con, """select count(*) from t where qt_ing is not null and qt_ing_fem + qt_ing_masc <> qt_ing""")
    n_idade = q1(con, f"""select count(*) from t where qt_mat is not null and
                       {' + '.join(f'coalesce(qt_mat_{f.lower()},0)' for f in FAIXAS)} <> qt_mat""")
    n_conc = q1(con, "select count(*) from t where qt_conc > qt_mat + qt_conc and qt_mat is not null")
    con.execute(f"""create or replace table t as select *,
        (qt_ing is not null and qt_ing_fem + qt_ing_masc <> qt_ing) as fl_incons_sexo_ing,
        (qt_mat is not null and {' + '.join(f'coalesce(qt_mat_{f.lower()},0)' for f in FAIXAS)} <> qt_mat)
            as fl_incons_idade_mat
        from t""")
    registrar("censo", "Soma feminino+masculino ≠ total de ingressantes",
              "Marcadas (fl_incons_sexo_ing); totais preservados",
              "Inconsistência rara de declaração; o total é o dado oficial", n_sexo)
    registrar("censo", "Soma das faixas etárias ≠ total de matrículas", "Marcadas (fl_incons_idade_mat)",
              "Idem; afeta apenas análises por faixa etária", n_idade)
    registrar("censo", "Concluintes acima do estoque de matrículas", "Nenhuma ação (verificação)",
              "Checagem de plausibilidade", n_conc)

    # ---- 8. ausentes
    n_area = q1(con, "select count(*) from t where co_cine_area_geral is null")
    con.execute("""update t set co_cine_area_geral = '99', no_cine_area_geral = 'Área não informada'
                   where co_cine_area_geral is null""")
    registrar("censo", "Área CINE ausente", "Categoria própria 'Área não informada' (99)",
              "Remover enviesaria a série; imputar área a partir do nome do curso seria arbitrário", n_area)
    n_qt_null = q1(con, "select count(*) from t where qt_mat is null and tp_dimensao in (1, 2, 4)")
    registrar("censo", "QT_MAT nulo em linhas que deveriam ter alunos", "Mantido NULL (não imputado)",
              "Imputar 0 confundiria 'não informado' com 'sem alunos'; somas ignoram nulos", n_qt_null)
    n_esc = q1(con, "select count(*) from t where ano = 2009")
    con.execute("update t set qt_ing_procescpublica = null, qt_ing_procescprivada = null where ano = 2009")
    registrar("censo", "Escola de origem do ingressante (QT_ING_PROCESC*) zerada em 2009 e parcial em 2010–2012",
              "2009 → NULL; % escola pública calculado sobre ingressantes com origem informada; "
              "série confiável a partir de 2013",
              "Em 2009 o campo não foi coletado (todo zero); até 2012 pública+privada < ingressantes. "
              "Usar o total de ingressantes como denominador criaria um 'salto' de 0% para 71% que é artefato",
              n_esc)
    n_grat = q1(con, "select count(*) from t where in_gratuito is null")
    registrar("censo", "IN_GRATUITO ausente (não coletado em 2009)", "Mantido NULL",
              "Variável inexistente no ano; ver dicionário INEP", n_grat)

    # ---- 9. outliers (regra explícita: IQR em log1p das matrículas, por modalidade)
    con.execute("""create or replace table t as
        with s as (select tp_modalidade_ensino m,
                          quantile_cont(ln(1+qt_mat), 0.25) q1, quantile_cont(ln(1+qt_mat), 0.75) q3
                   from t where qt_mat > 0 and tp_dimensao in (1, 2) group by 1)
        select t.*, coalesce(t.qt_mat > 0 and ln(1+t.qt_mat) > s.q3 + 1.5*(s.q3-s.q1), false) as fl_outlier_mat
        from t left join s on t.tp_modalidade_ensino = s.m""")
    n_out = q1(con, "select count(*) from t where fl_outlier_mat")
    registrar("censo", "Cursos com matrículas extremas (IQR em log1p, por modalidade)",
              "Mantidos e marcados (fl_outlier_mat)",
              "São fenômeno real (grandes cursos EAD/Direito/Pedagogia), não erro de digitação", n_out)

    # ---- 10. variáveis derivadas + decodificação
    casos = []
    for col, mapa in ROTULOS.items():
        whens = " ".join(f"when {k} then '{v}'" for k, v in mapa.items())
        casos.append(f"case {col} {whens} else 'Não informado' end as {col.replace('tp_', 'ds_')}")
    con.execute(f"""create or replace table t as select *,
        {', '.join(casos)},
        tp_dimensao in (1, 2, 4) as fl_conta_alunos,
        case when ano <= 2012 then '2009–2012' when ano <= 2016 then '2013–2016'
             when ano <= 2020 then '2017–2020' else '2021–2024' end as quadrienio,
        coalesce(qt_ing_preta,0) + coalesce(qt_ing_parda,0) + coalesce(qt_ing_indigena,0) as qt_ing_ppi,
        coalesce(qt_mat_preta,0) + coalesce(qt_mat_parda,0) + coalesce(qt_mat_indigena,0) as qt_mat_ppi,
        coalesce(qt_ing_25_29,0)+coalesce(qt_ing_30_34,0)+coalesce(qt_ing_35_39,0)+coalesce(qt_ing_40_49,0)
          +coalesce(qt_ing_50_59,0)+coalesce(qt_ing_60_mais,0) as qt_ing_25_mais
        from t""")
    registrar("censo", "Códigos numéricos sem rótulo (rede, categoria, organização, grau, modalidade, dimensão)",
              "Decodificados via dicionário INEP em colunas ds_*", "Leitura direta nos gráficos/tabelas",
              q1(con, "select count(*) from t"))

    # ---- 11. integração: município (IBGE) e população (IBGE)
    con.execute(f"create or replace view mun as select * from read_parquet('{C.BRONZE}/ibge_municipios/*.parquet')")
    n_mun = q1(con, "select count(*) from t where co_municipio is not null")
    n_mun_nao = q1(con, "select count(*) from t where co_municipio is not null and co_municipio not in "
                        "(select co_municipio from mun)")
    registrar("censo", "Código de município do INEP sem correspondência na tabela IBGE",
              "Verificação de integridade (left join); sem remoção",
              f"{n_mun - n_mun_nao:,} de {n_mun:,} linhas com município casaram "
              f"({100*(n_mun-n_mun_nao)/max(n_mun,1):.3f}%)", n_mun_nao)

    con.execute(f"create or replace table silver_cursos as select * from t order by ano, co_curso")
    return q1(con, "select count(*) from silver_cursos")


# ======================================================================= POPULAÇÃO
def limpar_populacao(con):
    print("\n[IBGE – população]")
    pop = pd.read_parquet(C.BRONZE / "ibge_populacao_uf" / "populacao_uf.parquet")
    pop = pop[pop.co_uf.isin(C.UFS)]
    # prioridade: Censo (2010, 2022) > estimativa
    pop["prior"] = pop.origem.map({"sidra_1378_censo2010": 0, "sidra_4709_censo2022": 0}).fillna(1)
    pop = pop.sort_values("prior").drop_duplicates(["co_uf", "ano"]).drop(columns="prior")
    grade = pd.MultiIndex.from_product([list(C.UFS), C.ANOS_CENSO], names=["co_uf", "ano"]).to_frame(index=False)
    full = pd.MultiIndex.from_product([list(C.UFS), range(2001, 2027)], names=["co_uf", "ano"]).to_frame(index=False)
    full = full.merge(pop, how="left", on=["co_uf", "ano"]).sort_values(["co_uf", "ano"])
    faltantes = full[full.ano.isin(C.ANOS_CENSO) & full.populacao.isna()]
    full["populacao"] = full.groupby("co_uf")["populacao"].transform(lambda s: s.interpolate(limit_area="inside"))
    full["origem"] = full["origem"].fillna("interpolação linear")
    out = grade.merge(full, on=["co_uf", "ano"], how="left")
    out["sg_uf"] = out.co_uf.map(lambda c: C.UFS[c][0])
    out["no_regiao"] = out.co_uf.map(lambda c: C.UFS[c][2])
    out["populacao"] = out.populacao.round().astype("int64")
    registrar("ibge", f"População ausente nos anos {sorted(faltantes.ano.unique().tolist())} "
              "(sem estimativa publicada)", "Interpolação linear entre anos vizinhos, por UF",
              "Crescimento populacional é suave; erro esperado < 1%", len(faltantes))
    out.to_parquet(C.SILVER / "populacao_uf.parquet", index=False)
    shutil.copy(C.BRONZE / "ibge_municipios" / "municipios.parquet", C.SILVER / "municipios.parquet")
    con.register("pop", out)
    n = q1(con, "select count(*) from silver_cursos where fl_conta_alunos")
    nao = q1(con, "select count(*) from silver_cursos c where fl_conta_alunos and not exists "
                  "(select 1 from pop p where p.co_uf = c.co_uf and p.ano = c.ano)")
    registrar("integracao", "Linhas do Censo sem população (chave UF×ano)",
              "Ficam fora das taxas por 100 mil hab., mas dentro do total Brasil",
              f"{n-nao:,} de {n:,} linhas com alunos casaram ({100*(n-nao)/n:.2f}%); "
              "as que não casam são EAD no exterior/sem UF", nao)


# ======================================================================= ENADE
PRESENCA = {555: "Presente", 222: "Ausente", 334: "Ausente – dispensa", 444: "Ausente – dupla graduação",
            556: "Presente – resultado desconsiderado", 565: "Presente – resultado desconsiderado",
            585: "Presente – resultado desconsiderado", 888: "Eliminado / resultado desconsiderado",
            333: "Ausente – outro motivo"}


def limpar_enade(con):
    print("\n[ENADE]")
    num = lambda c: f"try_cast(replace({nulo(c)}, ',', '.') as double)"  # noqa: E731
    con.execute(f"""create or replace table e as select
            cast(NU_ANO as smallint) as ano, try_cast(CO_CURSO as integer) as co_curso,
            try_cast(TP_PRES as smallint) as tp_pres, try_cast({nulo('TP_PR_GER')} as smallint) as tp_pr_ger,
            {num('NT_GER')} as nt_ger, {num('NT_FG')} as nt_fg, {num('NT_CE')} as nt_ce
        from read_parquet('{C.BRONZE}/enade_desempenho/*/*.parquet', hive_partitioning=true, union_by_name=true)""")
    n0 = q1(con, "select count(*) from e")
    registrar("enade", "Notas com vírgula decimal/strings e '.' como ausente",
              "Normalizado separador e convertido para DOUBLE", "Tipagem numérica para estatísticas", n0, n0, n0)
    n_fora = q1(con, "select count(*) from e where nt_ger < 0 or nt_ger > 100 or nt_fg < 0 or nt_fg > 100 "
                     "or nt_ce < 0 or nt_ce > 100")
    con.execute("update e set nt_ger = null where nt_ger < 0 or nt_ger > 100")
    registrar("enade", "Notas fora do domínio 0–100", "Convertidas para NULL", "Domínio definido no dicionário", n_fora)

    whens = " ".join(f"when {k} then '{v}'" for k, v in PRESENCA.items())
    con.execute(f"""create or replace table e as select *,
        case tp_pres {whens} else 'Outro' end as ds_presenca,
        (tp_pres = 555 and tp_pr_ger = 555 and nt_ger is not null) as fl_nota_valida from e""")
    n_inv = q1(con, "select count(*) from e where not fl_nota_valida")
    registrar("enade", "Inscritos ausentes, eliminados ou com prova em branco/desconsiderada",
              "Mantidos e marcados (fl_nota_valida=false); fora das médias de nota",
              "Remover apagaria a informação de abstenção, que também é resultado", n_inv)
    n_pres_sem = q1(con, "select count(*) from e where tp_pres = 555 and nt_ger is null")
    registrar("enade", "Presentes sem nota geral", "Fora das médias (fl_nota_valida=false)",
              "Sem nota não há o que imputar com segurança", n_pres_sem)

    # atributos de curso (arq1): 1 linha por curso-ano
    con.execute(f"""create or replace table ec as select distinct
            cast(NU_ANO as smallint) ano, try_cast(CO_CURSO as integer) co_curso, try_cast(CO_IES as integer) co_ies,
            try_cast(CO_GRUPO as integer) co_grupo, try_cast(CO_MODALIDADE as tinyint) co_modalidade_enade,
            try_cast(CO_MUNIC_CURSO as integer) co_munic_curso, try_cast(CO_UF_CURSO as tinyint) co_uf_curso,
            try_cast(CO_REGIAO_CURSO as tinyint) co_regiao_curso
        from read_parquet('{C.BRONZE}/enade_curso/*/*.parquet', hive_partitioning=true, union_by_name=true)""")
    n_cursos_conflito = q1(con, "select count(*) from (select ano, co_curso from ec group by 1,2 having count(*)>1)")
    con.execute("create or replace table ec as select * from ec qualify row_number() over "
                "(partition by ano, co_curso order by co_munic_curso) = 1")
    registrar("enade", "Atributos de curso repetidos 1×estudante no arquivo arq1",
              "Deduplicados para 1 linha por (ano, curso)",
              f"Cursos com atributos conflitantes: {n_cursos_conflito} (mantida a 1ª ocorrência)", n_cursos_conflito)

    # atributos do Censo por curso-ano (rede, área CINE, modalidade)
    con.execute("""create or replace table censo_curso as select ano, co_curso,
            any_value(ds_rede) ds_rede, any_value(ds_categoria_administrativa) ds_categoria_administrativa,
            any_value(ds_modalidade_ensino) ds_modalidade_ensino, any_value(ds_grau_academico) ds_grau_academico,
            any_value(no_cine_area_geral) no_cine_area_geral, any_value(no_cine_rotulo) no_cine_rotulo,
            any_value(ds_organizacao_academica) ds_organizacao_academica
        from silver_cursos group by 1,2""")
    con.execute("""create or replace table silver_enade as
        select e.*, ec.* exclude (ano, co_curso), cc.* exclude (ano, co_curso),
               case ec.co_regiao_curso when 1 then 'Norte' when 2 then 'Nordeste' when 3 then 'Sudeste'
                    when 4 then 'Sul' when 5 then 'Centro-Oeste' end as no_regiao,
               case ec.co_modalidade_enade when 0 then 'EAD' when 1 then 'Presencial' end as ds_modalidade_enade
        from e left join ec using (ano, co_curso) left join censo_curso cc using (ano, co_curso)""")
    nao_ec = q1(con, "select count(*) from silver_enade where co_ies is null")
    nao_cc = q1(con, "select count(*) from silver_enade where ds_rede is null")
    registrar("integracao", "Inscritos ENADE sem curso no arquivo de cursos do ENADE (arq1)",
              "Mantidos; atributos de curso nulos", f"{n0-nao_ec:,} de {n0:,} casaram", nao_ec)
    registrar("integracao", "Inscritos ENADE cujo CO_CURSO não aparece no Censo do mesmo ano",
              "Mantidos; rede/área CINE ficam nulas",
              f"{n0-nao_cc:,} de {n0:,} casaram ({100*(n0-nao_cc)/n0:.2f}%); cursos extintos/não recenseados",
              nao_cc)

    # perfil por curso (sexo, idade) – arquivos LGPD não ligáveis ao estudante
    con.execute(f"""create or replace table sx as select cast(NU_ANO as smallint) ano,
            try_cast(CO_CURSO as integer) co_curso, upper(trim(TP_SEXO)) sexo
        from read_parquet('{C.BRONZE}/enade_sexo/*/*.parquet', hive_partitioning=true, union_by_name=true)""")
    con.execute(f"""create or replace table idd as select cast(NU_ANO as smallint) ano,
            try_cast(CO_CURSO as integer) co_curso, try_cast({nulo('NU_IDADE')} as smallint) idade
        from read_parquet('{C.BRONZE}/enade_idade/*/*.parquet', hive_partitioning=true, union_by_name=true)""")
    n_sx_inv = q1(con, "select count(*) from sx where sexo not in ('M', 'F')")
    n_id_inv = q1(con, "select count(*) from idd where idade is null or idade < 16 or idade > 90")
    registrar("enade", "Sexo fora de {M,F} (ex.: código 9/N)", "Categoria 'Não informado'; fora do % feminino",
              "Remover reduziria o denominador de forma arbitrária", n_sx_inv)
    registrar("enade", "Idade ausente ou implausível (<16 ou >90)", "Convertida para NULL",
              "Erro de cadastro; não entra na média", n_id_inv)
    con.execute("""create or replace table silver_perfil as
        with a as (select ano, co_curso, count(*) n_inscritos_sexo,
                          avg(case when sexo='F' then 1.0 when sexo='M' then 0.0 end) pct_fem from sx group by 1,2),
             b as (select ano, co_curso, avg(case when idade between 16 and 90 then idade end) idade_media,
                          median(case when idade between 16 and 90 then idade end) idade_mediana from idd group by 1,2)
        select * from a full join b using (ano, co_curso)""")


# ======================================================================= main
def salvar(con, tabela, destino):
    if destino.exists():
        shutil.rmtree(destino)
    con.execute(f"copy {tabela} to '{destino}' (format parquet, partition_by (ano), compression zstd)")


def main():
    C.SILVER.mkdir(parents=True, exist_ok=True)
    C.REPORTS.mkdir(exist_ok=True)
    tmp = C.SILVER.parent / "_duckdb_tmp"
    tmp.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    # limita memória e permite spill em disco (sem isso o processo estourava ~10 GB e era morto pelo OOM killer)
    con.execute("SET memory_limit = '4GB'")
    con.execute(f"SET temp_directory = '{tmp}'")
    con.execute("SET preserve_insertion_order = false")
    con.execute("SET threads = 4")
    limpar_censo(con)
    limpar_populacao(con)
    limpar_enade(con)
    print("\n[gravando silver]")
    salvar(con, "silver_cursos", C.SILVER / "censo_cursos")
    salvar(con, "silver_enade", C.SILVER / "enade_desempenho")
    salvar(con, "silver_perfil", C.SILVER / "enade_perfil_curso")
    for t in ("silver_cursos", "silver_enade", "silver_perfil"):
        print(f"  {t}: {q1(con, f'select count(*) from {t}'):,} linhas")
    pd.DataFrame(LOG).to_csv(C.REPORTS / "log_limpeza.csv", index=False)
    print(f"\nLog: {C.REPORTS / 'log_limpeza.csv'} ({len(LOG)} decisões)")


if __name__ == "__main__":
    main()
