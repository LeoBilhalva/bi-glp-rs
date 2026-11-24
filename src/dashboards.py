"""Visualizações em Plotly para Colab e cópias HTML que funcionam sem servidor."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from plotly.subplots import make_subplots

CORES = {"Sem dados": "#e7e9ed", "Amostra reduzida": "#d79c32",
         "Divergência": "#b34e4e", "Elegível": "#2d8c64"}
CODES = {name: code for code, name in enumerate(CORES)}
BLUE = "#175c8d"
GREEN = "#2d8c64"


def mercado(weekly: pd.DataFrame, municipio: str = "PELOTAS") -> go.Figure:
    data = weekly[weekly["municipio"].eq(municipio)].sort_values("semana")
    ready = data["status"].eq("Elegível")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
                        row_heights=[0.65, 0.35], subplot_titles=("Preço e faixa observada", "Número de coletas"))
    fig.add_trace(go.Scatter(x=data["semana"], y=data["maximo_centavos"]/100,
                            mode="lines", line=dict(width=0), name="Máximo"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data["semana"], y=data["minimo_centavos"]/100,
                            fill="tonexty", fillcolor="rgba(23,92,141,.12)",
                            mode="lines", line=dict(width=0), name="Mínimo"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data["semana"], y=data["preco_medio"], mode="lines+markers",
                            line=dict(color=BLUE), connectgaps=False, name="Média pesquisada",
                            customdata=data[["n_coletas", "status"]],
                            hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:.2f}<br>%{customdata[0]} coletas<br>%{customdata[1]}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.loc[~ready, "semana"], y=data.loc[~ready, "preco_medio"],
                            mode="markers", marker=dict(color="#d79c32", size=12, symbol="x"),
                            name="Requer atenção"), row=1, col=1)
    fig.add_trace(go.Bar(x=data["semana"], y=data["n_coletas"],
                        marker_color=[CORES[s] for s in data["status"]], name="Coletas"), row=2, col=1)
    fig.add_hline(y=5, row=2, col=1, line_dash="dot", line_color="#777777")
    fig.update_yaxes(title_text="R$ / 13 kg", row=1, col=1)
    fig.update_layout(title=f"{municipio} · GLP P13 · semanas de 06/07 a 27/12/2025",
                      height=680, template="plotly_white", margin=dict(t=100, l=70, r=30, b=40),
                      legend=dict(orientation="h", y=-0.10))
    return fig


def qualidade(weekly: pd.DataFrame) -> go.Figure:
    data = weekly.copy()
    data["code"] = data["status"].map(CODES)
    matrix = data.pivot(index="municipio", columns="semana", values="code")
    n = data.pivot(index="municipio", columns="semana", values="n_coletas")
    colors = [CORES[k] for k in CODES]
    scale = []
    for i, color in enumerate(colors):
        scale.extend([[i/4, color], [(i+1)/4, color]])
    fig = go.Figure(go.Heatmap(z=matrix.values, x=matrix.columns, y=matrix.index,
                               zmin=-0.5, zmax=3.5,
                               customdata=n.values, colorscale=scale,
                               colorbar=dict(tickvals=list(CODES.values()), ticktext=list(CODES)),
                               hovertemplate="%{y}<br>%{x|%d/%m/%Y}<br>%{customdata} coletas<extra></extra>"))
    fig.update_layout(title="Cobertura por município e semana", height=950,
                      template="plotly_white", margin=dict(l=175, t=70, r=150, b=70))
    return fig


def previsao(weekly: pd.DataFrame, root: Path) -> go.Figure:
    hist = weekly[weekly["municipio"].eq("PELOTAS")].sort_values("semana")
    forecast = pd.read_csv(root/"outputs/previsoes.csv", parse_dates=["semana"])
    backtest = pd.read_csv(root/"outputs/backtest.csv", parse_dates=["semana"])
    selected = json.loads((root/"outputs/analytics.json").read_text(encoding="utf-8"))["modelo_selecionado"]
    test = backtest[backtest["fase"].eq("Teste") & backtest["modelo"].eq(selected)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["semana"], y=hist["preco_medio"], mode="lines+markers", name="Histórico", line=dict(color=BLUE)))
    fig.add_trace(go.Scatter(x=test["semana"], y=test["previsto"], mode="lines+markers",
                            name="Teste de um passo", line=dict(color="#c18c21", dash="dot")))
    fig.add_trace(go.Scatter(x=forecast["semana"], y=forecast["faixa_superior"], mode="lines", line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=forecast["semana"], y=forecast["faixa_inferior"], fill="tonexty",
                            fillcolor="rgba(45,140,100,.14)", mode="lines", line=dict(width=0),
                            name="Faixa indicativa de erro"))
    fig.add_trace(go.Scatter(x=forecast["semana"], y=forecast["previsto"], mode="lines+markers",
                            line=dict(color=GREEN, dash="dash"), name=f"Projeção · {selected}"))
    fig.update_layout(title="Pelotas · projeção retrospectiva de quatro semanas",
                      yaxis_title="R$ / 13 kg", template="plotly_white", height=560,
                      margin=dict(t=80, l=70, b=70, r=30),
                      legend=dict(orientation="h", y=-0.18))
    return fig


def salvar_html(figure: go.Figure, title: str, note: str, destination: Path,
                extra: str = "", script: str = "") -> None:
    plot = figure.to_html(full_html=False, include_plotlyjs="plotly.min.js", div_id="grafico",
                          config={"responsive": True, "displaylogo": False})
    controls, separator, comparison = extra.partition("<h2>")
    html = f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>body{{font:16px Arial,sans-serif;color:#172735;max-width:1320px;margin:32px auto;padding:0 20px}}
nav a{{margin-right:24px;color:#175c8d}}h1{{font-size:27px}}p{{line-height:1.5}}select{{padding:9px;max-width:100%;font-size:16px}}</style>
<nav><a href="01_mercado.html">Mercado</a><a href="02_qualidade.html">Qualidade</a><a href="03_previsao.html">Previsão</a></nav>
<h1>{title}</h1><p>{note}</p>{controls}{plot}{separator}{comparison}{script}</html>"""
    destination.write_text(html, encoding="utf-8")


