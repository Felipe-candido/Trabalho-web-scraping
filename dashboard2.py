import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score,
    recall_score, confusion_matrix, roc_auc_score, roc_curve
)
from sklearn.preprocessing import LabelEncoder

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Mercado Livre — Celulares Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta de cores consistente
CORES_LOJAS = px.colors.qualitative.Set2
COR_PRIMARIA = "#F5A623"
COR_SECUNDARIA = "#2C3E50"
COR_DESTAQUE = "#27AE60"
COR_PERIGO = "#E74C3C"

st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    .element-container {
        margin-bottom: 1.75rem !important;
    }
    .pergunta-box {
        background: #ffffff;
        color: #000000;
        border-left: 4px solid #4A6CF7;
        padding: 0.85rem 1rem;
        border-radius: 6px;
        margin-bottom: 1.5rem;
        font-size: 1rem;
        font-weight: 500;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
    }
    .conclusao-box {
        background: #f0fff4;
        color: #000000;
        border-left: 4px solid #27AE60;
        padding: 0.85rem 1rem;
        border-radius: 6px;
        margin-top: 1.25rem;
        margin-bottom: 1.5rem;
        font-size: 0.95rem;
    }
    .section-title {
        margin-top: 1.5rem;
        margin-bottom: 0.4rem;
    }
    .section-caption {
        margin-bottom: 1rem;
        color: #60656f;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FUNÇÕES UTILITÁRIAS
# ─────────────────────────────────────────────
def formatar_brl(valor):
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data
def carregar_dados():
    db_path = os.path.join(os.path.dirname(__file__), "celulares.db")
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM celulares", conn)
    conn.close()
    return df


@st.cache_data
def treinar_modelo(df_model):
    """Treina Random Forest para classificar se preço está acima da mediana.

    Observação: a avaliação dos produtos no dataset é muito concentrada em notas altas
    (4.6–4.9), por isso não é um preditor discriminativo forte para o preço.
    """
    mediana = df_model["preco"].median()
    df_model = df_model.copy()
    df_model["acima_mediana"] = (df_model["preco"] > mediana).astype(int)

    le_loja = LabelEncoder()
    df_model["loja_enc"] = le_loja.fit_transform(df_model["loja"].fillna("desconhecida"))

    features = ["desconto_pct", "avaliacao", "loja_enc"]
    df_model = df_model.dropna(subset=features + ["acima_mediana"])

    X = df_model[features]
    y = df_model["acima_mediana"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=100, max_depth=6, random_state=42, class_weight="balanced"
    )
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1]

    metrics = {
        "acuracia": accuracy_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "precisao": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "auc": roc_auc_score(y_test, y_proba),
        "cm": confusion_matrix(y_test, y_pred),
        "fpr": roc_curve(y_test, y_proba)[0],
        "tpr": roc_curve(y_test, y_proba)[1],
        "importancias": dict(zip(features, clf.feature_importances_)),
        "mediana": mediana,
    }
    return clf, metrics


# ─────────────────────────────────────────────
# CARREGAMENTO
# ─────────────────────────────────────────────
df_raw = carregar_dados()

# ─────────────────────────────────────────────
# SIDEBAR — FILTROS GLOBAIS
# ─────────────────────────────────────────────
st.sidebar.title(" Filtros Globais")
st.sidebar.caption("Aplicados a todas as abas do dashboard.")

todas_lojas = sorted(df_raw["loja"].dropna().unique())
lojas_sel = st.sidebar.multiselect(
    "Lojas", todas_lojas, default=todas_lojas, key="lojas_global"
)

min_p = float(df_raw["preco"].min())
max_p = float(df_raw["preco"].max())
faixa_preco = st.sidebar.slider(
    "Faixa de preço (R$)", min_p, max_p, (min_p, max_p), key="preco_global"
)

frete_opcao = st.sidebar.radio(
    "Frete grátis", ["Todos", "Apenas com frete grátis", "Sem frete grátis"],
    key="frete_global"
)

st.sidebar.markdown("---")
st.sidebar.caption("**Perguntas analíticas exploradas:**")
st.sidebar.markdown("""
1.  Quais lojas têm maiores preços médios e variabilidade?
2.  Maior desconto implica melhor avaliação?
3.  É possível prever se o celular terá preço acima da mediana?
""")

