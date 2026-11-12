"""Etapa 3b – Camada gold (silver → gold): tabelas agregadas que respondem às perguntas de pesquisa.

Perguntas de pesquisa
  P1. Como evoluíram ingressantes e matrículas de graduação entre 2009 e 2024, e quanto desse
      crescimento veio do EAD?
  P2. Como o acesso ao ensino superior (matrículas por 100 mil habitantes) varia entre UFs e regiões,
      e a desigualdade regional diminuiu no período?
  P3. Qual o peso da rede privada e dos programas federais (FIES, PROUNI) no acesso, e como isso mudou?
  P4. O perfil do ingressante mudou (sexo, cor/raça PPI, idade 25+, escola pública, reserva de vagas)?
  P5. O desempenho no ENADE difere entre rede (pública × privada), modalidade (presencial × EAD) e área?

Saídas (Parquet em data/gold):
  serie_brasil.parquet          ano × modalidade × rede – cursos, vagas, inscritos, ingressantes, matrículas…  (P1, P3)
  uf_ano.parquet                ano × UF – matrículas/ingressantes, população IBGE, taxas por 100 mil hab.   (P2)
  perfil_ingressantes.parquet   ano × rede × modalidade – composição dos ingressantes                       (P3, P4)
  area_ano.parquet              ano × área CINE × modalidade – ingressantes, matrículas, concluintes          (P1)
  enade_curso.parquet           ano × curso – nota média, abstenção, atributos do curso e do Censo           (P5)
  enade_resumo.parquet          ano × rede × modalidade × área – distribuição das notas individuais          (P5)
  antes_depois_categoria.parquet  matrículas por categoria administrativa, bronze × silver (efeito da limpeza)
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

SILVER_CURSOS = f"read_parquet('{C.SILVER}/censo_cursos/*/*.parquet', hive_partitioning=true)"
SILVER_ENADE = f"read_parquet('{C.SILVER}/enade_desempenho/*/*.parquet', hive_partitioning=true)"
SILVER_PERFIL = f"read_parquet('{C.SILVER}/enade_perfil_curso/*/*.parquet', hive_partitioning=true)"


def conectar():
    tmp = C.DATA / "_duckdb_tmp"
    tmp.mkdir(exist_ok=True)
    con = duckdb.connect()
    for s in ("SET enable_progress_bar = false", "SET memory_limit = '4GB'", f"SET temp_directory = '{tmp}'",
              "SET preserve_insertion_order = false", "SET threads = 4"):
        con.execute(s)
    con.execute(f"create or replace view c as select * from {SILVER_CURSOS}")
    return con


def salvar(con, nome, sql):
    destino = C.GOLD / f"{nome}.parquet"
    con.execute(f"copy ({sql}) to '{destino}' (format parquet, compression zstd)")
    n = con.execute(f"select count(*) from '{destino}'").fetchone()[0]
    print(f"  {nome}: {n:,} linhas")


# Regras de soma (ver log_limpeza.csv):
#  * alunos (ingressantes, matrículas, concluintes): só linhas com fl_conta_alunos (dimensões 1, 2 e 4);
#  * vagas e inscritos: presencial na dimensão 1 e EAD na dimensão 3 (único nível em que o EAD informa vagas).
ALUNOS = "fl_conta_alunos"
VAGAS = "(tp_dimensao = 1 or tp_dimensao = 3)"


def serie_brasil(con):
    salvar(con, "serie_brasil", f"""
        select ano, ds_modalidade_ensino, ds_rede,
               count(distinct co_curso) filter (where {ALUNOS} or tp_dimensao = 3) as n_cursos,
               sum(qt_vg_total) filter (where {VAGAS}) as qt_vagas,
               sum(qt_inscrito_total) filter (where {VAGAS}) as qt_inscritos,
               sum(qt_ing) filter (where {ALUNOS}) as qt_ing,
               sum(qt_mat) filter (where {ALUNOS}) as qt_mat,
               sum(qt_conc) filter (where {ALUNOS}) as qt_conc,
               sum(qt_sit_desvinculado) filter (where {ALUNOS}) as qt_desvinculado,
               sum(qt_sit_trancada) filter (where {ALUNOS}) as qt_trancada
        from c group by all order by all""")


def uf_ano(con):
    salvar(con, "uf_ano", f"""
        with a as (
            select ano, co_uf,
                   sum(qt_ing) as qt_ing, sum(qt_mat) as qt_mat, sum(qt_conc) as qt_conc,
                   sum(qt_mat) filter (where tp_modalidade_ensino = 1) as qt_mat_presencial,
                   sum(qt_mat) filter (where tp_modalidade_ensino = 2) as qt_mat_ead,
                   sum(qt_mat) filter (where tp_rede = 1) as qt_mat_publica
            from c where {ALUNOS} and co_uf is not null group by all)
        select a.ano, a.co_uf, p.sg_uf, p.no_regiao, p.populacao, p.origem as origem_populacao,
               a.* exclude (ano, co_uf),
               1e5 * a.qt_mat / p.populacao as tx_mat_100mil,
               1e5 * a.qt_ing / p.populacao as tx_ing_100mil,
               1e5 * a.qt_mat_presencial / p.populacao as tx_mat_presencial_100mil,
               1e5 * a.qt_mat_publica / p.populacao as tx_mat_publica_100mil,
               a.qt_mat_ead / a.qt_mat as pct_mat_ead
        from a join read_parquet('{C.SILVER}/populacao_uf.parquet') p using (co_uf, ano)
        order by a.ano, a.co_uf""")


def perfil_ingressantes(con):
    # Percentuais calculados no notebook a partir das somas; denominadores próprios onde há nulos.
    salvar(con, "perfil_ingressantes", f"""
        select ano, ds_rede, ds_modalidade_ensino,
               sum(qt_ing) as qt_ing,
               sum(qt_ing_fem) as qt_ing_fem,
               sum(qt_ing_ppi) as qt_ing_ppi,
               sum(qt_ing_branca) as qt_ing_branca,
               sum(qt_ing_cornd) as qt_ing_cor_nd,
               sum(qt_ing_25_mais) as qt_ing_25_mais,
               sum(qt_ing_18_24) as qt_ing_18_24,
               sum(qt_ing_noturno) as qt_ing_noturno,
               sum(qt_ing_fies) as qt_ing_fies,
               sum(coalesce(qt_ing_prounii, 0) + coalesce(qt_ing_prounip, 0)) as qt_ing_prouni,
               sum(qt_ing_reserva_vaga) as qt_ing_reserva_vaga,
               sum(qt_ing_procescpublica) as qt_ing_escola_publica,
               sum(qt_ing_procescprivada) as qt_ing_escola_privada,
               sum(qt_mat) as qt_mat,
               sum(qt_mat_fies) as qt_mat_fies,
               sum(coalesce(qt_mat_prounii, 0) + coalesce(qt_mat_prounip, 0)) as qt_mat_prouni
        from c where {ALUNOS} group by all order by all""")


def area_ano(con):
    salvar(con, "area_ano", f"""
        select ano, no_cine_area_geral, ds_modalidade_ensino,
               sum(qt_ing) as qt_ing, sum(qt_mat) as qt_mat, sum(qt_conc) as qt_conc
        from c where {ALUNOS} group by all order by all""")


def enade(con):
    con.execute(f"create or replace view e as select * from {SILVER_ENADE}")
    con.execute(f"""create or replace table censo_mat as
        select ano, co_curso, sum(qt_mat) as qt_mat_censo, sum(qt_ing) as qt_ing_censo,
               any_value(sg_uf) filter (where sg_uf not in ('NI', 'EX')) as sg_uf_censo
        from c where {ALUNOS} group by all""")
    salvar(con, "enade_curso", f"""
        with a as (
            select ano, co_curso,
                   count(*) as n_inscritos,
                   count(*) filter (where fl_nota_valida) as n_notas_validas,
                   avg(case when tp_pres = 555 then 0.0 else 1.0 end) as tx_ausencia,
                   avg(nt_ger) filter (where fl_nota_valida) as nt_ger_media,
                   avg(nt_fg) filter (where fl_nota_valida) as nt_fg_media,
                   avg(nt_ce) filter (where fl_nota_valida) as nt_ce_media,
                   any_value(co_ies) as co_ies, any_value(co_grupo) as co_grupo,
                   any_value(ds_rede) as ds_rede, any_value(ds_categoria_administrativa) as ds_categoria_administrativa,
                   any_value(ds_organizacao_academica) as ds_organizacao_academica,
                   any_value(ds_modalidade_enade) as ds_modalidade_enade,
                   any_value(ds_grau_academico) as ds_grau_academico,
                   any_value(no_cine_area_geral) as no_cine_area_geral,
                   any_value(no_cine_rotulo) as no_cine_rotulo,
                   any_value(co_uf_curso) as co_uf_curso, any_value(no_regiao) as no_regiao
            from e group by all)
        select a.*, p.pct_fem, p.idade_media, p.idade_mediana, m.qt_mat_censo, m.qt_ing_censo
        from a left join {SILVER_PERFIL} p using (ano, co_curso)
               left join censo_mat m using (ano, co_curso)
        order by ano, co_curso""")
    salvar(con, "enade_resumo", """
        select ano, coalesce(ds_rede, 'Não casou com o Censo') as ds_rede, ds_modalidade_enade,
               coalesce(no_cine_area_geral, 'Não casou com o Censo') as no_cine_area_geral,
               count(*) as n_inscritos,
               count(*) filter (where fl_nota_valida) as n_notas_validas,
               avg(nt_ger) filter (where fl_nota_valida) as nt_ger_media,
               stddev_samp(nt_ger) filter (where fl_nota_valida) as nt_ger_dp,
               quantile_cont(nt_ger, [0.1, 0.25, 0.5, 0.75, 0.9]) filter (where fl_nota_valida) as nt_ger_quantis
        from e group by all order by all""")


def antes_depois(con):
    """Efeito da harmonização da categoria administrativa (códigos 6/8/9 existem só em 2009)."""
    rotulos_bronze = {1: "Pública Federal", 2: "Pública Estadual", 3: "Pública Municipal",
                      4: "Privada com fins lucrativos", 5: "Privada sem fins lucrativos", 6: "Particular (2009)",
                      7: "Especial", 8: "Comunitária (2009)", 9: "Confessional (2009)"}
    whens = " ".join(f"when {k} then '{v}'" for k, v in rotulos_bronze.items())
    salvar(con, "antes_depois_categoria", f"""
        select 'antes (bronze)' as versao, cast(NU_ANO_CENSO as smallint) as ano,
               case try_cast(TP_CATEGORIA_ADMINISTRATIVA as tinyint) {whens} else 'Não informado' end
                   as ds_categoria_administrativa,
               sum(try_cast(nullif(nullif(trim(QT_MAT), ''), '.') as bigint)) as qt_mat
        from read_parquet('{C.BRONZE}/censo_cursos/*/*.parquet', hive_partitioning=true, union_by_name=true)
        where try_cast(TP_DIMENSAO as tinyint) in (1, 2, 4)
          and coalesce(try_cast(TP_NIVEL_ACADEMICO as tinyint), 1) <> 2
          and cast(NU_ANO_CENSO as smallint) <= 2012
        group by all
        union all
        select 'depois (silver)', ano, ds_categoria_administrativa, sum(qt_mat)
        from c where {ALUNOS} and ano <= 2012 group by all
        order by 1, 2, 3""")


def validar(con):
    """Confere os totais com os números oficiais divulgados pelo INEP (Resumo Técnico / Sinopse)."""
    oficiais = {2019: (8_603_824, 3_633_320), 2022: (9_443_597, 4_756_728), 2023: (9_976_782, 4_993_992)}
    df = con.execute(f"select ano, sum(qt_mat), sum(qt_ing) from c where {ALUNOS} group by 1").df()
    df.columns = ["ano", "mat", "ing"]
    df = df.set_index("ano")
    print("  validação × INEP (matrículas / ingressantes):")
    for ano, (mat, ing) in oficiais.items():
        print(f"    {ano}: {df.loc[ano, 'mat']:,.0f} × {mat:,}  |  {df.loc[ano, 'ing']:,.0f} × {ing:,}")


def main():
    C.GOLD.mkdir(parents=True, exist_ok=True)
    con = conectar()
    print("[gold]")
    serie_brasil(con)
    uf_ano(con)
    perfil_ingressantes(con)
    area_ano(con)
    enade(con)
    antes_depois(con)
    validar(con)


if __name__ == "__main__":
    main()