def static_figures(weekly: pd.DataFrame, root: Path) -> None:
    folder = root/"outputs"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    pelotas = weekly[weekly["municipio"].eq("PELOTAS")].sort_values("semana")
    fig, axes = plt.subplots(2, 1, figsize=(10.8, 6.1), sharex=True, gridspec_kw={"height_ratios":[3,1]})
    axes[0].plot(pelotas["semana"], pelotas["preco_medio"], marker="o", ms=4, color=BLUE)
    axes[0].fill_between(pelotas["semana"], pelotas["minimo_centavos"]/100,
                         pelotas["maximo_centavos"]/100, alpha=.12, color=BLUE, label="Mínimo e máximo pesquisados")
    axes[0].set_ylabel("R$ por botijão de 13 kg")
    axes[0].set_title("Pelotas · preço médio e faixa de preços pesquisados", loc="left", fontweight="bold")
    axes[0].legend(frameon=False,fontsize=9)
    axes[1].bar(pelotas["semana"], pelotas["n_coletas"], width=4, color=GREEN)
    axes[1].axhline(5,color="#a57414",lw=1,ls="--")
    axes[1].set_ylabel("Coletas")
    for ax in axes:
        ax.spines[["top","right"]].set_visible(False)
        ax.grid(axis="y",alpha=.18)
    fig.autofmt_xdate();fig.tight_layout();fig.savefig(folder/"mercado.png",dpi=180);plt.close(fig)

    latest = weekly[(weekly["semana"]==weekly["semana"].max()) & weekly["status"].eq("Elegível")].sort_values("preco_medio")
    latest = pd.concat([latest.head(5), latest.tail(5)]).drop_duplicates("municipio")
    fig,ax=plt.subplots(figsize=(9.8,5.8))
    bars=ax.barh(latest["municipio"],latest["preco_medio"],color=BLUE)
    ax.bar_label(bars,fmt="%.2f",padding=4)
    ax.set_xlim(0,latest["preco_medio"].max()*1.16)
    ax.set_xlabel("Média de revenda · R$ / 13 kg")
    ax.set_title("Cinco menores e cinco maiores médias · 21 a 27/12/2025",loc="left",fontweight="bold")
    ax.spines[["top","right"]].set_visible(False);fig.tight_layout()
    fig.savefig(folder/"comparacao.png",dpi=180);plt.close(fig)

    matrix=weekly.assign(code=weekly["status"].map(CODES)).pivot(index="municipio",columns="semana",values="code")
    from matplotlib.colors import ListedColormap, BoundaryNorm
    fig,ax=plt.subplots(figsize=(11,7.7))
    cmap=ListedColormap(list(CORES.values()))
    ax.imshow(matrix.values,aspect="auto",cmap=cmap,norm=BoundaryNorm([-0.5,.5,1.5,2.5,3.5],cmap.N))
    ax.set_yticks(range(len(matrix)),matrix.index,fontsize=8)
    ticks=list(range(0,len(matrix.columns),3))
    ax.set_xticks(ticks,[matrix.columns[i].strftime("%d/%m") for i in ticks],fontsize=9)
    ax.set_title("Cobertura por município e semana",loc="left",fontweight="bold")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=v,label=k) for k,v in CORES.items()],loc="upper center",
              bbox_to_anchor=(.5,-.06),ncol=4,frameon=False,fontsize=9)
    fig.tight_layout();fig.savefig(folder/"qualidade.png",dpi=180);plt.close(fig)

    fc=pd.read_csv(folder/"previsoes.csv",parse_dates=["semana"])
    scores=pd.read_csv(folder/"metricas_modelos.csv")
    test=pd.read_csv(folder/"backtest.csv",parse_dates=["semana"])
    model=json.loads((folder/"analytics.json").read_text())["modelo_selecionado"]
    chosen=test[test["fase"].eq("Teste")&test["modelo"].eq(model)]
    fig,ax=plt.subplots(figsize=(10.7,5.5))
    ax.plot(pelotas["semana"],pelotas["preco_medio"],marker="o",ms=4,label="Histórico",color=BLUE)
    ax.plot(chosen["semana"],chosen["previsto"],"--",label="Teste de um passo",color="#a57414")
    ax.plot(fc["semana"],fc["previsto"],"o--",label="Projeção de quatro semanas",color=GREEN)
    ax.fill_between(fc["semana"],fc["faixa_inferior"],fc["faixa_superior"],alpha=.15,color=GREEN,label="Faixa indicativa")
    ax.set_ylabel("R$ por botijão de 13 kg")
    ax.set_title("Pelotas · previsão com dados até 27/12/2025",loc="left",fontweight="bold")
    ax.spines[["top","right"]].set_visible(False);ax.grid(axis="y",alpha=.18)
    ax.legend(frameon=False,fontsize=9,ncol=2);fig.autofmt_xdate();fig.tight_layout()
    fig.savefig(folder/"previsao.png",dpi=180);plt.close(fig)

    fig,ax=plt.subplots(figsize=(9.3,4.4))
    models=list(scores["modelo"].unique());x=np.arange(len(models))
    for j,phase in enumerate(["Validação","Teste"]):
        data=scores[scores["fase"].eq(phase)].set_index("modelo").loc[models]
        bars=ax.bar(x+(j-.5)*.32,data["mae"],width=.32,label=phase,color=[BLUE,GREEN][j])
        ax.bar_label(bars,fmt="%.3f",padding=3,fontsize=10)
    ax.set_xticks(x,models);ax.set_ylabel("MAE · R$ por botijão")
    ax.set_ylim(0,scores["mae"].max()*1.3)
    ax.set_title("Erro de previsão de um passo",loc="left",fontweight="bold")
    ax.legend(frameon=False);ax.spines[["top","right"]].set_visible(False)
    fig.tight_layout();fig.savefig(folder/"modelos.png",dpi=180);plt.close(fig)