# Aplicar filtros
df = df_raw[
    (df_raw["loja"].isin(lojas_sel)) &
    (df_raw["preco"] >= faixa_preco[0]) &
    (df_raw["preco"] <= faixa_preco[1])
].copy()

if frete_opcao == "Apenas com frete grátis":
    df = df[df["frete_gratis"] == 1]
elif frete_opcao == "Sem frete grátis":
    df = df[df["frete_gratis"] == 0]

df_uniq = df.drop_duplicates(subset=["titulo"])

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.title(" Mercado Livre — Análise de Celulares")
st.caption("Dataset coletado via scraping do Mercado Livre. Trabalho Prático — Mineração de Dados, Fase 2.")

# KPIs
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(" Anúncios", f"{len(df):,}")
c2.metric(" Preço médio", formatar_brl(df_uniq["preco"].mean()))
c3.metric(" Desconto médio", f"{df_uniq['desconto_pct'].mean():.1f}%")
c4.metric(" Frete grátis", f"{df['frete_gratis'].mean()*100:.1f}%")
c5.metric(" Avaliação média", f"{df_uniq['avaliacao'].mean():.2f}")

st.markdown("---")

# ─────────────────────────────────────────────
# ABAS
# ─────────────────────────────────────────────
abas = st.tabs([
    " Visão Geral",
    " Pergunta 1 — Preços por Loja",
    " Pergunta 2 — Desconto × Avaliação",
    " Pergunta 3 — Modelo ML",
    " Melhores Oportunidades",
])


