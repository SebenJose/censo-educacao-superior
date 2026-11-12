# Dicionário de dados (camada silver)

Gerado por `src/dicionario.py`. Tipos e % de nulos medidos na silver; códigos conforme o layout dos microdados do INEP e do IBGE. Variáveis `ds_*`, `fl_*` e as marcadas como *derivada* foram criadas na limpeza (ver `reports/log_limpeza.csv`).

## censo_cursos

Censo da Educação Superior (INEP) – 1 linha por curso × município × dimensão × ano. 117 variáveis.

| Variável | Original | Tipo | Descrição | Domínio | % nulos |
|---|---|---|---|---|---|
| `co_uf` | CO_UF | TINYINT | Código IBGE da UF de oferta do curso | 11–53 (código IBGE); 0 ou nulo = sem UF (EAD nível Brasil ou exterior) | 1.48 |
| `co_municipio` | CO_MUNICIPIO | INTEGER | Código IBGE (7 dígitos) do município de oferta; no EAD, município do polo | código IBGE de 7 dígitos; 0 ou nulo = sem município | 1.48 |
| `no_municipio` | NO_MUNICIPIO | VARCHAR | Nome do município de oferta | texto (3.647 valores distintos) | 1.73 |
| `in_capital` | IN_CAPITAL | TINYINT | Indica se o município de oferta é capital | 0 = não; 1 = sim | 1.48 |
| `tp_dimensao` | TP_DIMENSAO | TINYINT | Nível geográfico em que o curso é informado | 1 = Presencial – Brasil; 2 = EAD – por município de oferta; 3 = EAD – somente nível Brasil; 4 = EAD – oferta no exterior | 0 |
| `tp_organizacao_academica` | TP_ORGANIZACAO_ACADEMICA | TINYINT | Organização acadêmica da IES | 1 = Universidade; 2 = Centro Universitário; 3 = Faculdade; 4 = Instituto Federal; 5 = CEFET | 0 |
| `tp_rede` | TP_REDE | TINYINT | Rede da IES (2013 derivada da categoria administrativa) | 1 = Pública; 2 = Privada | 0 |
| `tp_categoria_administrativa` | TP_CATEGORIA_ADMINISTRATIVA | TINYINT | Categoria administrativa da IES (códigos 6/8/9 de 2009 harmonizados) | 1 = Pública Federal; 2 = Pública Estadual; 3 = Pública Municipal; 4 = Privada com fins lucrativos; 5 = Privada sem fins lucrativos; 7 = Especial | 0 |
| `co_ies` | CO_IES | INTEGER | Código da instituição de ensino superior no INEP | identificador (3.710 valores distintos) | 0 |
| `no_curso` | NO_CURSO | VARCHAR | Nome do curso informado pela IES | texto (9.745 valores distintos) | 0 |
| `co_curso` | CO_CURSO | INTEGER | Código do curso no INEP (chave de ligação Censo × ENADE) | identificador (73.641 valores distintos) | 0 |
| `no_cine_rotulo` | NO_CINE_ROTULO | VARCHAR | Nome do rótulo CINE Brasil (classificação de cursos) | texto (374 valores distintos) | 0 |
| `co_cine_rotulo` | CO_CINE_ROTULO | VARCHAR | Código do rótulo CINE Brasil do curso (aspas removidas) | código alfanumérico de 7 caracteres (ex.: 0114E07) | 8.95 |
| `co_cine_area_geral` | CO_CINE_AREA_GERAL | VARCHAR | Código da área geral CINE | 00–10; 99 = área não informada | 0 |
| `no_cine_area_geral` | NO_CINE_AREA_GERAL | VARCHAR | Área geral CINE do curso | texto (11 valores distintos) | 0 |
| `co_cine_area_especifica` | CO_CINE_AREA_ESPECIFICA | VARCHAR | Código da área específica CINE | texto (40 valores distintos) | 0 |
| `no_cine_area_especifica` | NO_CINE_AREA_ESPECIFICA | VARCHAR | Área específica CINE do curso | texto (39 valores distintos) | 0 |
| `tp_grau_academico` | TP_GRAU_ACADEMICO | TINYINT | Grau acadêmico conferido | 1 = Bacharelado; 2 = Licenciatura; 3 = Tecnológico; 4 = Bacharelado e Licenciatura; 0 = não aplicável (ABI) | 0.17 |
| `in_gratuito` | IN_GRATUITO | TINYINT | Curso gratuito (não coletado em 2009) | 0 = não; 1 = sim | 1.35 |
| `tp_modalidade_ensino` | TP_MODALIDADE_ENSINO | TINYINT | Modalidade de ensino | 1 = Presencial; 2 = EAD | 0 |
| `tp_nivel_academico` | TP_NIVEL_ACADEMICO | TINYINT | Nível acadêmico (sequenciais, código 2, foram removidos) | 1 = graduação | 0 |
| `qt_curso` | QT_CURSO | INTEGER | Indicador de curso contabilizado na linha | 0–1 | 18.87 |
| `qt_vg_total` | QT_VG_TOTAL | INTEGER | Total de vagas oferecidas (EAD informa só na dimensão 3) | 0 – 149153 | 18.87 |
| `qt_inscrito_total` | QT_INSCRITO_TOTAL | INTEGER | Total de inscritos nos processos seletivos (EAD só na dimensão 3) | 0 – 398817 | 18.87 |
| `qt_ing_fem` | QT_ING_FEM | INTEGER | Ingressantes do sexo feminino | 0 – 11116 | 0.51 |
| `qt_ing_masc` | QT_ING_MASC | INTEGER | Ingressantes do sexo masculino | 0 – 3333 | 0.51 |
| `qt_ing_diurno` | QT_ING_DIURNO | INTEGER | Ingressantes no turno diurno | 0 – 1821 | 0.51 |
| `qt_ing_noturno` | QT_ING_NOTURNO | INTEGER | Ingressantes no turno noturno | 0 – 5041 | 0.51 |
| `qt_mat_fem` | QT_MAT_FEM | INTEGER | Matrículas do sexo feminino | 0 – 14801 | 0.51 |
| `qt_mat_masc` | QT_MAT_MASC | INTEGER | Matrículas do sexo masculino | 0 – 5946 | 0.51 |
| `qt_mat_diurno` | QT_MAT_DIURNO | INTEGER | Matrículas no turno diurno | 0 – 5657 | 0.51 |
| `qt_mat_noturno` | QT_MAT_NOTURNO | INTEGER | Matrículas no turno noturno | 0 – 6105 | 0.51 |
| `qt_conc_fem` | QT_CONC_FEM | INTEGER | Concluintes do sexo feminino | 0 – 5998 | 0.51 |
| `qt_conc_masc` | QT_CONC_MASC | INTEGER | Concluintes do sexo masculino | 0 – 2932 | 0.51 |
| `qt_conc_diurno` | QT_CONC_DIURNO | INTEGER | Concluintes no turno diurno | 0 – 1375 | 0.51 |
| `qt_conc_noturno` | QT_CONC_NOTURNO | INTEGER | Concluintes no turno noturno | 0 – 1459 | 0.51 |
| `qt_ing` | QT_ING | INTEGER | Total de ingressantes | 0 – 12082 | 0.51 |
| `qt_mat` | QT_MAT | INTEGER | Total de matrículas | 0 – 16351 | 0.51 |
| `qt_conc` | QT_CONC | INTEGER | Total de concluintes | 0 – 6441 | 0.51 |
| `qt_ing_enem` | QT_ING_ENEM | INTEGER | Ingressantes que usaram o ENEM | 0 – 1714 | 0.51 |
| `qt_ing_vestibular` | QT_ING_VESTIBULAR | INTEGER | Ingressantes por vestibular | 0 – 5631 | 0.51 |
| `qt_ing_0_17` | QT_ING_0_17 | INTEGER | Ingressantes na faixa de 0 a 17 anos | 0 – 167 | 0.51 |
| `qt_ing_18_24` | QT_ING_18_24 | INTEGER | Ingressantes na faixa de 18 a 24 anos | 0 – 2579 | 0.51 |
| `qt_ing_25_29` | QT_ING_25_29 | INTEGER | Ingressantes na faixa de 25 a 29 anos | 0 – 1865 | 0.51 |
| `qt_ing_30_34` | QT_ING_30_34 | INTEGER | Ingressantes na faixa de 30 a 34 anos | 0 – 2411 | 0.51 |
| `qt_ing_35_39` | QT_ING_35_39 | INTEGER | Ingressantes na faixa de 35 a 39 anos | 0 – 2281 | 0.51 |
| `qt_ing_40_49` | QT_ING_40_49 | INTEGER | Ingressantes na faixa de 40 a 49 anos | 0 – 3101 | 0.51 |
| `qt_ing_50_59` | QT_ING_50_59 | INTEGER | Ingressantes na faixa de 50 a 59 anos | 0 – 993 | 0.51 |
| `qt_ing_60_mais` | QT_ING_60_MAIS | INTEGER | Ingressantes na faixa de 60 anos ou mais | 0 – 131 | 0.51 |
| `qt_mat_0_17` | QT_MAT_0_17 | INTEGER | Matrículas na faixa de 0 a 17 anos | 0 – 173 | 0.51 |
| `qt_mat_18_24` | QT_MAT_18_24 | INTEGER | Matrículas na faixa de 18 a 24 anos | 0 – 6068 | 0.51 |
| `qt_mat_25_29` | QT_MAT_25_29 | INTEGER | Matrículas na faixa de 25 a 29 anos | 0 – 2589 | 0.51 |
| `qt_mat_30_34` | QT_MAT_30_34 | INTEGER | Matrículas na faixa de 30 a 34 anos | 0 – 2815 | 0.51 |
| `qt_mat_35_39` | QT_MAT_35_39 | INTEGER | Matrículas na faixa de 35 a 39 anos | 0 – 3006 | 0.51 |
| `qt_mat_40_49` | QT_MAT_40_49 | INTEGER | Matrículas na faixa de 40 a 49 anos | 0 – 4803 | 0.51 |
| `qt_mat_50_59` | QT_MAT_50_59 | INTEGER | Matrículas na faixa de 50 a 59 anos | 0 – 2101 | 0.51 |
| `qt_mat_60_mais` | QT_MAT_60_MAIS | INTEGER | Matrículas na faixa de 60 anos ou mais | 0 – 323 | 0.51 |
| `qt_conc_0_17` | QT_CONC_0_17 | INTEGER | Concluintes na faixa de 0 a 17 anos | 0 – 5 | 0.51 |
| `qt_conc_18_24` | QT_CONC_18_24 | INTEGER | Concluintes na faixa de 18 a 24 anos | 0 – 1188 | 0.51 |
| `qt_conc_25_29` | QT_CONC_25_29 | INTEGER | Concluintes na faixa de 25 a 29 anos | 0 – 1136 | 0.51 |
| `qt_conc_30_34` | QT_CONC_30_34 | INTEGER | Concluintes na faixa de 30 a 34 anos | 0 – 1319 | 0.51 |
| `qt_conc_35_39` | QT_CONC_35_39 | INTEGER | Concluintes na faixa de 35 a 39 anos | 0 – 1304 | 0.51 |
| `qt_conc_40_49` | QT_CONC_40_49 | INTEGER | Concluintes na faixa de 40 a 49 anos | 0 – 2585 | 0.51 |
| `qt_conc_50_59` | QT_CONC_50_59 | INTEGER | Concluintes na faixa de 50 a 59 anos | 0 – 1343 | 0.51 |
| `qt_conc_60_mais` | QT_CONC_60_MAIS | INTEGER | Concluintes na faixa de 60 anos ou mais | 0 – 147 | 0.51 |
| `qt_ing_branca` | QT_ING_BRANCA | INTEGER | Ingressantes de cor/raça branca | 0 – 2537 | 0.51 |
| `qt_ing_preta` | QT_ING_PRETA | INTEGER | Ingressantes de cor/raça preta | 0 – 841 | 0.51 |
| `qt_ing_parda` | QT_ING_PARDA | INTEGER | Ingressantes de cor/raça parda | 0 – 4083 | 0.51 |
| `qt_ing_amarela` | QT_ING_AMARELA | INTEGER | Ingressantes de cor/raça amarela | 0 – 432 | 0.51 |
| `qt_ing_indigena` | QT_ING_INDIGENA | INTEGER | Ingressantes de cor/raça indígena | 0 – 313 | 0.51 |
| `qt_ing_cornd` | QT_ING_CORND | INTEGER | Ingressantes com cor/raça não declarada | 0 – 11944 | 0.51 |
| `qt_mat_branca` | QT_MAT_BRANCA | INTEGER | Matrículas de cor/raça branca | 0 – 6620 | 0.51 |
| `qt_mat_preta` | QT_MAT_PRETA | INTEGER | Matrículas de cor/raça preta | 0 – 1913 | 0.51 |
| `qt_mat_parda` | QT_MAT_PARDA | INTEGER | Matrículas de cor/raça parda | 0 – 5956 | 0.51 |
| `qt_mat_amarela` | QT_MAT_AMARELA | INTEGER | Matrículas de cor/raça amarela | 0 – 1253 | 0.51 |
| `qt_mat_indigena` | QT_MAT_INDIGENA | INTEGER | Matrículas de cor/raça indígena | 0 – 1309 | 0.51 |
| `qt_mat_cornd` | QT_MAT_CORND | INTEGER | Matrículas com cor/raça não declarada | 0 – 16285 | 0.51 |
| `qt_conc_branca` | QT_CONC_BRANCA | INTEGER | Concluintes de cor/raça branca | 0 – 1467 | 0.51 |
| `qt_conc_preta` | QT_CONC_PRETA | INTEGER | Concluintes de cor/raça preta | 0 – 311 | 0.51 |
| `qt_conc_parda` | QT_CONC_PARDA | INTEGER | Concluintes de cor/raça parda | 0 – 939 | 0.51 |
| `qt_conc_amarela` | QT_CONC_AMARELA | INTEGER | Concluintes de cor/raça amarela | 0 – 459 | 0.51 |
| `qt_conc_indigena` | QT_CONC_INDIGENA | INTEGER | Concluintes de cor/raça indígena | 0 – 356 | 0.51 |
| `qt_conc_cornd` | QT_CONC_CORND | INTEGER | Concluintes com cor/raça não declarada | 0 – 6404 | 0.51 |
| `qt_ing_fies` | QT_ING_FIES | INTEGER | Ingressantes com FIES | 0 – 1675 | 0.51 |
| `qt_ing_prounii` | QT_ING_PROUNII | INTEGER | Ingressantes com PROUNI integral | 0 – 623 | 0.51 |
| `qt_ing_prounip` | QT_ING_PROUNIP | INTEGER | Ingressantes com PROUNI parcial | 0 – 613 | 0.51 |
| `qt_mat_fies` | QT_MAT_FIES | INTEGER | Matrículas com FIES | 0 – 3797 | 0.51 |
| `qt_mat_prounii` | QT_MAT_PROUNII | INTEGER | Matrículas com PROUNI integral | 0 – 1111 | 0.51 |
| `qt_mat_prounip` | QT_MAT_PROUNIP | INTEGER | Matrículas com PROUNI parcial | 0 – 1401 | 0.51 |
| `qt_ing_reserva_vaga` | QT_ING_RESERVA_VAGA | INTEGER | Ingressantes por reserva de vagas | 0 – 770 | 0.51 |
| `qt_mat_reserva_vaga` | QT_MAT_RESERVA_VAGA | INTEGER | Matrículas por reserva de vagas | 0 – 3140 | 0.51 |
| `qt_ing_procescpublica` | QT_ING_PROCESCPUBLICA | INTEGER | Ingressantes que cursaram o ensino médio em escola pública | 0 – 5541 | 1.83 |
| `qt_ing_procescprivada` | QT_ING_PROCESCPRIVADA | INTEGER | Ingressantes que cursaram o ensino médio em escola privada | 0 – 4304 | 1.83 |
| `qt_mat_deficiente` | QT_MAT_DEFICIENTE | INTEGER | Matrículas com deficiência | 0 – 617 | 0.51 |
| `qt_sit_trancada` | QT_SIT_TRANCADA | INTEGER | Matrículas em situação trancada no ano | 0 – 4961 | 0.51 |
| `qt_sit_desvinculado` | QT_SIT_DESVINCULADO | INTEGER | Matrículas em situação desvinculada do curso no ano | 0 – 12110 | 0.51 |
| `qt_sit_transferido` | QT_SIT_TRANSFERIDO | INTEGER | Matrículas em situação transferida para outro curso no ano | 0 – 4005 | 0.51 |
| `qt_sit_falecido` | QT_SIT_FALECIDO | INTEGER | Matrículas em situação encerrada por falecimento no ano | 0 – 201 | 0.51 |
| `fl_chave_duplicada` | derivada | BOOLEAN | Chave (ano, curso, município, dimensão) repetida | true/false | 0 |
| `sg_uf` | SG_UF (recalculada) | VARCHAR | Sigla da UF, recalculada a partir do código IBGE | 27 siglas; EX = exterior; NI = não informado | 0 |
| `no_uf` | derivada | VARCHAR | Nome da UF | 27 UFs; Exterior; Não informado | 0 |
| `no_regiao` | derivada / CO_REGIAO_CURSO | VARCHAR | Grande região do IBGE | Norte; Nordeste; Sudeste; Sul; Centro-Oeste (Censo também: Exterior; Não informado) | 0 |
| `fl_incons_sexo_ing` | derivada | BOOLEAN | Feminino + masculino ≠ total de ingressantes | true/false | 0 |
| `fl_incons_idade_mat` | derivada | BOOLEAN | Soma das faixas etárias ≠ total de matrículas | true/false | 0 |
| `fl_outlier_mat` | derivada | BOOLEAN | Matrículas acima de Q3 + 1,5·IQR em log1p, por modalidade | true/false | 0 |
| `ds_rede` | derivada | VARCHAR | Rótulo da rede (pública/privada) | texto (2 valores distintos) | 0 |
| `ds_categoria_administrativa` | derivada | VARCHAR | Rótulo da categoria administrativa | texto (6 valores distintos) | 0 |
| `ds_organizacao_academica` | derivada | VARCHAR | Rótulo de tp_organizacao_academica | texto (5 valores distintos) | 0 |
| `ds_grau_academico` | derivada | VARCHAR | Rótulo do grau acadêmico | texto (5 valores distintos) | 0 |
| `ds_modalidade_ensino` | derivada | VARCHAR | Rótulo da modalidade (Censo) | texto (2 valores distintos) | 0 |
| `ds_dimensao` | derivada | VARCHAR | Rótulo de tp_dimensao | texto (4 valores distintos) | 0 |
| `fl_conta_alunos` | derivada | BOOLEAN | Linha entra nas somas de alunos (dimensões 1, 2 e 4) | true/false | 0 |
| `quadrienio` | derivada | VARCHAR | Agrupamento de anos | 2009–2012; 2013–2016; 2017–2020; 2021–2024 | 0 |
| `qt_ing_ppi` | derivada | INTEGER | Ingressantes pretos + pardos + indígenas | 0 – 4143 | 0 |
| `qt_mat_ppi` | derivada | INTEGER | Matrículas de pretos + pardos + indígenas | 0 – 7913 | 0 |
| `qt_ing_25_mais` | derivada | INTEGER | Ingressantes com 25 anos ou mais (soma das faixas 25–29 a 60+) | 0 – 10782 | 0 |
| `ano` | NU_ANO_CENSO / NU_ANO | BIGINT | Ano de referência do Censo ou do ENADE (partição) | 2009 – 2024 | 0 |

