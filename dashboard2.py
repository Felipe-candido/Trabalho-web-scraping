import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="Mercado Livre Analytics", layout="wide")


# FUNÇÃO FORMATAÇÃO BRL
def formatar_brl(valor):
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# LOAD
db_path = os.path.join(os.path.dirname(__file__), "celulares.db")
conn = sqlite3.connect(db_path)
df = pd.read_sql("SELECT * FROM celulares", conn)

# SIDEBAR
st.sidebar.title("Filtros")

lojas = st.sidebar.multiselect(
    "Lojas",
    df["loja"].unique(),
    default=df["loja"].unique()
)

# FILTRO DE PREÇOS
min_preco, max_preco = st.sidebar.slider(
    "Faixa de preço",
    float(df["preco"].min()),
    float(df["preco"].max()),
    (float(df["preco"].min()), float(df["preco"].max()))
)

df = df[
    (df["loja"].isin(lojas)) &
    (df["preco"] >= min_preco) &
    (df["preco"] <= max_preco)
]

# KPI (SEM DUPLICATAS)
df_kpi = df.drop_duplicates(subset=["titulo"])

st.title("Análise de Mercado - Celulares")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Anúncios", len(df))
c2.metric("Preço médio", formatar_brl(df_kpi["preco"].mean()))
c3.metric("Desconto médio", f"{df_kpi['desconto_pct'].mean():.1f}%")
c4.metric("Frete grátis", f"{df['frete_gratis'].mean()*100:.1f}%")


# GRÁFICO 1
st.subheader("Distribuição de preços")
fig1 = px.histogram(df, x="preco", nbins=30)
st.plotly_chart(fig1, use_container_width=True)


# GRÁFICO 2 (TOP LOJAS)
top_lojas = df["loja"].value_counts().head(10).index
df_lojas = df[df["loja"].isin(top_lojas)]

st.subheader("Preço por loja (Top 10)")
fig2 = px.box(df_lojas, x="loja", y="preco")
st.plotly_chart(fig2, use_container_width=True)

# =========================
# GRÁFICO 3
st.subheader("Desconto vs Preço")
fig3 = px.scatter(
    df,
    x="preco",
    y="desconto_pct",
    color="loja",
    hover_data=["titulo"]
)
st.plotly_chart(fig3, use_container_width=True)


# GRÁFICO 4
st.subheader("Avaliação vs Preço")
fig4 = px.scatter(
    df,
    x="preco",
    y="avaliacao",
    color="desconto_pct",
    color_continuous_scale="RdYlBu"
)
st.plotly_chart(fig4, use_container_width=True)

# MELHORES OPORTUNIDADES
st.subheader("Melhores oportunidades")

top = (
    df.sort_values("score", ascending=False)
    .drop_duplicates(subset=["titulo"])
    .head(10)
).copy()

top["preco"] = top["preco"].apply(formatar_brl)
top["preco_antigo"] = top["preco_antigo"].apply(formatar_brl)

st.dataframe(top[[
    "titulo", "loja", "preco", "preco_antigo",
    "desconto_pct", "avaliacao"
]])

# =========================
# DATASET COMPLETO
# =========================
st.subheader("Dataset completo")

df_view = df.copy()
df_view["preco"] = df_view["preco"].apply(formatar_brl)
df_view["preco_antigo"] = df_view["preco_antigo"].apply(formatar_brl)

st.dataframe(df_view, use_container_width=True)