# ══════════════════════════════════════════════
# ABA 0 — VISÃO GERAL
# ══════════════════════════════════════════════
with abas[0]:
    st.subheader("Visão Geral do Dataset")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Distribuição de Preços**")
        st.caption("Histograma mostra a concentração de anúncios por faixa de preço.")
        nbins = st.slider("Número de barras", 10, 60, 30, key="hist_bins")
        fig_hist = px.histogram(
            df_uniq, x="preco", nbins=nbins,
            color_discrete_sequence=[COR_PRIMARIA],
            labels={"preco": "Preço (R$)", "count": "Qtd. anúncios"},
            title="Distribuição de Preços dos Celulares"
        )
        fig_hist.update_layout(bargap=0.05, plot_bgcolor="white")
        fig_hist.add_vline(
            x=df_uniq["preco"].median(), line_dash="dash",
            line_color=COR_SECUNDARIA,
            annotation_text=f"Mediana: {formatar_brl(df_uniq['preco'].median())}",
            annotation_position="top right"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_b:
        st.markdown("**Participação das Lojas (Top 10)**")
        st.caption("Gráfico de pizza mostra o volume de anúncios por loja.")
        top15 = df["loja"].value_counts().head(15)
        fig_pie = px.pie(
            values=top15.values, names=top15.index,
            color_discrete_sequence=CORES_LOJAS,
            title="Distribuição de Anúncios por Loja (Top 10)"
        )
        fig_pie.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("**Frete Grátis × Preço × Desconto (%)**")
    st.caption("Scatter plot relaciona preço, desconto e condição de frete.")
    df_frete = df_uniq.dropna(subset=["desconto_pct"])
    fig_frete = px.scatter(
        df_frete,
        x="preco", y="desconto_pct",
        color=df_frete["frete_gratis"].map(
            {1: "Frete Grátis", 0: "Sem Frete Grátis"}
        ),
        opacity=0.6,
        color_discrete_map={"Frete Grátis": COR_DESTAQUE, "Sem Frete Grátis": COR_PERIGO},
        labels={"preco": "Preço (R$)", "desconto_pct": "Desconto (%)", "color": "Frete"},
        title="Relação entre Preço, Desconto (%) e Frete Grátis",
        hover_data=["titulo", "loja", "avaliacao"]
    )
    fig_frete.update_layout(plot_bgcolor="white")
    st.plotly_chart(fig_frete, use_container_width=True)


# ══════════════════════════════════════════════
# ABA 1 — PERGUNTA 1
# ══════════════════════════════════════════════
with abas[1]:
    st.markdown(
        '<div class="pergunta-box"> <b>Pergunta 1:</b> Quais lojas concentram os maiores preços médios '
        'e maior variabilidade de preços no Mercado Livre?</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        min_anuncios = st.slider(
            "Qtd. mínima de anúncios por loja",
            1, 50, 5, key="min_anuncios_p1"
        )
        metrica_ord = st.radio(
            "Ordenar por", ["Preço médio", "Mediana", "Desvio padrão"],
            key="ord_p1"
        )

    contagem_lojas = df["loja"].value_counts()
    lojas_filtradas = contagem_lojas[contagem_lojas >= min_anuncios].index
    df_p1 = df[df["loja"].isin(lojas_filtradas)]

    stats_loja = df_p1.groupby("loja")["preco"].agg(
        media="mean", mediana="median", desvio="std",
        minimo="min", maximo="max", qtd="count"
    ).reset_index()

    ord_map = {"Preço médio": "media", "Mediana": "mediana", "Desvio padrão": "desvio"}
    stats_loja = stats_loja.sort_values(ord_map[metrica_ord], ascending=False).head(15)

    with col2:
        fig_box = px.box(
            df_p1[df_p1["loja"].isin(stats_loja["loja"])],
            x="loja", y="preco",
            category_orders={"loja": stats_loja["loja"].tolist()},
            color="loja",
            color_discrete_sequence=CORES_LOJAS,
            labels={"loja": "Loja", "preco": "Preço (R$)"},
            title="Distribuição de Preços por Loja (Top 15 por critério selecionado)"
        )
        fig_box.update_layout(
            xaxis_tickangle=-35,
            showlegend=False,
            plot_bgcolor="white"
        )
        st.plotly_chart(fig_box, use_container_width=True)

    # Gráfico de barras com média e desvio
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=stats_loja["loja"],
        y=stats_loja["media"],
        name="Preço médio",
        marker_color=COR_PRIMARIA,
        error_y=dict(type="data", array=stats_loja["desvio"].fillna(0), visible=True)
    ))
    fig_bar.add_trace(go.Scatter(
        x=stats_loja["loja"],
        y=stats_loja["mediana"],
        name="Mediana",
        mode="markers",
        marker=dict(color=COR_SECUNDARIA, size=8, symbol="diamond")
    ))
    fig_bar.update_layout(
        title="Preço Médio (± Desvio Padrão) e Mediana por Loja",
        xaxis_tickangle=-35,
        plot_bgcolor="white",
        yaxis_title="Preço (R$)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.dataframe(
        stats_loja.rename(columns={
            "loja": "Loja", "media": "Preço Médio (R$)", "mediana": "Mediana (R$)",
            "desvio": "Desvio Padrão", "minimo": "Mínimo (R$)",
            "maximo": "Máximo (R$)", "qtd": "Qtd. Anúncios"
        }).style.format({
            "Preço Médio (R$)": "R$ {:.2f}",
            "Mediana (R$)": "R$ {:.2f}",
            "Desvio Padrão": "{:.2f}",
            "Mínimo (R$)": "R$ {:.2f}",
            "Máximo (R$)": "R$ {:.2f}",
        }),
        use_container_width=True
    )

    top1 = stats_loja.iloc[0]
    st.markdown(
        f'<div class="conclusao-box"> <b>Conclusão parcial:</b> A loja <b>{top1["loja"]}</b> apresenta o maior '
        f'{metrica_ord.lower()} de preço (R$ {top1[ord_map[metrica_ord]]:.2f}), indicando posicionamento em segmento premium. '
        f'O desvio padrão elevado em algumas lojas revela um portfólio diversificado com grande amplitude de preços.</div>',
        unsafe_allow_html=True
    )


