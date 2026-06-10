# Documentação do Dashboard

Este documento explica a usabilidade dos gráficos do dashboard, como cada visualização é gerada no código e como o modelo de Machine Learning foi implementado.

## 1. Visão geral do projeto

O dashboard usa Streamlit para montar a interface e Plotly para os gráficos interativos. Os dados são carregados de um banco SQLite (`celulares.db`) na função `carregar_dados()`.

### 1.1 Carregamento de dados

- `carregar_dados()` abre o arquivo SQLite em `celulares.db`.
- Executa `SELECT * FROM celulares` e retorna um `DataFrame` pandas.
- Os dados são usados em todo o dashboard para tabelas, filtros e gráficos.

### 1.2 Filtros globais

A barra lateral (`st.sidebar`) aplica filtros em todas as abas do dashboard:

- `Lojas`: seleção de lojas para incluir na análise.
- `Faixa de preço`: filtro contínuo pelo campo `preco`.
- `Frete grátis`: opção `Todos`, `Apenas com frete grátis` ou `Sem frete grátis`.

Após aplicar os filtros, o dataset filtrado é armazenado em `df` e uma versão sem anúncios duplicados (`titulo`) fica em `df_uniq`.

## 2. Cabeçalho e KPIs

No topo do dashboard são exibidos indicadores principais:

- `Anúncios`: número total de linhas após filtros.
- `Preço médio`: média da coluna `preco` em `df_uniq`.
- `Desconto médio`: média de `desconto_pct` em `df_uniq`.
- `Frete grátis`: porcentagem de anúncios com `frete_gratis == 1`.
- `Avaliação média`: média de `avaliacao` em `df_uniq`.

A função `formatar_brl()` transforma valores numéricos em strings no formato `R$ 1.234,56`.

## 3. Abas do dashboard

O dashboard tem 5 abas:

1. `Visão Geral`
2. `Pergunta 1 — Preços por Loja`
3. `Pergunta 2 — Desconto × Avaliação`
4. `Pergunta 3 — Modelo ML`
5. `Melhores Oportunidades`

Cada aba foi criada com `st.tabs()`.

## 4. Aba 0: Visão Geral

### 4.1 Gráfico `Distribuição de Preços`

- Tipo: histograma (`px.histogram`).
- Dados: `df_uniq` e coluna `preco`.
- Parâmetros:
  - `nbins`: número de barras controlado pelo usuário.
  - `color_discrete_sequence`: cor primária personalizada.
- O gráfico exibe também uma linha vertical na mediana de preço.

### 4.2 Gráfico `Participação das Lojas (Top 15)` 

- Tipo: gráfico de pizza (`px.pie`).
- Dados: contagem de anúncios por `loja` no dataset filtrado `df`.
- Mostra a participação percentual das 15 lojas mais frequentes.

### 4.3 Gráfico `Frete Grátis × Preço × Desconto (%)`

- Tipo: scatter plot (`px.scatter`).
- Eixos:
  - `x = preco`
  - `y = desconto_pct`
- Cor: condição de frete grátis com dois grupos (`Frete Grátis` e `Sem Frete Grátis`).
- Hover: mostra `titulo`, `loja` e `avaliacao`.
- Objetivo: entender se descontos maiores aparecem em produtos com ou sem frete grátis e quais faixas de preço estão envolvidas.

## 5. Aba 1: Pergunta 1 — Preços por Loja

### 5.1 Objetivo

Responder: `Quais lojas concentram os maiores preços médios e maior variabilidade de preços?`

### 5.2 Filtros

- `Qtd. mínima de anúncios por loja`: remove lojas com poucos produtos para análise mais confiável.
- `Ordenar por`: permite escolher entre `Preço médio`, `Mediana` e `Desvio padrão`.

### 5.3 Gráfico de caixa de preços por loja

- Tipo: box plot (`px.box`).
- Dados: lojas filtradas, usando coluna `preco`.
- O gráfico mostra distribuição, mediana e outliers de preço por loja.
- Ordenação segue o critério escolhido.

### 5.4 Gráfico de barras com média e desvio

- Tipo: gráfico combinado de barras (`go.Bar`) e pontos (`go.Scatter`).
- Barras mostram preço médio por loja.
- O erro de barras mostra desvio padrão.
- Marker de diamante indica a mediana.
- Isso ajuda a comparar preço médio e variabilidade.

### 5.5 Tabela de resumo

- Exibe dados por loja:
  - `Preço Médio`
  - `Mediana`
  - `Desvio Padrão`
  - `Mínimo`
  - `Máximo`
  - `Qtd. Anúncios`

### 5.6 Conclusão parcial

- Exibe a loja com melhor valor no critério atual.
- O texto é renderizado em `st.markdown` com HTML customizado na classe `conclusao-box`.

## 6. Aba 2: Pergunta 2 — Desconto × Avaliação

### 6.1 Objetivo

Responder: `Produtos com maior percentual de desconto tendem a ter preços mais elevados ou mais acessíveis?`

### 6.2 Filtros

- Faixa de desconto (%).
- Linha de tendência opcional.

### 6.3 Gráfico principal

