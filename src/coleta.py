"""Etapa 1 – Coleta automatizada e reprodutível.

Baixa, valida e converte para Parquet:
  * Microdados do Censo da Educação Superior (INEP), 2009–2024 – tabelas de cursos e de IES;
  * Microdados do ENADE (INEP), 2017, 2018, 2019, 2021, 2023 – blocos curso, desempenho, sexo e idade;
  * População residente por UF (IBGE/SIDRA) e tabela de municípios (IBGE/Localidades).

Uso:
    python src/coleta.py                 # tudo
    python src/coleta.py --so-download   # só baixa os ZIPs/JSONs
    python src/coleta.py --benchmark     # também mede CSV × Parquet (tamanho e tempo de leitura)

Recursos: repetição com backoff em caso de erro, verificação de arquivos já baixados
(tamanho do Content-Length + MD5 registrado), conversão latin-1/';' → Parquet particionado
por ano, registro de metadados em reports/metadados_coleta.csv.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import io
import json
import shutil
import ssl
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import certifi
import duckdb
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

TMP = C.BRONZE / "_tmp_csv"


# ------------------------------------------------------------------ utilidades HTTP
def garantir_ca_bundle() -> Path:
    """Monta bundle de CAs = certifi + intermediário RNP/GlobalSign (que o INEP não envia)."""
    if C.CA_BUNDLE.exists():
        return C.CA_BUNDLE
    C.CERTS.mkdir(parents=True, exist_ok=True)
    der = requests.get(C.URL_CERT_INTERMEDIARIO, timeout=60).content
    pem = ssl.DER_cert_to_PEM_cert(der) if not der.startswith(b"-----BEGIN") else der.decode()
    C.CA_BUNDLE.write_text(Path(certifi.where()).read_text() + "\n" + pem)
    return C.CA_BUNDLE


def sessao() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "projeto-academico-censo-educacao-superior/1.0"
    s.verify = str(garantir_ca_bundle())
    return s


def md5(caminho: Path, bloco: int = 1 << 20) -> str:
    h = hashlib.md5()
    with open(caminho, "rb") as f:
        for b in iter(lambda: f.read(bloco), b""):
            h.update(b)
    return h.hexdigest()


def baixar(s: requests.Session, url: str, destino: Path, tentativas: int = 5) -> dict:
    """Baixa `url` para `destino` com retomada lógica: pula se já existe com o tamanho certo."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tamanho_remoto = None
    for t in range(1, tentativas + 1):
        try:
            h = s.head(url, timeout=60, allow_redirects=True)
            h.raise_for_status()
            tamanho_remoto = int(h.headers.get("Content-Length", 0)) or None
            break
        except requests.RequestException as e:
            print(f"  HEAD falhou ({t}/{tentativas}): {e}")
            time.sleep(2 ** t)

    if destino.exists() and (tamanho_remoto is None or destino.stat().st_size == tamanho_remoto):
        print(f"  já baixado: {destino.name}")
        return {"arquivo": destino.name, "url": url, "bytes": destino.stat().st_size,
                "baixado_agora": False, "data_download": datetime.fromtimestamp(
                    destino.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")}

    parcial = destino.with_suffix(destino.suffix + ".part")
    for t in range(1, tentativas + 1):
        try:
            with s.get(url, stream=True, timeout=(30, 300)) as r:
                r.raise_for_status()
                with open(parcial, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            if tamanho_remoto and parcial.stat().st_size != tamanho_remoto:
                raise IOError(f"tamanho {parcial.stat().st_size} != {tamanho_remoto}")
            parcial.rename(destino)
            print(f"  baixado: {destino.name} ({destino.stat().st_size/1e6:.1f} MB)")
            return {"arquivo": destino.name, "url": url, "bytes": destino.stat().st_size,
                    "baixado_agora": True,
                    "data_download": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        except (requests.RequestException, IOError) as e:
            espera = 2 ** t
            print(f"  erro ({t}/{tentativas}) em {url}: {e} – nova tentativa em {espera}s")
            time.sleep(espera)
    raise RuntimeError(f"Falha definitiva ao baixar {url}")


def get_json(s: requests.Session, url: str, tentativas: int = 5):
    for t in range(1, tentativas + 1):
        try:
            r = s.get(url, timeout=120)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  erro ({t}/{tentativas}) em {url}: {e}")
            time.sleep(2 ** t)
    raise RuntimeError(f"Falha definitiva: {url}")


# ------------------------------------------------------------------ conversão p/ Parquet
def csv_para_parquet(csv: Path, destino_dir: Path, ano: int) -> dict:
    """Lê CSV ';' (já em UTF-8) com DuckDB e grava Parquet em destino_dir/ano=AAAA/parte.parquet."""
    out = destino_dir / f"ano={ano}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    alvo = out / "parte.parquet"
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    # all_varchar na camada bronze: preserva o dado exatamente como publicado
    # (zeros à esquerda, '.', códigos com aspas); a tipagem é feita na camada silver.
    rel = con.read_csv(str(csv), delimiter=";", header=True,
                       all_varchar=True, quotechar='"', strict_mode=False)
    rel.write_parquet(str(alvo), compression="zstd")
    linhas = con.execute(f"select count(*) from '{alvo}'").fetchall()[0][0]
    colunas = len(rel.columns)
    con.close()
    return {"linhas": linhas, "colunas": colunas, "bytes_parquet": alvo.stat().st_size}


def extrair(zf: zipfile.ZipFile, membro: str, destino: Path, encoding: str = "latin-1") -> Path:
    """Extrai um membro do ZIP convertendo a codificação de origem (latin-1) para UTF-8."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(membro) as bsrc, open(destino, "w", encoding="utf-8", newline="") as dst:
        src = io.TextIOWrapper(bsrc, encoding=encoding, newline="")
        shutil.copyfileobj(src, dst, 1 << 20)
    return destino


# ------------------------------------------------------------------ fontes
def coletar_censo(s, so_download=False) -> list[dict]:
    metas = []
    for ano in C.ANOS_CENSO:
        url = C.URL_CENSO.format(ano=ano)
        print(f"[Censo {ano}]")
        zpath = C.RAW_CENSO / Path(url).name
        m = baixar(s, url, zpath)
        m["md5_zip"] = md5(zpath)
        if so_download:
            metas.append(m)
            continue
        with zipfile.ZipFile(zpath) as zf:
            for tabela, padrao in [("censo_cursos", "CURSOS"), ("censo_ies", "_IES_")]:
                membro = next(n for n in zf.namelist()
                              if padrao in n.upper() and n.upper().endswith(".CSV"))
                csv = extrair(zf, membro, TMP / tabela / f"{ano}.csv")
                info = csv_para_parquet(csv, C.BRONZE / tabela, ano)
                metas.append({**m, "fonte": "INEP – Censo da Educação Superior", "tabela": tabela,
                              "ano": ano, "membro_zip": membro, "bytes_csv": csv.stat().st_size, **info})
                print(f"  {tabela}: {info['linhas']:,} linhas × {info['colunas']} colunas")
    return metas


def coletar_enade(s, so_download=False) -> list[dict]:
    metas = []
    for ano, url in C.URL_ENADE.items():
        print(f"[ENADE {ano}]")
        zpath = C.RAW_ENADE / Path(url).name
        m = baixar(s, url, zpath)
        m["md5_zip"] = md5(zpath)
        if so_download:
            metas.append(m)
            continue
        with zipfile.ZipFile(zpath) as zf:
            for arq, tabela in C.ENADE_ARQUIVOS.items():
                membro = next(n for n in zf.namelist() if n.lower().endswith(f"_{arq}.txt"))
                csv = extrair(zf, membro, TMP / tabela / f"{ano}.csv")
                info = csv_para_parquet(csv, C.BRONZE / tabela, ano)
                metas.append({**m, "fonte": "INEP – ENADE", "tabela": tabela, "ano": ano,
                              "membro_zip": membro, "bytes_csv": csv.stat().st_size, **info})
                print(f"  {tabela}: {info['linhas']:,} linhas × {info['colunas']} colunas")
    return metas


def _sidra_df(dados) -> pd.DataFrame:
    df = pd.DataFrame(dados[1:])
    return pd.DataFrame({"co_uf": df["D1C"].astype(int), "ano": df["D3C"].astype(int),
                         "populacao": pd.to_numeric(df["V"], errors="coerce")})


def coletar_ibge(s) -> list[dict]:
    print("[IBGE]")
    C.RAW_IBGE.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metas, partes = [], []
    for nome, url in [("sidra_6579_estimativas", C.URL_SIDRA_ESTIMATIVAS),
                      ("sidra_4709_censo2022", C.URL_SIDRA_CENSO2022),
                      ("sidra_1378_censo2010", C.URL_SIDRA_CENSO2010)]:
        dados = get_json(s, url)
        (C.RAW_IBGE / f"{nome}.json").write_text(json.dumps(dados, ensure_ascii=False))
        df = _sidra_df(dados)
        df["origem"] = nome
        partes.append(df)
        metas.append({"fonte": "IBGE – SIDRA", "tabela": nome, "url": url, "data_download": agora,
                      "linhas": len(df), "colunas": df.shape[1], "baixado_agora": True,
                      "arquivo": f"{nome}.json", "bytes": (C.RAW_IBGE / f"{nome}.json").stat().st_size})
    pop = pd.concat(partes).dropna(subset=["populacao"])
    (C.BRONZE / "ibge_populacao_uf").mkdir(parents=True, exist_ok=True)
    pop.to_parquet(C.BRONZE / "ibge_populacao_uf" / "populacao_uf.parquet", index=False)

    mun = get_json(s, C.URL_IBGE_MUNICIPIOS)
    (C.RAW_IBGE / "municipios.json").write_text(json.dumps(mun, ensure_ascii=False))
    linhas = []
    for m in mun:
        mic = m.get("microrregiao") or {}
        uf = (mic.get("mesorregiao") or {}).get("UF") or \
             ((m.get("regiao-imediata") or {}).get("regiao-intermediaria") or {}).get("UF") or {}
        linhas.append({"co_municipio": m["id"], "no_municipio": m["nome"],
                       "co_uf": uf.get("id"), "sg_uf": uf.get("sigla"),
                       "no_regiao": (uf.get("regiao") or {}).get("nome")})
    dfm = pd.DataFrame(linhas)
    (C.BRONZE / "ibge_municipios").mkdir(parents=True, exist_ok=True)
    dfm.to_parquet(C.BRONZE / "ibge_municipios" / "municipios.parquet", index=False)
    metas.append({"fonte": "IBGE – Localidades", "tabela": "ibge_municipios", "url": C.URL_IBGE_MUNICIPIOS,
                  "data_download": agora, "linhas": len(dfm), "colunas": dfm.shape[1],
                  "arquivo": "municipios.json", "baixado_agora": True,
                  "bytes": (C.RAW_IBGE / "municipios.json").stat().st_size})
    # malha das UFs (GeoJSON) para os mapas coropléticos
    malha = get_json(s, C.URL_IBGE_MALHA_UF)
    (C.RAW_IBGE / "malha_uf.geojson").write_text(json.dumps(malha, ensure_ascii=False))
    metas.append({"fonte": "IBGE – Malhas", "tabela": "ibge_malha_uf", "url": C.URL_IBGE_MALHA_UF,
                  "data_download": agora, "linhas": len(malha["features"]), "arquivo": "malha_uf.geojson",
                  "baixado_agora": True, "bytes": (C.RAW_IBGE / "malha_uf.geojson").stat().st_size})
    print(f"  população: {len(pop)} linhas; municípios: {len(dfm)}; malha UF: {len(malha['features'])} polígonos")
    return metas


# ------------------------------------------------------------------ benchmark CSV × Parquet
def benchmark() -> pd.DataFrame:
    """Compara tamanho em disco e tempo de leitura (pandas) CSV × Parquet por tabela/ano."""
    res = []
    for tabela_dir in sorted(TMP.iterdir()):
        for csv in sorted(tabela_dir.glob("*.csv")):
            ano = int(csv.stem)
            pq = C.BRONZE / tabela_dir.name / f"ano={ano}" / "parte.parquet"
            t0 = time.perf_counter()
            df = pd.read_csv(csv, sep=";", encoding="utf-8", dtype=str, engine="pyarrow")
            t_csv = time.perf_counter() - t0
            del df
            gc.collect()
            t0 = time.perf_counter()
            df = pd.read_parquet(pq)
            t_pq = time.perf_counter() - t0
            del df
            gc.collect()
            res.append({"tabela": tabela_dir.name, "ano": ano,
                        "mb_csv": csv.stat().st_size / 1e6, "mb_parquet": pq.stat().st_size / 1e6,
                        "seg_leitura_csv": t_csv, "seg_leitura_parquet": t_pq})
            print(f"  {tabela_dir.name} {ano}: CSV {t_csv:.1f}s × Parquet {t_pq:.1f}s")
    df = pd.DataFrame(res)
    df["reducao_tamanho_pct"] = 100 * (1 - df.mb_parquet / df.mb_csv)
    df["ganho_velocidade_x"] = df.seg_leitura_csv / df.seg_leitura_parquet
    return df


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--so-download", action="store_true")
    ap.add_argument("--benchmark", action="store_true")
    ap.add_argument("--manter-csv", action="store_true", help="não apaga os CSVs extraídos")
    ap.add_argument("--so-benchmark", action="store_true",
                    help="só refaz o benchmark sobre os CSVs já extraídos em data/bronze/_tmp_csv")
    ap.add_argument("--so-malha", action="store_true", help="só baixa a malha de UFs do IBGE")
    a = ap.parse_args()
    if a.so_benchmark:
        print("[Benchmark CSV × Parquet]")
        benchmark().to_csv(C.REPORTS / "benchmark_csv_parquet.csv", index=False)
        return
    if a.so_malha:
        C.RAW_IBGE.mkdir(parents=True, exist_ok=True)
        malha = get_json(sessao(), C.URL_IBGE_MALHA_UF)
        (C.RAW_IBGE / "malha_uf.geojson").write_text(json.dumps(malha, ensure_ascii=False))
        print(f"  malha UF: {len(malha['features'])} polígonos")
        return

    C.REPORTS.mkdir(exist_ok=True)
    s = sessao()
    metas = coletar_censo(s, a.so_download) + coletar_enade(s, a.so_download)
    if not a.so_download:
        metas += coletar_ibge(s)
    meta = pd.DataFrame(metas)
    meta.to_csv(C.REPORTS / "metadados_coleta.csv", index=False)
    print(f"\nMetadados: {C.REPORTS / 'metadados_coleta.csv'}")

    if not a.so_download:
        resumo = meta.groupby("tabela").agg(arquivos=("ano", "count"), linhas=("linhas", "sum"),
                                            mb_csv=("bytes_csv", lambda x: x.sum() / 1e6),
                                            mb_parquet=("bytes_parquet", lambda x: x.sum() / 1e6))
        print(resumo.to_string())
        print(f"TOTAL de linhas: {int(resumo.linhas.sum()):,}")
        if a.benchmark:
            print("\n[Benchmark CSV × Parquet]")
            benchmark().to_csv(C.REPORTS / "benchmark_csv_parquet.csv", index=False)
        if not a.manter_csv and TMP.exists():
            shutil.rmtree(TMP)


if __name__ == "__main__":
    main()
