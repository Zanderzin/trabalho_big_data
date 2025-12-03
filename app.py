import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Vendas de Videogames",
    page_icon="🎮",
    layout="wide"
)

# Título principal
st.title("🎮 Dashboard Interativo de Vendas de Videogames")
st.markdown("---")

# Carregar dados
@st.cache_data
def load_data():
    df = pd.read_csv("VideoGames_Vendas.csv")
    # Converter Year para numérico se necessário
    if 'Year' in df.columns:
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
    return df


try:
    df = load_data()
    
    df = df.rename(columns={
    'title': 'Name',
    'console': 'Platform',
    'genre': 'Genre',
    'publisher': 'Publisher',
    'developer': 'Developer',
    'critic_score': 'Critic_Score',
    'total_sales(mil)': 'Global_Sales',
    'na_sales(mil)': 'NA_Sales',
    'pal_sales(mil)': 'EU_Sales',
    'jp_sales(mil)': 'JP_Sales',
    'other_sales(mil)': 'Other_Sales',
    'release_date': 'Year'
    })

    # Converter release_date para ano
    df['Year'] = pd.to_datetime(df['Year'], errors='coerce').dt.year


    # Sidebar para filtros
    st.sidebar.header("🔍 Filtros")
    
    # Filtro de ano
    if 'Year' in df.columns:
        years = sorted([y for y in df['Year'].dropna().unique() if y > 1980])
        year_range = st.sidebar.slider(
            "Selecione o período",
            min_value=int(min(years)),
            max_value=int(max(years)),
            value=(int(min(years)), int(max(years)))
        )
        df_filtered = df[(df['Year'] >= year_range[0]) & (df['Year'] <= year_range[1])]
    else:
        df_filtered = df
    
    # Filtro de plataforma
    if 'Platform' in df.columns:
        platforms = ['Todas'] + sorted(df['Platform'].dropna().unique().tolist())
        selected_platform = st.sidebar.selectbox("Selecione a Plataforma", platforms)
        if selected_platform != 'Todas':
            df_filtered = df_filtered[df_filtered['Platform'] == selected_platform]
    
    # Filtro de gênero
    if 'Genre' in df.columns:
        genres = ['Todos'] + sorted(df['Genre'].dropna().unique().tolist())
        selected_genre = st.sidebar.selectbox("Selecione o Gênero", genres)
        if selected_genre != 'Todos':
            df_filtered = df_filtered[df_filtered['Genre'] == selected_genre]
    
    # KPIs principais
    st.header("📊 Indicadores Principais")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_games = len(df_filtered)
        st.metric("Total de Jogos", f"{total_games:,}")
    
    with col2:
        if 'Global_Sales' in df.columns:
            total_sales = df_filtered['Global_Sales'].sum()
            st.metric("Vendas Globais", f"{total_sales:.2f}M")
    
    with col3:
        if 'Platform' in df.columns:
            platforms_count = df_filtered['Platform'].nunique()
            st.metric("Plataformas", platforms_count)
    
    with col4:
        if 'Genre' in df.columns:
            genres_count = df_filtered['Genre'].nunique()
            st.metric("Gêneros", genres_count)
    
    st.markdown("---")
    
    # Seção de gráficos
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Vendas por Região", "🎯 Categorias", "📅 Série Temporal", "🏆 Rankings"])
    
    # Tab 1: Vendas por Região
    with tab1:
        st.subheader("Distribuição de Vendas por Região")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Vendas por região
            regions = ['NA_Sales', 'EU_Sales', 'JP_Sales', 'Other_Sales']
            region_sales = []
            region_names = ['América do Norte', 'Europa', 'Japão', 'Outros']
            
            for region in regions:
                if region in df_filtered.columns:
                    region_sales.append(df_filtered[region].sum())
                else:
                    region_sales.append(0)
            
            fig_regions = px.pie(
                values=region_sales,
                names=region_names,
                title="Participação de Vendas por Região",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_regions.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_regions, use_container_width=True)
        
        with col2:
            # Gráfico de barras comparativo
            fig_bars = go.Figure(data=[
                go.Bar(name='Vendas (Milhões)', x=region_names, y=region_sales,
                       marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'])
            ])
            fig_bars.update_layout(
                title="Comparação de Vendas por Região",
                xaxis_title="Região",
                yaxis_title="Vendas (Milhões)",
                showlegend=False
            )
            st.plotly_chart(fig_bars, use_container_width=True)
    
    # Tab 2: Categorias
    with tab2:
        st.subheader("Análise por Categorias")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Top gêneros
            if 'Genre' in df_filtered.columns and 'Global_Sales' in df_filtered.columns:
                genre_sales = df_filtered.groupby('Genre')['Global_Sales'].sum().sort_values(ascending=False).head(10)
                fig_genre = px.bar(
                    x=genre_sales.values,
                    y=genre_sales.index,
                    orientation='h',
                    title="Top 10 Gêneros por Vendas",
                    labels={'x': 'Vendas (Milhões)', 'y': 'Gênero'},
                    color=genre_sales.values,
                    color_continuous_scale='Viridis'
                )
                fig_genre.update_layout(showlegend=False)
                st.plotly_chart(fig_genre, use_container_width=True)
        
        with col2:
            # Top plataformas
            if 'Platform' in df_filtered.columns and 'Global_Sales' in df_filtered.columns:
                platform_sales = df_filtered.groupby('Platform')['Global_Sales'].sum().sort_values(ascending=False).head(10)
                fig_platform = px.bar(
                    x=platform_sales.values,
                    y=platform_sales.index,
                    orientation='h',
                    title="Top 10 Plataformas por Vendas",
                    labels={'x': 'Vendas (Milhões)', 'y': 'Plataforma'},
                    color=platform_sales.values,
                    color_continuous_scale='Plasma'
                )
                fig_platform.update_layout(showlegend=False)
                st.plotly_chart(fig_platform, use_container_width=True)
        
        # Treemap de publishers
        if 'Publisher' in df_filtered.columns and 'Global_Sales' in df_filtered.columns:
            st.subheader("Mapa de Calor: Publishers")
            publisher_sales = df_filtered.groupby('Publisher')['Global_Sales'].sum().sort_values(ascending=False).head(15)
            fig_treemap = px.treemap(
                names=publisher_sales.index,
                parents=[''] * len(publisher_sales),
                values=publisher_sales.values,
                title="Top 15 Publishers por Vendas",
                color=publisher_sales.values,
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig_treemap, use_container_width=True)
    
    # Tab 3: Série Temporal
    with tab3:
        st.subheader("Evolução Temporal das Vendas")
        
        if 'Year' in df_filtered.columns and 'Global_Sales' in df_filtered.columns:
            # Vendas ao longo do tempo
            yearly_sales = df_filtered.groupby('Year')['Global_Sales'].sum().reset_index()
            yearly_games = df_filtered.groupby('Year').size().reset_index(name='Count')
            
            fig_timeline = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Vendas Globais ao Longo do Tempo', 'Número de Jogos Lançados'),
                vertical_spacing=0.15
            )
            
            fig_timeline.add_trace(
                go.Scatter(x=yearly_sales['Year'], y=yearly_sales['Global_Sales'],
                          mode='lines+markers', name='Vendas',
                          line=dict(color='#FF6B6B', width=3),
                          fill='tonexty'),
                row=1, col=1
            )
            
            fig_timeline.add_trace(
                go.Bar(x=yearly_games['Year'], y=yearly_games['Count'],
                      name='Lançamentos', marker_color='#4ECDC4'),
                row=2, col=1
            )
            
            fig_timeline.update_xaxes(title_text="Ano", row=2, col=1)
            fig_timeline.update_yaxes(title_text="Vendas (Milhões)", row=1, col=1)
            fig_timeline.update_yaxes(title_text="Número de Jogos", row=2, col=1)
            fig_timeline.update_layout(height=700, showlegend=False)
            
            st.plotly_chart(fig_timeline, use_container_width=True)
            
            # Vendas regionais ao longo do tempo
            st.subheader("Evolução por Região")
            
            regions_time = []
            for region, name in zip(['NA_Sales', 'EU_Sales', 'JP_Sales', 'Other_Sales'],
                                   ['América do Norte', 'Europa', 'Japão', 'Outros']):
                if region in df_filtered.columns:
                    temp = df_filtered.groupby('Year')[region].sum().reset_index()
                    temp['Region'] = name
                    temp.columns = ['Year', 'Sales', 'Region']
                    regions_time.append(temp)
            
            if regions_time:
                df_regions_time = pd.concat(regions_time)
                fig_regions_time = px.line(
                    df_regions_time,
                    x='Year',
                    y='Sales',
                    color='Region',
                    title="Vendas por Região ao Longo do Tempo",
                    labels={'Sales': 'Vendas (Milhões)', 'Year': 'Ano'},
                    markers=True
                )
                fig_regions_time.update_layout(hovermode='x unified')
                st.plotly_chart(fig_regions_time, use_container_width=True)
    
    # Tab 4: Rankings
    with tab4:
        st.subheader("🏆 Rankings e Destaques")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Top 10 Jogos Mais Vendidos")
            if 'Name' in df_filtered.columns and 'Global_Sales' in df_filtered.columns:
                top_games = df_filtered.nlargest(10, 'Global_Sales')[['Name', 'Platform', 'Year', 'Genre', 'Global_Sales']]
                top_games.index = range(1, len(top_games) + 1)
                st.dataframe(top_games, use_container_width=True)
        
        with col2:
            st.markdown("### Top 10 Publishers")
            if 'Publisher' in df_filtered.columns and 'Global_Sales' in df_filtered.columns:
                top_publishers = df_filtered.groupby('Publisher').agg({
                    'Global_Sales': 'sum',
                    'Name': 'count'
                }).sort_values('Global_Sales', ascending=False).head(10)
                top_publishers.columns = ['Vendas Totais', 'Número de Jogos']
                top_publishers.index.name = 'Publisher'
                st.dataframe(top_publishers, use_container_width=True)
        
        # Análise de correlação entre gêneros e regiões
        st.subheader("Preferências Regionais por Gênero")
        if 'Genre' in df_filtered.columns:
            genre_region = df_filtered.groupby('Genre')[['NA_Sales', 'EU_Sales', 'JP_Sales', 'Other_Sales']].sum()
            genre_region.columns = ['América do Norte', 'Europa', 'Japão', 'Outros']
            
            fig_heatmap = px.imshow(
                genre_region.T,
                labels=dict(x="Gênero", y="Região", color="Vendas"),
                title="Mapa de Calor: Vendas por Gênero e Região",
                color_continuous_scale='YlOrRd',
                aspect='auto'
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Rodapé com estatísticas
    st.markdown("---")
    st.markdown("### 📊 Estatísticas do Dataset Filtrado")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"**Período analisado:** {df_filtered['Year'].min():.0f} - {df_filtered['Year'].max():.0f}")
    with col2:
        st.info(f"**Registros filtrados:** {len(df_filtered):,} de {len(df):,}")
    with col3:
        if 'Global_Sales' in df_filtered.columns:
            avg_sales = df_filtered['Global_Sales'].mean()
            st.info(f"**Média de vendas:** {avg_sales:.2f}M")

except FileNotFoundError:
    st.error("❌ Arquivo não encontrado! Verifique se o caminho está correto: /opt/ceub-bigdata/streamlit/data/VideoGames_Sales_Limpo.csv")
except Exception as e:
    st.error(f"❌ Erro ao carregar os dados: {str(e)}")
    st.info("💡 Certifique-se de que o arquivo CSV está no formato correto e contém as colunas esperadas.")