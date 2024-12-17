import pandas as pd
import folium
from folium import FeatureGroup, LayerControl
from streamlit_folium import st_folium
import streamlit as st
import sqlite3

# Configuração da página
st.set_page_config(layout="wide")

# Função única para carregar dados do banco de dados SQLite
@st.cache_resource
def carregar_dados_sqlite(nome_banco):
    conn = sqlite3.connect(nome_banco)
    query = "SELECT * FROM minha_tabela"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Inicializar variáveis no session_state, se não existirem
if "base_dados_anterior" not in st.session_state:
    st.session_state.base_dados_anterior = "K-means"
if "df" not in st.session_state:
    st.session_state.df = carregar_dados_sqlite("kmeans_banco_dados.db")  # Padrão inicial

# Radio button Cluster
base_dados = st.sidebar.radio(
    "Clustering type",
    ("K-means", "Spectral")
)

# Carregar os dados apenas se o radio button for alterado
if base_dados != st.session_state.base_dados_anterior:
    banco_dados = "kmeans_banco_dados.db" if base_dados == "K-means" else "spectral_banco_dados.db"
    st.session_state.df = carregar_dados_sqlite(banco_dados)
    st.session_state.base_dados_anterior = base_dados

# Obter os dados do cache salvo no session_state
df = st.session_state.df

# === Filtros ===
# Filtros no sidebar
st.sidebar.header("Filter")

mes_range = st.sidebar.select_slider(
    "Select Month Range:",
    options=range(1, 13),  # Valores entre 1 e 12
    value=(1, 12)  # Intervalo padrão: de 1 a 12
)

# Multiselect para cluster
cluster_selecionados = st.sidebar.multiselect(
    "Clusters:",
    options=sorted(df["cluster"].dropna().unique(), reverse=True),
    default=sorted(df["cluster"].dropna().unique(), reverse=True)
)

df_filtrado = df[
    (df["month"] >= mes_range[0]) & (df["month"] <= mes_range[1]) &  # Filtro pelo intervalo de meses
    df["cluster"].isin(cluster_selecionados)  # Filtro pelos clusters selecionados
]

# Verificar se o DataFrame filtrado está vazio e plot de mapa
if df_filtrado.empty:
    st.warning("No data to display.")
else:
    # Agrupar analyte_primary_name únicos por x, y e cluster
    df_analytes = (
        df_filtrado.groupby(['x', 'y', 'cluster', 'monitoring_loc_id'])['analyte_primary_name']
        .agg(lambda x: ', '.join(pd.unique(x)))
        .reset_index()
    )

    # Definir as cores para cada cluster
    cluster_colors = {0: 'red', 1: 'blue', 2: 'green', 3: 'purple', 4: 'orange'}

    # Encontrar o ponto central entre os limites
    lat_min, lat_max = df_analytes['y'].min(), df_analytes['y'].max()
    lon_min, lon_max = df_analytes['x'].min(), df_analytes['x'].max()
    latitude_central = (lat_min + lat_max) / 2
    longitude_central = (lon_min + lon_max) / 2

    # Criar o mapa
    mapa_clusters = folium.Map(location=[latitude_central, longitude_central], zoom_start=8)

    # Adicionar os pontos diretamente ao mapa
    for _, row in df_analytes.iterrows():
        popup_text = f"Location Name: {row['monitoring_loc_id']}<br>Cluster: {row['cluster']}<br>Analitos: {row['analyte_primary_name']}"
        folium.CircleMarker(
            location=[row['y'], row['x']],
            radius=5,
            color=cluster_colors.get(row['cluster'], 'gray'),
            fill=True,
            fill_color=cluster_colors.get(row['cluster'], 'gray'),
            fill_opacity=0.7,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(mapa_clusters)

    # Mostrar o mapa no Streamlit dentro de um container ajustado
    with st.container():
        st.write("### Clusters Map")
        st_folium(mapa_clusters, width=1500, height=800)  # Define largura e altura máxima ajustável
