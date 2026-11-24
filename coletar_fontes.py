"""Atualiza os recortes a partir dos dois arquivos oficiais da ANP.

Execute separadamente quando desejar uma nova versão das fontes.
A execução normal do estudo usa os recortes congelados já incluídos.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
from openpyxl import load_workbook

BASE = "https://www.gov.br/anp/pt-br/"
CSV_URL = BASE + "centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/glp/glp-2025-02.csv"
XLSX_URL = BASE + "assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/shlp/semanal/semanal-municipio-2024-2025.xlsx"


def baixar(url: str, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".download")
    with urlopen(url, timeout=90) as response, temporary.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    os.replace(temporary, destination)


def atualizar(root: Path) -> None:
    originals = root / "data/originais"
    raw = root / "data/raw"
    originals.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    csv_file = originals / "glp-2025-02.csv"
    xlsx_file = originals / "semanal-municipio-2024-2025.xlsx"
    baixar(CSV_URL, csv_file)
    baixar(XLSX_URL, xlsx_file)
    coletas = pd.read_csv(csv_file, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    coletas.insert(0, "linha_origem", range(2, len(coletas) + 2))
    coletas = coletas[(coletas["Estado - Sigla"] == "RS") & (coletas["Produto"] == "GLP")]
    coletas = coletas.copy()
    identifiers = pd.factorize(coletas["CNPJ da Revenda"], sort=False)[0] + 1
    coletas["id_revenda"] = ["R" + str(n).zfill(6) for n in identifiers]
    coletas["linha_origem"] = range(1, len(coletas) + 1)
    public_columns = ["linha_origem", "Estado - Sigla", "Municipio", "id_revenda",
                      "Produto", "Data da Coleta", "Valor de Venda", "Unidade de Medida"]
    coletas = coletas[public_columns]
    coletas.to_csv(raw / "coletas_rs.csv", sep=";", index=False, encoding="utf-8")
    workbook = load_workbook(xlsx_file, read_only=True, data_only=True)
    rows = []
    for row in workbook.active.iter_rows(min_row=13, values_only=True):
        if (row[3] == "RIO GRANDE DO SUL" and row[5] == "GLP"
                and datetime(2025, 7, 6) <= row[0] <= datetime(2025, 12, 21)):
            rows.append([row[0].strftime("%Y-%m-%d"), row[1].strftime("%Y-%m-%d"),
                         row[4], row[6], row[8], row[10], row[11]])
    workbook.close()
    columns = ["semana", "fim_semana", "municipio", "n_oficial", "media_oficial", "min_oficial", "max_oficial"]
    pd.DataFrame(rows, columns=columns).to_csv(raw / "referencia_rs.csv", sep=";", index=False)
    now = datetime.now(timezone.utc).isoformat()
    sources = []
    for original, url, subset, filter_description, count in [
        (csv_file, CSV_URL, "coletas_rs.csv", "Estado - Sigla = RS e Produto = GLP", len(coletas)),
        (xlsx_file, XLSX_URL, "referencia_rs.csv", "RS, GLP e semanas completas entre 06/07 e 27/12/2025", len(rows)),
    ]:
        sources.append({"arquivo_original": original.name, "url": url,
                        "sha256_original": hashlib.sha256(original.read_bytes()).hexdigest(),
                        "bytes_original": original.stat().st_size, "obtido_em": now,
                        "arquivo_recorte": subset, "filtro": filter_description, "linhas": count,
                        "sha256_recorte": hashlib.sha256((raw / subset).read_bytes()).hexdigest()})
    manifest = {"fontes": sources, "unidade": "R$ por botijão de 13 kg",
                "nota": "Recortes atualizados diretamente dos arquivos oficiais. Reexecute run.py para atualizar resultados."}
    (raw / "fontes.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Recortes atualizados: {len(coletas)} coletas RS e {len(rows)} referências municipais.")


if __name__ == "__main__":
    atualizar(Path(__file__).resolve().parent)
