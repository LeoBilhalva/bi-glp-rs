"""Testes dos limites definidos na Fase 1 e da integridade dos cálculos."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from shutil import copytree

import numpy as np
import pandas as pd

from src.analytics import avaliar, prever
from src.pipeline import centavos, classificar, executar_pipeline, limpar_coletas


class TestesProjeto(unittest.TestCase):
    def test_precos(self):
        for raw, expected in [("105,50", 10550), ("105", 10500), ("0", None),
                              ("-2", None), ("abc", None), ("1,999", None)]:
            with self.subTest(preco=raw):
                self.assertEqual(centavos(raw), expected)

    def test_limites_h2(self):
        cases = [(0, False, "Sem dados"), (4, True, "Amostra reduzida"),
                 (5, True, "Elegível"), (5, False, "Divergência")]
        for n, ok, expected in cases:
            self.assertEqual(classificar(n, ok), expected)

    def test_duplicata_e_conflito(self):
        raw = pd.read_csv(Path(__file__).parent/"data/raw/coletas_rs.csv",
                          sep=";", dtype=str, keep_default_na=False)
        sample = raw[pd.to_datetime(raw["Data da Coleta"], format="%d/%m/%Y").between("2025-07-06","2025-12-27")].head(1)
        duplicated = pd.concat([sample,sample],ignore_index=True)
        clean, rejected, audit = limpar_coletas(duplicated)
        self.assertEqual((len(clean),len(rejected),audit["duplicatas"]),(1,1,1))
        conflicted = duplicated.copy()
        conflicted.loc[1,"Valor de Venda"] = "999"
        clean, rejected, audit = limpar_coletas(conflicted)
        self.assertEqual((len(clean),len(rejected),audit["conflitantes"]),(0,2,2))

    def test_carga_reexecutavel_e_h1(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            copytree(Path(__file__).parent/"data/raw", root/"data/raw")
            _, first, audit = executar_pipeline(root)
            _, second, _ = executar_pipeline(root)
            pd.testing.assert_frame_equal(first,second)
            self.assertEqual(audit["coletas_validas"],3471)
            self.assertEqual(audit["pares_observados"],367)
            self.assertEqual(audit["pares_conciliados"],367)
            self.assertTrue(audit["h1_atendida"])
            with sqlite3.connect(root/"data/processed/glp.sqlite") as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM fato_preco").fetchone()[0],3471)

    def test_grade_nao_transforma_ausencia_em_zero(self):
        root=Path(__file__).parent
        weekly=pd.read_csv(root/"data/processed/indicadores_semanais.csv")
        absent=weekly["status"].eq("Sem dados")
        self.assertTrue(weekly.loc[absent,"preco_medio"].isna().all())
        self.assertEqual(len(weekly),875)
        self.assertEqual(absent.sum(),508)

    def test_backtest_sem_futuro(self):
        y=np.array([100,101,99,102,100,103,102,104,103,105,104,106],dtype=float)
        dates=pd.Series(pd.date_range("2025-01-05",periods=len(y),freq="W-SUN"))
        actual=avaliar(y,dates,range(10,12),"Teste")
        self.assertTrue((actual["treino_ate"] < actual["semana"]).all())
        first=actual[(actual["modelo"]=="Ridge") & (actual["semana"]==dates.iloc[10])]
        self.assertAlmostEqual(first.iloc[0]["previsto"],prever(y[:10],"Ridge"))
        future_changed=y.copy()
        future_changed[10:]=999
        altered=avaliar(future_changed,dates,range(10,12),"Teste")
        first_altered=altered[(altered["modelo"]=="Ridge")&(altered["semana"]==dates.iloc[10])]
        self.assertAlmostEqual(first.iloc[0]["previsto"],first_altered.iloc[0]["previsto"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