## enade_desempenho

ENADE (INEP) – 1 linha por inscrito, enriquecida com atributos do curso. 24 variáveis.

| Variável | Original | Tipo | Descrição | Domínio | % nulos |
|---|---|---|---|---|---|
| `co_curso` | CO_CURSO | INTEGER | Código do curso no INEP (chave de ligação Censo × ENADE) | identificador (30.740 valores distintos) | 0 |
| `tp_pres` | TP_PRES | SMALLINT | Situação de presença do inscrito na prova | 555 = Presente; 222 = Ausente; 334 = Ausente – dispensa; 444 = Ausente – dupla graduação; 556 = Presente – resultado desconsiderado; 565 = Presente – resultado desconsiderado; 585 = Presente – resultado desconsiderado; 888 = Eliminado / resultado desconsiderado; 333 = Ausente – outro motivo | 0 |
| `tp_pr_ger` | TP_PR_GER | SMALLINT | Situação da prova geral (mesmos códigos de TP_PRES) | 555 = prova válida; demais = ausência ou resultado desconsiderado | 0.13 |
| `nt_ger` | NT_GER | DOUBLE | Nota bruta da prova geral (0,25·FG + 0,75·CE) | 0.0 – 99.0 | 17.07 |
| `nt_fg` | NT_FG | DOUBLE | Nota bruta da formação geral | 0.0 – 100.0 | 17.07 |
| `nt_ce` | NT_CE | DOUBLE | Nota bruta do componente específico | 0.0 – 100.0 | 17.07 |
| `ds_presenca` | derivada | VARCHAR | Rótulo de tp_pres | texto (7 valores distintos) | 0 |
| `fl_nota_valida` | derivada | BOOLEAN | Presente com prova geral válida e nota não nula (entra nas médias) | true/false | 0 |
| `co_ies` | CO_IES | INTEGER | Código da IES no INEP | identificador (2.290 valores distintos) | 0 |
| `co_grupo` | CO_GRUPO | INTEGER | Código da área de enquadramento do curso no ENADE | identificador (91 valores distintos) | 0 |
| `co_modalidade_enade` | CO_MODALIDADE | TINYINT | Modalidade segundo o ENADE | 0 = EAD; 1 = presencial | 0 |
| `co_munic_curso` | CO_MUNIC_CURSO | INTEGER | Código IBGE do município do curso (ENADE) | identificador (1.048 valores distintos) | 0 |
| `co_uf_curso` | CO_UF_CURSO | TINYINT | Código IBGE da UF do curso (ENADE) | 11–53 | 0 |
| `co_regiao_curso` | CO_REGIAO_CURSO | TINYINT | Código da região do curso (ENADE) | 1 = Norte; 2 = Nordeste; 3 = Sudeste; 4 = Sul; 5 = Centro-Oeste | 0 |
| `ds_rede` | Censo (via co_curso × ano) | VARCHAR | Rede da IES do curso, trazida do Censo | Pública; Privada; nulo = curso não encontrado no Censo | 0.18 |
| `ds_categoria_administrativa` | derivada | VARCHAR | Rótulo da categoria administrativa | texto (6 valores distintos) | 0.18 |
| `ds_modalidade_ensino` | derivada | VARCHAR | Rótulo da modalidade (Censo) | texto (2 valores distintos) | 0.18 |
| `ds_grau_academico` | derivada | VARCHAR | Rótulo do grau acadêmico | texto (3 valores distintos) | 0.18 |
| `no_cine_area_geral` | NO_CINE_AREA_GERAL | VARCHAR | Área geral CINE do curso | texto (10 valores distintos) | 0.18 |
| `no_cine_rotulo` | NO_CINE_ROTULO | VARCHAR | Nome do rótulo CINE Brasil (classificação de cursos) | texto (179 valores distintos) | 0.18 |
| `ds_organizacao_academica` | derivada | VARCHAR | Rótulo de tp_organizacao_academica | texto (5 valores distintos) | 0.18 |
| `no_regiao` | CO_REGIAO_CURSO | VARCHAR | Região do curso no ENADE | texto (5 valores distintos) | 0 |
| `ds_modalidade_enade` | derivada | VARCHAR | Rótulo de co_modalidade_enade | texto (2 valores distintos) | 0 |
| `ano` | NU_ANO | BIGINT | Ano de aplicação do ENADE (partição) | 2017 – 2023 | 0 |

