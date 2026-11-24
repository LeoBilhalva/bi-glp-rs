"""Previsão retrospectiva do preço médio semanal em Pelotas."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

MODELOS = ("Último preço", "Média de 3 semanas", "Ridge")


def prever(history: np.ndarray, model: str) -> float:
    """Usa apenas observações anteriores à data da previsão."""
    values = np.asarray(history, dtype=float)
    if len(values) < 8:
        raise ValueError("Histórico insuficiente para os modelos.")
    if model == "Último preço":
        return float(values[-1])
    if model == "Média de 3 semanas":
        return float(values[-3:].mean())
    if model != "Ridge":
        raise ValueError(f"Modelo desconhecido: {model}")
    features = np.array([values[i-3:i] for i in range(3, len(values))])
    target = values[3:]
    estimator = Ridge(alpha=1.0)
    estimator.fit(features, target)
    return float(estimator.predict(values[-3:].reshape(1, -1))[0])


def avaliar(y: np.ndarray, dates: pd.Series, indices: range, fase: str) -> pd.DataFrame:
    records = []
    for i in indices:
        for model in MODELOS:
            prediction = prever(y[:i], model)
            records.append({"fase": fase, "semana": dates.iloc[i], "modelo": model,
                            "real": float(y[i]), "previsto": prediction,
                            "treino_ate": dates.iloc[i-1]})
    return pd.DataFrame(records)


def executar_analytics(weekly: pd.DataFrame, root: Path) -> dict:
    series = weekly[weekly["municipio"].eq("PELOTAS")].sort_values("semana").copy()
    if len(series) < 20 or not series["status"].eq("Elegível").all():
        raise ValueError("Pelotas precisa de pelo menos 20 semanas consecutivas elegíveis.")
    y = series["preco_medio"].to_numpy(float)
    dates = series["semana"].reset_index(drop=True)
    # 10 semanas iniciais, 10 origens de validação e 5 origens finais intocadas na seleção.
    cut = len(y) - 5
    validation = avaliar(y, dates, range(10, cut), "Validação")
    testing = avaliar(y, dates, range(cut, len(y)), "Teste")
    results = []
    for frame in (validation, testing):
        for model in MODELOS:
            data = frame[frame["modelo"].eq(model)]
            results.append({"fase": data["fase"].iloc[0], "modelo": model, "n": len(data),
                            "mae": float(mean_absolute_error(data["real"], data["previsto"])),
                            "rmse": float(np.sqrt(mean_squared_error(data["real"], data["previsto"])))})
    scores = pd.DataFrame(results)
    # Empates respeitam a ordem, favorecendo o modelo mais simples.
    winner = scores[scores["fase"].eq("Validação")].sort_values("mae", kind="stable").iloc[0]["modelo"]
    errors = validation[validation["modelo"].eq(winner)]
    q90 = float(np.quantile(np.abs(errors["real"] - errors["previsto"]), 0.9))
    history = y.copy()
    ridge_history = y.copy()
    forecasts = []
    for h in range(1, 5):
        prediction = prever(history, winner)
        ridge_prediction = prever(ridge_history, "Ridge")
        future = dates.iloc[-1] + pd.Timedelta(weeks=h)
        margin = q90 * np.sqrt(h)
        forecasts.append({"semana": future, "fim_semana": future + pd.Timedelta(days=6),
                          "previsto": prediction, "ridge_previsto": ridge_prediction, "faixa_inferior": prediction-margin,
                          "faixa_superior": prediction+margin, "modelo": winner})
        history = np.append(history, prediction)
        ridge_history = np.append(ridge_history, ridge_prediction)
    forecast = pd.DataFrame(forecasts)
    destination = root / "outputs"
    destination.mkdir(parents=True, exist_ok=True)
    pd.concat([validation, testing]).to_csv(destination / "backtest.csv", index=False, date_format="%Y-%m-%d")
    scores.to_csv(destination / "metricas_modelos.csv", index=False)
    forecast.to_csv(destination / "previsoes.csv", index=False, date_format="%Y-%m-%d")
    test_winner = scores[scores["fase"].eq("Teste") & scores["modelo"].eq(winner)].iloc[0]
    summary = {
        "municipio": "PELOTAS", "n_semanas": len(series),
        "ultimo_dado": dates.iloc[-1].strftime("%Y-%m-%d"),
        "treino_inicial_semanas": 10, "origens_validacao": len(y)-15, "origens_teste": 5,
        "modelo_selecionado": winner, "horizonte_semanas": 4,
        "mae_teste": float(test_winner["mae"]), "rmse_teste": float(test_winner["rmse"]),
        "validacao_inicio": dates.iloc[10].strftime("%Y-%m-%d"),
        "validacao_fim": dates.iloc[cut-1].strftime("%Y-%m-%d"),
        "teste_inicio": dates.iloc[cut].strftime("%Y-%m-%d"),
        "teste_fim": dates.iloc[-1].strftime("%Y-%m-%d"),
        "nota": "Previsões retrospectivas a partir de dezembro de 2025. Teste de um passo com atualização semanal. Projeção final recursiva de quatro passos. Faixa ilustrativa baseada no percentil 90 do erro de validação e raiz do horizonte, sem garantia de cobertura."
    }
    (destination / "analytics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
