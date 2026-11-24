"""Coleta, limpeza, modelo dimensional e conciliação dos preços de GLP P13."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.request import urlopen

import numpy as np
import pandas as pd

INICIO = pd.Timestamp("2025-07-06")
FIM = pd.Timestamp("2025-12-27")
MIN_COLETAS = 5


def normalizar_municipio(values: pd.Series) -> pd.Series:
    """A chave textual preserva o padrão sem acentos usado nos arquivos da ANP."""
    return values.astype(str).str.strip().str.upper()


def centavos(value: object) -> int | None:
    """Converte preços com vírgula decimal sem truncar casas decimais."""
    try:
        price = Decimal(str(value).strip().replace(",", "."))
        if not price.is_finite() or price <= 0:
            return None
        rounded = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if rounded != price:
            return None
        return int(rounded * 100)
    except (InvalidOperation, ValueError, OverflowError):
        return None


def classificar(n_coletas: int, conciliado: bool) -> str:
    if n_coletas == 0:
        return "Sem dados"
    if n_coletas < MIN_COLETAS:
        return "Amostra reduzida"
    if not conciliado:
        return "Divergência"
    return "Elegível"


def verificar_fontes(root: Path) -> dict:
    manifest = json.loads((root / "data/raw/fontes.json").read_text(encoding="utf-8"))
    for item in manifest["fontes"]:
        path = root / "data/raw" / item["arquivo_recorte"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256_recorte"]:
            raise ValueError(f"Arquivo alterado desde a preparação: {path.name}")
    return manifest


def coletar_arquivos_originais(root: Path) -> list[str]:
    """Download opcional para auditoria. A execução padrão usa o recorte congelado."""
    manifest = verificar_fontes(root)
    destination = root / "data/originais"
    destination.mkdir(parents=True, exist_ok=True)
    saved = []
    for item in manifest["fontes"]:
        path = destination / item["arquivo_original"]
        temporary = path.with_suffix(path.suffix + ".tmp")
        with urlopen(item["url"], timeout=90) as response:
            temporary.write_bytes(response.read())
        os.replace(temporary, path)
        saved.append(str(path))
    return saved


def limpar_coletas(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    required = ["linha_origem", "Estado - Sigla", "Municipio", "id_revenda",
                "Produto", "Data da Coleta", "Valor de Venda", "Unidade de Medida"]
    missing = set(required) - set(raw.columns)
    if missing:
        raise ValueError(f"Campos ausentes: {sorted(missing)}")
    data = raw[(raw["Estado - Sigla"] == "RS") & (raw["Produto"] == "GLP")].copy()
    data["data"] = pd.to_datetime(data["Data da Coleta"], format="%d/%m/%Y", errors="coerce")
    data["municipio"] = normalizar_municipio(data["Municipio"])
    data["id_origem"] = data["id_revenda"].astype(str).str.strip()
    data["preco_centavos"] = data["Valor de Venda"].map(centavos)
    data["motivo"] = ""
    invalid = {
        "data inválida": data["data"].isna(),
        "município ausente": data["municipio"].isin(["", "NAN", "NONE"]),
        "identificador de revenda inválido": ~data["id_origem"].str.fullmatch(r"R\d{6}"),
        "preço inválido": data["preco_centavos"].isna(),
        "unidade incompatível": data["Unidade de Medida"].str.replace(" ", "", regex=False).ne("R$/13kg"),
    }
    for reason, mask in invalid.items():
        data.loc[mask & data["motivo"].eq(""), "motivo"] = reason
    invalid_rows = data[data["motivo"].ne("")].copy()
    outside = data["data"].notna() & ~data["data"].between(INICIO, FIM)
    scoped = data[data["data"].between(INICIO, FIM) & data["motivo"].eq("")].copy()
    key = ["id_origem", "data", "Produto"]
    # Mesma chave com município ou preço diferente exige revisão.
    conflicted = scoped.groupby(key)[["municipio", "preco_centavos"]].transform("nunique").gt(1).any(axis=1)
    conflict_rows = scoped[conflicted].copy()
    conflict_rows["motivo"] = "coletas conflitantes para a mesma chave"
    scoped = scoped[~conflicted].copy()
    duplicates = scoped.duplicated(key, keep="first")
    duplicate_rows = scoped[duplicates].copy()
    duplicate_rows["motivo"] = "duplicata exata da medição"
    clean = scoped[~duplicates].copy()
    clean["preco_centavos"] = clean["preco_centavos"].astype(int)
    clean["semana"] = clean["data"] - pd.to_timedelta((clean["data"].dt.weekday + 1) % 7, unit="D")
    rejected = pd.concat([invalid_rows, conflict_rows, duplicate_rows], ignore_index=True)
    audit = {
        "linhas_rs_brutas": len(data),
        "municipios_rs_brutos": data["municipio"].nunique(),
        "fora_do_recorte": int(outside.sum()),
        "invalidas": len(invalid_rows),
        "conflitantes": len(conflict_rows),
        "duplicatas": len(duplicate_rows),
        "coletas_validas": len(clean),
    }
    return clean, rejected, audit


def agregar_e_conciliar(clean: pd.DataFrame, reference: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    ref = reference.copy()
    ref["municipio"] = normalizar_municipio(ref["municipio"])
    ref["semana"] = pd.to_datetime(ref["semana"], errors="raise")
    if ref.duplicated(["municipio", "semana"]).any():
        raise ValueError("Referência oficial contém chaves repetidas.")
    ref = ref[ref["semana"].between(INICIO, FIM)]
    grouped = clean.groupby(["municipio", "semana"], as_index=False).agg(
        n_coletas=("preco_centavos", "size"),
        soma_centavos=("preco_centavos", "sum"),
        minimo_centavos=("preco_centavos", "min"),
        maximo_centavos=("preco_centavos", "max"),
    )
    grouped["preco_medio"] = grouped.apply(
        lambda row: float((Decimal(int(row["soma_centavos"])) /
                           Decimal(int(row["n_coletas"])) / 100).quantize(
                               Decimal("0.01"), rounding=ROUND_HALF_UP)), axis=1)
    union = grouped.merge(ref, how="outer", on=["municipio", "semana"], validate="one_to_one")
    union["diferenca_media"] = (union["preco_medio"] - union["media_oficial"]).abs()
    union["conciliado"] = (union["n_coletas"].eq(union["n_oficial"]) &
                            union["diferenca_media"].le(0.01000001))
    municipios = sorted(set(clean["municipio"]) | set(ref["municipio"]))
    weeks = pd.date_range(INICIO, FIM, freq="W-SUN")
    grid = pd.MultiIndex.from_product([municipios, weeks], names=["municipio", "semana"]).to_frame(index=False)
    weekly = grid.merge(union, on=["municipio", "semana"], how="left", validate="one_to_one")
    weekly["n_coletas"] = weekly["n_coletas"].fillna(0).astype(int)
    weekly["conciliado"] = weekly["conciliado"].eq(True)
    weekly["status"] = [classificar(n, bool(c)) for n, c in zip(weekly["n_coletas"], weekly["conciliado"])]
    weekly["amplitude"] = (weekly["maximo_centavos"] - weekly["minimo_centavos"]) / 100
    weekly["fim_semana"] = weekly["semana"] + pd.Timedelta(days=6)
    # A grade semanal impede variações sobre semanas saltadas.
    weekly["variacao_pct"] = weekly.groupby("municipio")["preco_medio"].pct_change(fill_method=None) * 100
    current_ready = weekly["status"].eq("Elegível")
    previous_ready = current_ready.groupby(weekly["municipio"]).shift(1, fill_value=False)
    weekly.loc[~(current_ready & previous_ready), "variacao_pct"] = np.nan
    audit = {
        "pares_observados": len(union),
        "pares_conciliados": int(union["conciliado"].sum()),
        "taxa_conciliacao_pct": float(union["conciliado"].mean() * 100),
        "grade_municipio_semana": len(weekly),
        "municipios": len(municipios),
        "semanas": len(weeks),
        "status": {k: int(v) for k, v in weekly["status"].value_counts().items()},
        "maior_diferenca_media": float(union["diferenca_media"].max()),
        "h1_atendida": bool(union["conciliado"].mean() >= 0.95),
    }
    return weekly, audit


def salvar_banco(clean: pd.DataFrame, weekly: pd.DataFrame, rejected: pd.DataFrame, root: Path) -> None:
    """Substitui uma carga completa por arquivo temporário, sem acumular duplicatas."""
    destination = root / "data/processed/glp.sqlite"
    handle, temporary_name = tempfile.mkstemp(suffix=".sqlite", prefix=".carga-", dir=destination.parent)
    os.close(handle)
    temporary = Path(temporary_name)
    municipios = pd.DataFrame({"municipio": sorted(weekly["municipio"].unique())})
    municipios.insert(0, "municipio_id", range(1, len(municipios) + 1))
    revendas = clean[["id_origem", "municipio"]].drop_duplicates().sort_values(["id_origem", "municipio"]).reset_index(drop=True)
    revendas.insert(0, "revenda_id", range(1, len(revendas) + 1))
    revendas = revendas.merge(municipios, on="municipio", validate="many_to_one")
    dates = pd.DataFrame({"data": pd.date_range(INICIO, FIM, freq="D")})
    dates["data_id"] = dates["data"].dt.strftime("%Y%m%d").astype(int)
    dates["semana"] = dates["data"] - pd.to_timedelta((dates["data"].dt.weekday + 1) % 7, unit="D")
    fact = clean.merge(revendas[["id_origem", "municipio", "revenda_id", "municipio_id"]],
                       on=["id_origem", "municipio"], validate="many_to_one")
    fact["data_id"] = fact["data"].dt.strftime("%Y%m%d").astype(int)
    fact["produto"] = "GLP"
    fact = fact[["linha_origem", "revenda_id", "municipio_id", "data_id", "produto", "preco_centavos"]]
    with sqlite3.connect(temporary) as db:
        municipios.to_sql("dim_municipio", db, index=False)
        revendas[["revenda_id", "id_origem", "municipio_id"]].to_sql("dim_revenda", db, index=False)
        dates.to_sql("dim_data", db, index=False)
        fact.to_sql("fato_preco", db, index=False)
        weekly.to_sql("indicador_semanal", db, index=False)
        rejected[["linha_origem", "id_origem", "data", "preco_centavos", "motivo"]].to_sql("rejeicoes", db, index=False)
        for table, field in [("dim_municipio", "municipio_id"), ("dim_revenda", "revenda_id"), ("dim_data", "data_id")]:
            db.execute(f"CREATE UNIQUE INDEX pk_{table} ON {table} ({field})")
        db.execute("CREATE UNIQUE INDEX uk_fato ON fato_preco (revenda_id, data_id, produto)")
        db.execute("CREATE UNIQUE INDEX uk_semanal ON indicador_semanal (municipio, semana)")
        orphan_count = db.execute("""
            SELECT COUNT(*) FROM fato_preco f
            LEFT JOIN dim_revenda r ON f.revenda_id=r.revenda_id
            LEFT JOIN dim_municipio m ON f.municipio_id=m.municipio_id
            LEFT JOIN dim_data d ON f.data_id=d.data_id
            WHERE r.revenda_id IS NULL OR m.municipio_id IS NULL OR d.data_id IS NULL
        """).fetchone()[0]
        if orphan_count:
            raise ValueError("A carga gerou fatos sem dimensão.")
    os.replace(temporary, destination)


def executar_pipeline(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    verificar_fontes(root)
    destination = root / "data/processed"
    destination.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(root / "data/raw/coletas_rs.csv", sep=";", dtype=str, keep_default_na=False)
    reference = pd.read_csv(root / "data/raw/referencia_rs.csv", sep=";")
    clean, rejected, audit_clean = limpar_coletas(raw)
    if clean.empty:
        raise ValueError("Nenhuma coleta válida no período selecionado.")
    weekly, audit_weekly = agregar_e_conciliar(clean, reference)
    salvar_banco(clean, weekly, rejected, root)
    clean.to_csv(destination / "coletas_validas.csv", index=False)
    weekly.to_csv(destination / "indicadores_semanais.csv", index=False, date_format="%Y-%m-%d")
    rejected.to_csv(destination / "rejeicoes.csv", index=False)
    audit = {**audit_clean, **audit_weekly}
    audit["testes_h2"] = [
        {"coletas": n, "conciliado": c, "obtido": classificar(n, c), "esperado": e,
         "passou": classificar(n, c) == e}
        for n, c, e in [(0, False, "Sem dados"), (4, True, "Amostra reduzida"),
                         (5, True, "Elegível"), (5, False, "Divergência")]
    ]
    audit["h2_atendida"] = all(x["passou"] for x in audit["testes_h2"])
    (destination / "auditoria.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return clean, weekly, audit