## enade_perfil_curso

ENADE (INEP) – perfil agregado por curso × ano (arquivos LGPD de sexo e idade). 6 variáveis.

| Variável | Original | Tipo | Descrição | Domínio | % nulos |
|---|---|---|---|---|---|
| `co_curso` | CO_CURSO | INTEGER | Código do curso no INEP (chave de ligação Censo × ENADE) | identificador (30.740 valores distintos) | 0 |
| `n_inscritos_sexo` | derivada (TP_SEXO) | BIGINT | Inscritos do curso no arquivo de sexo | 1 – 26771 | 0 |
| `pct_fem` | derivada (TP_SEXO) | DOUBLE | Proporção de mulheres entre os inscritos do curso | 0–1 | 1.29 |
| `idade_media` | derivada (NU_IDADE) | DOUBLE | Idade média dos inscritos do curso (idades 16–90) | 19.3 – 61.9 | 1.29 |
| `idade_mediana` | derivada (NU_IDADE) | DOUBLE | Idade mediana dos inscritos do curso (idades 16–90) | 19.0 – 63.0 | 1.29 |
| `ano` | NU_ANO | BIGINT | Ano de aplicação do ENADE (partição) | 2017 – 2023 | 0 |

## populacao_uf

IBGE – população residente por UF × ano. 6 variáveis.

