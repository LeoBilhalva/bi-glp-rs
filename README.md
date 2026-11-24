# BI e Analytics do GLP P13 no Rio Grande do Sul

Projeto de Leonardo Bilhalva Silva para a Fase 2 de Projeto em Business Intelligence e Analytics da PUCRS.

O cliente do estudo é uma rede fictícia de revendas de gás. A solução acompanha preços de mercado e deixa visível a quantidade de coletas que sustenta cada média.

O repositório público inclui o código, o notebook com resultados agregados e figuras. A base por revenda e o banco são gerados no ambiente de quem executar o projeto.

## Consulta e execução

**[Abrir dashboards e Analytics no Google Colab](https://colab.research.google.com/github/LeoBilhalva/bi-glp-rs/blob/main/GLP_BI_Analytics.ipynb)**

[Consultar o notebook com os resultados salvos](GLP_BI_Analytics.ipynb)


Abra o arquivo **GLP_BI_Analytics.ipynb** no Google Colab e use **Ambiente de execução > Executar tudo**. O notebook contém o código e baixa as fontes oficiais da ANP durante a execução. A base por revenda fica no ambiente local ou no Colab. As saídas salvas permitem visualizar os resultados antes da execução.

Para consultar os dashboards publicados, abra o notebook no Google Colab pelo link acima. As saídas salvas também podem ser vistas no próprio GitHub.

Para usar as cópias HTML a partir de um clone do repositório, execute **python run.py** uma vez. O comando gera o banco, os resultados CSV e a biblioteca Plotly local em dashboards. Depois, abra **dashboards/01_mercado.html**. O ZIP de entrega contém as cópias offline já preparadas.

## Execução local

Use Python 3.12 ou posterior.

    python -m venv .venv
    .venv\Scripts\activate
    python -m pip install -r requirements.txt
    python coletar_fontes.py
    python run.py
    python -m unittest discover -s . -p "tests_*.py"

No Linux e macOS, ative o ambiente com **source .venv/bin/activate**.

Para refazer a coleta e a extração diretamente dos dois arquivos oficiais, execute **python coletar_fontes.py** e depois **python run.py**. Uma nova versão da fonte pode alterar os totais do estudo.

O comando **python run.py --baixar-originais** também baixa as fontes oficiais integrais para auditoria. Depois da coleta, a execução usa os recortes locais em data/raw. O download opcional preserva os arquivos originais em data/originais e mantém os recortes utilizados no estudo.

## Estrutura

- **coletar_fontes.py** — baixa os arquivos nacionais, extrai os recortes e atualiza a proveniência.
- **src/pipeline.py** — confere hashes, limpa coletas, cria o modelo dimensional e concilia os indicadores.
- **src/analytics.py** — valida três modelos em ordem temporal, calcula erros e produz quatro semanas de previsão.
- **src/dashboards.py** — cria gráficos Plotly, filtros HTML e figuras dos resultados.
- **data/raw** — recortes oficiais, proveniência e hashes.
- **data/processed** — SQLite, registros válidos, rejeições e grade semanal.
- **outputs** — erros, previsões, backtest e gráficos.
- **dashboards** — mercado, qualidade e previsão em HTML.
- **DICIONARIO_DADOS.md** — campos, métricas e regras.
- **tests_pipeline.py** — testes de limites, duplicatas, carga repetida, ausência e uso exclusivo do passado.

## Fontes e recorte

São 3.782 coletas brutas de GLP no Rio Grande do Sul no segundo semestre de 2025. O estudo usa semanas completas de 06/07 a 27/12/2025, com 3.471 coletas válidas em 35 municípios. A planilha municipal serve de referência para conferir as 367 combinações observadas de município e semana.

Os registros por revenda são obtidos diretamente da ANP durante a execução e ficam no ambiente do Colab ou do usuário. A preparação local usa códigos internos de revenda e retira os campos cadastrais do recorte analítico. O repositório publica o código e os resultados agregados do estudo. URLs, datas de obtenção e hashes constam em **data/raw/fontes.json**. Na execução original, o CSV foi obtido em 23/11/2026 e a planilha em 13/11/2026. A nova coleta registra sua própria data. Os arquivos de origem têm datas de coleta de 2025.

## Resultados de BI

As 367 combinações observadas conferiram com a referência, dentro da tolerância de R$ 0,01 e com igualdade das contagens. Na grade de 875 combinações, há 343 elegíveis, 24 com amostra reduzida e 508 sem dados.

Em Pelotas, o preço médio passou de R$ 111,39 para R$ 115,13, aumento de 3,36%. Na última semana, 27 municípios tiveram amostra elegível. As médias extremas entre eles foram São Leopoldo, com R$ 104,41, e Erechim, com R$ 132,88. A diferença de R$ 28,47 ajuda a priorizar a pesquisa comercial, considerando que o estudo não inclui custos, volume vendido e frete.

## Analytics

A série de Pelotas tem 25 semanas completas e foi usada sem preencher valores ausentes. Foram comparados último preço, média das três últimas semanas e regressão Ridge com os três preços anteriores como variáveis. O Ridge usa alpha igual a 1 e é treinado novamente em cada origem de previsão.

As dez primeiras semanas formam o histórico inicial. As dez seguintes servem de validação e as cinco finais de teste. A escolha usa apenas o MAE da validação. Cada previsão de um passo usa exclusivamente o passado e incorpora os novos preços depois que a semana é observada.

O último preço teve MAE de validação de R$ 0,539 e de teste de R$ 0,026. Ridge teve, respectivamente, R$ 0,699 e R$ 0,069. O teste cobre apenas cinco semanas estáveis.

A projeção final de quatro semanas mantém R$ 115,13 pelo modelo selecionado. O arquivo **outputs/previsoes.csv** também contém a projeção do Ridge. São previsões retrospectivas feitas com informação até dezembro de 2025. Os quatro passos finais são recursivos. A faixa indicativa usa o percentil 90 do erro de validação multiplicado pela raiz do horizonte e precisa ser interpretada como uma referência de erro.

## Verificações e limites

Foram executados seis testes, incluindo reexecução da carga e ausência de vazamento temporal. As hipóteses H1 e H2 da Fase 1 foram atendidas nos critérios operacionais definidos.

O limite de cinco coletas é uma regra de exibição. Conferir duas publicações da ANP avalia a transformação dos dados. O projeto não mede precisão do levantamento em campo, lucro da rede, demanda ou efeito causal de mudanças de preço.

A escolha de Google Colab usa uma plataforma permitida no enunciado. Python e SQLite continuam no tratamento e no armazenamento. O notebook publicado no Colab substitui a visualização inicialmente planejada em Power BI.
