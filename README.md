# BI e Analytics do GLP P13 no Rio Grande do Sul

Leonardo Bilhalva Silva — Projeto em Business Intelligence e Analytics, PUCRS.

O estudo considera uma rede fictícia de revendas de gás e usa preços públicos da ANP de 06/07 a 27/12/2025. A solução reúne indicadores de mercado, qualidade dos dados e previsão para Pelotas.

## Dashboards

[Abrir no Google Colab](https://colab.research.google.com/github/LeoBilhalva/bi-glp-rs/blob/main/GLP_BI_Analytics.ipynb)

O notebook contém gráficos e tabelas com resultados salvos. Para usar os filtros, execute todas as células. A coleta exige internet. Os arquivos por revenda e o banco são gerados no ambiente de execução, com códigos internos de revenda no recorte analítico.

## Execução local

Ambiente verificado: Python 3.12.

```bash
python -m venv .venv
```

No Windows, ative com `.venv\Scripts\activate`. No Linux ou macOS, use `source .venv/bin/activate`.

```bash
python -m pip install -r requirements.txt
python coletar_fontes.py
python run.py
python -m unittest discover -s . -p "tests_*.py"
```

Após a execução, abra `dashboards/01_mercado.html`, `02_qualidade.html` ou `03_previsao.html`. Mantenha `plotly.min.js` na mesma pasta.

## Arquivos do projeto

| Arquivo ou pasta | Conteúdo |
|---|---|
| coletar_fontes.py | Download e preparação dos recortes da ANP |
| src/pipeline.py | Validação, limpeza, modelagem em SQLite e conciliação |
| src/analytics.py | Modelos, avaliação temporal e previsão |
| src/dashboards.py | Dashboards e figuras |
| data/raw | Recortes e fontes.json com URLs, datas e hashes |
| data/processed | Dados tratados, auditoria e banco SQLite |
| outputs | Métricas, previsões e gráficos |
| tests_pipeline.py | Testes de qualidade, reexecução e uso exclusivo do passado |
| DICIONARIO_DADOS.md | Campos, indicadores e regras |
| requirements.txt e requirements-lock.txt | Dependências e versões utilizadas |

## Resultados e limites

O recorte tem 3.471 coletas válidas em 35 municípios. As 367 combinações observadas de município e semana conferiram com a referência da ANP. Das 875 combinações possíveis, 343 são elegíveis, 24 têm amostra reduzida e 508 estão sem dados.

A previsão compara último preço, média de três semanas e regressão Ridge. A seleção usa dez semanas de validação e o teste final contém cinco semanas. O último preço teve o menor MAE de validação (R$ 0,539) e projetou R$ 115,13 para as quatro semanas seguintes ao recorte.

A previsão é retrospectiva. O histórico é curto e os preços do teste ficaram estáveis. O estudo não inclui custos ou vendas da rede. Atualizações nas fontes podem mudar os resultados.

## Fontes

- [ANP: medições por revenda](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis)
- [ANP: série municipal semanal](https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos)