def exportar_dashboards(weekly: pd.DataFrame, root: Path) -> None:
    folder = root/"dashboards"
    folder.mkdir(parents=True, exist_ok=True)
    (folder/"plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
    municipalities=sorted(weekly["municipio"].unique())
    data = weekly.copy()
    for col in ("semana","fim_semana"):
        data[col]=data[col].dt.strftime("%Y-%m-%d")
    payload=data[["municipio","semana","preco_medio","minimo_centavos","maximo_centavos","n_coletas","status","variacao_pct"]].to_json(orient="records",force_ascii=False)
    options="".join(f'<option {"selected" if m=="PELOTAS" else ""}>{m}</option>' for m in municipalities)
    weeks=sorted(data["semana"].unique())
    week_options="".join(f'<option {"selected" if i==len(weeks)-1 else ""} value="{w}">{w}</option>' for i,w in enumerate(weeks))
    extra=f'<label for="municipio">Município </label><select id="municipio">{options}</select><h2>Comparação semanal</h2><label for="semana">Início da semana </label><select id="semana">{week_options}</select><p>Somente médias conciliadas com pelo menos cinco coletas. Ordem crescente de preço.</p><div id="comparacao"></div>' 
    script="""<script>const dados=PAYLOAD;
function comparar(){
const s=document.getElementById('semana').value;
const rows=dados.filter(r=>r.semana===s&&r.status==='Elegível').sort((a,b)=>a.preco_medio-b.preco_medio);
let html='<table style="border-collapse:collapse;width:100%;max-width:900px"><thead><tr><th style="text-align:left">Município</th><th>Média R$</th><th>Coletas</th><th>Variação %</th></tr></thead><tbody>';
for(const r of rows){html+='<tr style="border-bottom:1px solid #ddd"><td style="padding:7px">'+r.municipio+'</td><td style="text-align:center">'+r.preco_medio.toFixed(2).replace('.',',')+'</td><td style="text-align:center">'+r.n_coletas+'</td><td style="text-align:center">'+(r.variacao_pct===null?'Sem comparação':r.variacao_pct.toFixed(2).replace('.',','))+'</td></tr>';}
document.getElementById('comparacao').innerHTML=html+'</tbody></table>';
}
document.getElementById('semana').addEventListener('change',comparar);
comparar();
document.getElementById('municipio').addEventListener('change', e=>{
const d=dados.filter(r=>r.municipio===e.target.value),x=d.map(r=>r.semana);
const ys=[d.map(r=>r.maximo_centavos===null?null:r.maximo_centavos/100),
d.map(r=>r.minimo_centavos===null?null:r.minimo_centavos/100),
d.map(r=>r.preco_medio),
d.map(r=>r.status==='Elegível'?null:r.preco_medio),
d.map(r=>r.n_coletas)];
Plotly.restyle('grafico',{x:[x],y:ys},[0,1,2,3,4]);
Plotly.restyle('grafico',{customdata:[d.map(r=>[r.n_coletas,r.status])]},[2]);
const cores={'Sem dados':'#e7e9ed','Amostra reduzida':'#d79c32','Divergência':'#b34e4e','Elegível':'#2d8c64'};
Plotly.restyle('grafico',{'marker.color':[d.map(r=>cores[r.status])]},[4]);
Plotly.relayout('grafico',{'title.text':e.target.value+' · GLP P13 · semanas de 06/07 a 27/12/2025'});
});</script>""".replace("PAYLOAD",payload)
    salvar_html(mercado(weekly),"Mercado de GLP P13 no Rio Grande do Sul",
                "Dados históricos de 2025. A faixa mostra os menores e maiores preços coletados. Lacunas indicam ausência de coleta. Valores por botijão de 13 kg.",
                folder/"01_mercado.html",extra,script)
    salvar_html(qualidade(weekly),"Qualidade e cobertura",
                "A grade contém 35 municípios e 25 semanas. Ausência de coleta e amostra reduzida aparecem com status próprio. O limite de cinco coletas é uma regra operacional.",
                folder/"02_qualidade.html")
    salvar_html(previsao(weekly,root),"Previsão de preço em Pelotas",
                "Exercício retrospectivo com dados disponíveis até 27/12/2025. A projeção cobre quatro semanas subsequentes. A faixa é indicativa e o teste contém apenas cinco semanas.",
                folder/"03_previsao.html")
    static_figures(weekly,root)