# ABA 2 — PERGUNTA 2
with abas[2]:
    st.markdown(
        '<div class="pergunta-box"> <b>Pergunta 2:</b> Produtos com maior percentual de desconto '
        'tendem a ter preços mais elevados ou mais acessíveis?</div>',
        unsafe_allow_html=True
    )

    df_p2 = df_uniq.dropna(subset=["desconto_pct", "preco", "preco_antigo"])
    df_p2 = df_p2[df_p2["desconto_pct"] > 0]

    col1, col2 = st.columns([1, 3])
    with col1:
        faixa_desc = st.slider(
            "Faixa de desconto (%)",
            0, 100, (0, 100), key="desc_p2"
        )
        mostrar_tendencia = st.checkbox("Exibir linha de tendência", value=True, key="trend_p2")

    df_p2 = df_p2[
        (df_p2["desconto_pct"] >= faixa_desc[0]) &
        (df_p2["desconto_pct"] <= faixa_desc[1])
    ]

    trendline = "ols" if mostrar_tendencia else None

    with col2:
        fig_scatter2 = px.scatter(
            df_p2,
            x="desconto_pct",
            y="preco_antigo",
            color="loja",
            opacity=0.6,
            trendline=trendline,
            trendline_scope="overall",
            trendline_color_override=COR_PERIGO,
            labels={"desconto_pct": "Desconto (%)", "preco_antigo": "Preço Antigo (R$)", "loja": "Loja"},
            title="Desconto (%) × Preço Antigo por Loja",
            hover_data=["titulo", "preco", "avaliacao"]
        )
        fig_scatter2.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig_scatter2, use_container_width=True)

    # Box plot por faixa de desconto
    bins_desc = [0, 10, 20, 30, 50, 100]
    labels_desc = ["1-10%", "11-20%", "21-30%", "31-50%", ">50%"]
    df_p2["faixa_desc"] = pd.cut(
        df_p2["desconto_pct"], bins=bins_desc, labels=labels_desc
    )
    df_p2_faixas = df_p2.dropna(subset=["faixa_desc"])

    fig_box2 = px.box(
        df_p2_faixas,
        x="faixa_desc",
        y="preco_antigo",
        color="faixa_desc",
        color_discrete_sequence=px.colors.sequential.Oranges[2:],
        category_orders={"faixa_desc": labels_desc},
        labels={"faixa_desc": "Faixa de Desconto", "preco_antigo": "Preço Antigo (R$)"},
        title="Distribuição de Preço Antigo por Faixa de Desconto"
    )
    fig_box2.update_layout(plot_bgcolor="white", showlegend=False)
    st.plotly_chart(fig_box2, use_container_width=True)




# ABA 3 — PERGUNTA 3 — ML
with abas[3]:
    st.markdown(
        '<div class="pergunta-box"> <b>Pergunta 3:</b> É possível prever se um celular terá preço '
        'acima da mediana com base em desconto, avaliação e loja?</div>',
        unsafe_allow_html=True
    )
    st.caption("Respondida pela técnica de ML — Classificação com Random Forest. Avaliação foi incluída na modelagem junto com desconto e loja.")

    with st.expander(" Sobre o modelo — Random Forest", expanded=False):
        st.markdown("""
        **Algoritmo:** Random Forest Classifier (scikit-learn)

        **Lógica de aprendizado:** O Random Forest constrói múltiplas árvores de decisão em subconjuntos
        aleatórios dos dados (bagging) e combina suas previsões por votação majoritária. Isso reduz
        overfitting e aumenta a generalização em relação a uma única árvore.

        **Variável alvo:** `acima_mediana` — binária (1 = preço > mediana do dataset; 0 = caso contrário).

        **Features utilizadas:**
        - `desconto_pct` — percentual de desconto aplicado
        - `avaliacao` — nota média do produto
        - `loja_enc` — loja codificada com LabelEncoder

        **Parâmetros configurados:**
        - `n_estimators=100` — 100 árvores; equilíbrio entre desempenho e custo computacional
        - `max_depth=6` — limita profundidade para evitar overfitting
        - `class_weight='balanced'` — compensa possível desbalanceamento de classes
        - `test_size=0.2` — 80% treino / 20% teste, com estratificação

        **Justificativa da escolha:** O Random Forest é robusto a outliers, lida bem com features mistas
        (numéricas e categóricas codificadas) e fornece importância de features, o que auxilia na
        interpretação dos resultados.
        """)

    clf, metrics = treinar_modelo(df_raw)

    # Métricas principais
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Acurácia", f"{metrics['acuracia']:.1%}")
    m2.metric("F1-Score", f"{metrics['f1']:.1%}")
    m3.metric("Precisão", f"{metrics['precisao']:.1%}")
    m4.metric("Recall", f"{metrics['recall']:.1%}")
    m5.metric("AUC-ROC", f"{metrics['auc']:.3f}")

    col_cm, col_roc = st.columns(2)

    with col_cm:
        cm = metrics["cm"]
        fig_cm = px.imshow(
            cm,
            text_auto=True,
            color_continuous_scale="Blues",
            labels=dict(x="Previsto", y="Real", color="Contagem"),
            x=["Abaixo mediana", "Acima mediana"],
            y=["Abaixo mediana", "Acima mediana"],
            title="Matriz de Confusão"
        )
        fig_cm.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_cm, use_container_width=True)

    with col_roc:
        fig_roc = go.Figure()
        fig_roc.add_trace(go.Scatter(
            x=metrics["fpr"], y=metrics["tpr"],
            mode="lines",
            name=f"AUC = {metrics['auc']:.3f}",
            line=dict(color=COR_PRIMARIA, width=2.5)
        ))
        fig_roc.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode="lines",
            name="Classificador aleatório",
            line=dict(color="gray", dash="dash")
        ))
        fig_roc.update_layout(
            title="Curva ROC",
            xaxis_title="Taxa de Falsos Positivos",
            yaxis_title="Taxa de Verdadeiros Positivos",
            plot_bgcolor="white",
            legend=dict(x=0.6, y=0.1)
        )
        st.plotly_chart(fig_roc, use_container_width=True)

    # Importância das features
    imp = pd.DataFrame(
        metrics["importancias"].items(), columns=["Feature", "Importância"]
    ).sort_values("Importância", ascending=True)
    imp["Feature"] = imp["Feature"].map({
        "desconto_pct": "Desconto (%)",
        "avaliacao": "Avaliação",
        "loja_enc": "Loja"
    })

    fig_imp = px.bar(
        imp, x="Importância", y="Feature",
        orientation="h",
        color="Importância",
        color_continuous_scale="Oranges",
        title="Importância das Features no Modelo",
        labels={"Feature": "", "Importância": "Importância relativa"}
    )
    fig_imp.update_layout(plot_bgcolor="white", coloraxis_showscale=False)
    st.plotly_chart(fig_imp, use_container_width=True)

    acuracia = metrics["acuracia"]
    auc = metrics["auc"]
    satisfatorio = "satisfatório" if acuracia >= 0.70 else "moderado"
    st.markdown(
        f'<div class="conclusao-box"><b>Conclusão:</b> O modelo Random Forest atingiu acurácia de '
        f'<b>{acuracia:.1%}</b> e AUC de <b>{auc:.3f}</b>, desempenho considerado <b>{satisfatorio}</b>. '
        f'O modelo usa principalmente <b>desconto</b>, <b>avaliação</b> e <b>loja</b>. '
        f'Essas features são mais informativas do que frete grátis para prever a faixa de preço.</div>',
        unsafe_allow_html=True
    )



