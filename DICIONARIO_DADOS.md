# Dicionário de dados

As tabelas e arquivos abaixo são gerados durante a execução. Os registros por revenda ficam no ambiente do Colab ou do usuário.

Os preços são de revenda do GLP em botijão de 13 kg. A granularidade de uma coleta é revenda, data e produto. A média semanal municipal é uma média simples das coletas válidas.

| Arquivo ou tabela | Chave | Campos principais |
|---|---|---|
| data/raw/coletas_rs.csv | linha_origem | Município, data, preço, produto, unidade e identificador interno de revenda. linha_origem enumera o recorte local. |
| data/raw/referencia_rs.csv | municipio e semana | n_oficial, media_oficial, min_oficial, max_oficial |
| dim_municipio | municipio_id | municipio |
| dim_revenda | revenda_id | id_origem gerado internamente e municipio_id |
| dim_data | data_id | data e semana iniciada no domingo |
| fato_preco | revenda_id, data_id e produto | preco_centavos, municipio_id e linha_origem |
| indicador_semanal | municipio e semana | n_coletas, preco_medio, amplitude, variacao_pct, n_oficial, media_oficial, conciliado e status |
| rejeicoes | linha_origem e motivo | Identificação da coleta descartada ou separada para revisão |
| outputs/backtest.csv | fase, semana e modelo | real, previsto e treino_ate |
| outputs/previsoes.csv | semana | previsto pelo modelo selecionado, ridge_previsto, faixa_inferior, faixa_superior e fim_semana |

## Indicadores

- **Preço médio** — soma em centavos dividida pela contagem, convertida para reais e arredondada com metade para cima a duas casas.
- **Amplitude** — diferença entre maior e menor preço observado na semana.
- **Variação semanal** — (média atual / média anterior − 1) × 100, para semanas consecutivas elegíveis do mesmo município.
- **Quantidade de coletas** — número de medições válidas após tratar duplicatas e conflitos.
- **Conciliação** — presença nas duas bases, mesma contagem e diferença absoluta da média de até R$ 0,01.
- **MAE** — média do valor absoluto de real menos previsto, em reais por botijão.
- **RMSE** — raiz da média dos erros ao quadrado, na mesma unidade do preço.

## Status e ausência

A grade contém 35 × 25 = 875 combinações. Preço ausente permanece nulo.

| Status | Regra |
|---|---|
| Sem dados | Nenhuma coleta |
| Amostra reduzida | Uma a quatro coletas |
| Divergência | Cinco ou mais coletas e falha na conciliação |
| Elegível | Cinco ou mais coletas e conciliação aprovada |

Cinco coletas é uma escolha operacional do projeto. A conciliação verifica a reprodução de duas publicações da mesma pesquisa. O número de cidades observadas não representa a cobertura de todas as revendas do estado.