- Tipo: scatter plot (`px.scatter`).
- Eixos:
  - `x = desconto_pct`
  - `y = preco_antigo`
- Cor: loja.
- Hover: mostra `titulo`, `preco` e `avaliacao`.
- Trendline: regressão OLS opcional.
- Finalidade: ver se descontos maiores são aplicados em produtos com preço antigo mais alto ou mais baixo.

### 6.4 Box plot por faixa de desconto

- Tipo: box plot (`px.box`).
- Agrupa produtos em intervalos de desconto: `1-10%`, `11-20%`, `21-30%`, `31-50%`, `>50%`.
- Mostra a distribuição de `preco_antigo` por faixa.

### 6.5 Correlação por loja

- Calcula a correlação entre `desconto_pct` e `preco_antigo` para cada loja.
- Exibe um `bar chart` horizontal (`px.bar`) ordenado por correlação.
- Objetivo: comparar se algumas lojas têm padrões mais fortes de desconto vs. preço antigo.

### 6.6 Conclusão parcial

- Mostra a correlação global entre desconto e preço antigo.
- Indica se a relação é positiva, negativa, fraca, moderada ou forte.

## 7. Aba 3: Pergunta 3 — Modelo ML

### 7.1 Objetivo

Responder: `É possível prever se um celular terá preço acima da mediana com base em desconto, avaliação e loja?`

### 7.2 Implementação do modelo

A função `treinar_modelo(df_model)` faz o seguinte:

1. Calcula a mediana do preço com `df_model["preco"].median()`.
2. Cria a variável alvo `acima_mediana` como `1` se `preco` for maior que a mediana e `0` caso contrário.
3. Codifica a loja com `LabelEncoder()` em `loja_enc`.
4. Seleciona features:
   - `desconto_pct`
   - `avaliacao`
   - `loja_enc`
5. Remove linhas com valores nulos nas features ou na variável alvo.
6. Divide dados em treino e teste (`train_test_split` com `test_size=0.2` e `stratify=y`).
7. Treina `RandomForestClassifier` com:
   - `n_estimators=100`
   - `max_depth=6`
   - `class_weight='balanced'`
   - `random_state=42`

### 7.3 Métricas exibidas

- Acurácia
- F1-Score
- Precisão
- Recall
- AUC-ROC

### 7.4 Gráficos do modelo

- `Matriz de confusão` (`px.imshow`): compara classes previstas vs reais.
- `Curva ROC` (`go.Figure`): visualiza tradeoff entre taxa de falsos positivos e verdadeiros positivos.
- `Importância das features` (`px.bar`): mostra quanto cada feature contribui para as decisões do modelo.

### 7.5 Observação sobre a avaliação

- O dataset original apresenta notas muito altas e pouco variáveis (`4.6` a `4.9`).
- Isso significa que `avaliacao` tem pouco poder discriminativo, mas ainda foi incluída no modelo para ver se ajuda.
- A intenção do dashboard é explicar esse comportamento: se a avaliação está sempre alta, ela não é um forte sinal de diferença de preço.

## 8. Aba 4: Melhores Oportunidades

### 8.1 Objetivo

Exibir os anúncios com maior `score` de oportunidades.

### 8.2 Filtros

- Quantos produtos exibir.
- Avaliação mínima.
- Desconto mínimo (%).

### 8.3 Gráfico principal

- Tipo: scatter plot (`px.scatter`).
- Eixos:
  - `x = preco`
  - `y = desconto_pct`
- Tamanho dos pontos: `score`.
- Cor: `loja`.
- Hover exibe `titulo` e `avaliacao`.

### 8.4 Tabela de oportunidades

- Exibe colunas:
  - `Produto`
  - `Loja`
  - `Preço`
  - `Preço Antigo`
  - `Desconto (%)`
  - `Avaliação`
  - `Score`

## 9. Como foram implementadas as perguntas

### Pergunta 1
- Análise de preços por loja usando box plot e barras com média/mediana/desvio.
- Permite responder quais lojas têm preços mais altos e mais dispersão.

### Pergunta 2
- Compara desconto com preço antigo em vez de avaliação.
- Permite entender se altos descontos estão vinculados a produtos originalmente mais caros.

### Pergunta 3
- Usa classificação em Random Forest para prever se um produto está acima da mediana de preço.
- Features: desconto, avaliação e loja.
- Avaliação mostra um sinal fraco devido à alta concentração de notas.

## 10. Observações de usabilidade

- Os filtros na barra lateral afetam todas as abas, garantindo consistência.
- Gráficos usam cores consistentes definidas em variáveis como `COR_PRIMARIA`, `COR_SECUNDARIA`, `COR_DESTAQUE` e `COR_PERIGO`.
- A interface foi ajustada com CSS customizado para melhorar espaçamento e legibilidade.
- `use_container_width=True` garante que os gráficos se ajustem à largura disponível.

## 11. Como rodar o dashboard

No terminal, dentro da pasta do projeto:

```powershell
streamlit run dashboard2.py
```

Se necessário, instale as dependências:

```powershell
pip install -r requirements.txt
```

---

Esta documentação resume a lógica dos gráficos e a implementação do modelo ML no código do dashboard.