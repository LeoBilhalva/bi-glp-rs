"""Execute python run.py na raiz do projeto."""
import argparse
import json
from pathlib import Path

from src.pipeline import coletar_arquivos_originais, executar_pipeline
from src.analytics import executar_analytics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baixar-originais", action="store_true", help="Baixa os arquivos oficiais integrais para auditoria.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.baixar_originais:
        coletar_arquivos_originais(root)
    _, weekly, quality = executar_pipeline(root)
    forecast = executar_analytics(weekly, root)
    from src.dashboards import exportar_dashboards
    exportar_dashboards(weekly, root)
    print(json.dumps({"qualidade": quality, "analytics": forecast}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