| Variável | Original | Tipo | Descrição | Domínio | % nulos |
|---|---|---|---|---|---|
| `co_uf` | D1C (SIDRA) | BIGINT | Código IBGE da UF | 11–53 | 0 |
| `ano` | D3C (SIDRA) | BIGINT | Ano de referência da população | 2009 – 2024 | 0 |
| `populacao` | V (SIDRA) | BIGINT | População residente na UF | 421499 – 46649132 | 0 |
| `origem` | derivada | VARCHAR | Fonte do valor de população | sidra_6579_estimativas; sidra_1378_censo2010; sidra_4709_censo2022; interpolação linear | 0 |
| `sg_uf` | derivada | VARCHAR | Sigla da UF | 27 siglas | 0 |
| `no_regiao` | derivada | VARCHAR | Grande região do IBGE | Norte; Nordeste; Sudeste; Sul; Centro-Oeste | 0 |

## municipios

IBGE – tabela de municípios. 5 variáveis.

| Variável | Original | Tipo | Descrição | Domínio | % nulos |
|---|---|---|---|---|---|
| `co_municipio` | id (API Localidades) | BIGINT | Código IBGE do município (7 dígitos) | código IBGE de 7 dígitos | 0 |
| `no_municipio` | nome (API Localidades) | VARCHAR | Nome do município | texto (5.261 valores distintos) | 0 |
| `co_uf` | UF.id (API Localidades) | BIGINT | Código IBGE da UF do município | 11–53 | 0 |
| `sg_uf` | UF.sigla (API Localidades) | VARCHAR | Sigla da UF do município | 27 siglas | 0 |
| `no_regiao` | UF.regiao.nome (API Localidades) | VARCHAR | Grande região do município | Norte; Nordeste; Sudeste; Sul; Centro-Oeste | 0 |