# ABA 4 — MELHORES OPORTUNIDADES
with abas[4]:
    st.subheader("Melhores Oportunidades")
    st.caption("Ranking dos anúncios com melhor relação entre desconto, avaliação e preço (score calculado).")

    col1, col2 = st.columns([1, 3])
    with col1:
        n_top = st.slider("Quantos produtos exibir", 5, 50, 10, key="n_top")
        avaliacao_min = st.slider(
            "Avaliação mínima", 0.0, 5.0, 3.0, 0.1, key="aval_min"
        )
        desconto_min = st.slider(
            "Desconto mínimo (%)", 0, 80, 0, key="desc_min"
        )

    df_op = df_uniq.copy()
    df_op = df_op[
        (df_op["avaliacao"] >= avaliacao_min) &
        (df_op["desconto_pct"] >= desconto_min)
    ]
    df_op = df_op.sort_values("score", ascending=False).head(n_top)

    with col2:
        fig_op = px.scatter(
            df_op,
            x="preco",
            y="desconto_pct",
            size="score",
            color="loja",
            hover_data=["titulo", "avaliacao"],
            labels={
                "preco": "Preço (R$)", "desconto_pct": "Desconto (%)",
                "score": "Score", "loja": "Loja"
            },
            title=f"Top {n_top} Oportunidades — Preço Final × Desconto (%)",
            color_discrete_sequence=CORES_LOJAS,
            size_max=20
        )
        fig_op.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig_op, use_container_width=True)

    df_show = df_op.copy()
    df_show["preco_fmt"] = df_show["preco"].apply(formatar_brl)
    df_show["preco_antigo_fmt"] = df_show["preco_antigo"].apply(formatar_brl)

    st.dataframe(
        df_show[[
            "titulo", "loja", "preco_fmt", "preco_antigo_fmt",
            "desconto_pct", "avaliacao", "score"
        ]].rename(columns={
            "titulo": "Produto", "loja": "Loja",
            "preco_fmt": "Preço", "preco_antigo_fmt": "Preço Antigo",
            "desconto_pct": "Desconto (%)", "avaliacao": "Avaliação", "score": "Score"
        }),
        use_container_width=True
    )

