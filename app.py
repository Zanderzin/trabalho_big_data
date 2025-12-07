import streamlit as st
import s3fs
import pyarrow.parquet as pq
import pyarrow as pa
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="TLC FHV - EDA", layout="wide", initial_sidebar_state="expanded")

# -----------------------------------------
# 1. Conectar ao MinIO
# -----------------------------------------
@st.cache_resource
def get_fs():
    try:
        endpoint = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
        access_key = os.getenv("MINIO_ROOT_USER", "minioadmin")
        secret_key = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
        
        fs = s3fs.S3FileSystem(
            key=access_key,
            secret=secret_key,
            client_kwargs={"endpoint_url": endpoint, "verify": False},
            use_ssl=False
        )
        fs.ls("")
        return fs
    except Exception as e:
        st.error(f"❌ Erro ao conectar ao MinIO: {str(e)}")
        st.stop()

fs = get_fs()

# Configuração do bucket
bucket_name = "trabalho"
folder_path = "limpo/for_hire_2023"
bucket_path = f"{bucket_name}/{folder_path}"

# -----------------------------------------
# SIDEBAR - Navegação e Configurações
# -----------------------------------------
with st.sidebar:
    st.title("🚕 TLC FHV 2023")
    st.markdown("**For-Hire Vehicle Trip Records**")
    st.divider()
    
    # Navegação
    pagina = st.radio(
        "📊 Navegação",
        ["🏠 Carregar Dados", "📈 Visão Geral", "🗓️ Análise Temporal", 
         "🚗 Análise de Bases", "🔍 Dados Detalhados"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Info da base
    with st.expander("ℹ️ Sobre os Dados"):
        st.markdown("""
        **FHV Trip Records 2023**
        
        Viagens de veículos de aluguel (Uber, Lyft, etc) em NYC.
        
        **Colunas:**
        - `dispatching_base_num`: Base que despachou
        - `pickup_datetime`: Data/hora do pickup
        - `dropoff_datetime`: Data/hora do dropoff
        - `PULocationID`: Zona de pickup
        - `DOLocationID`: Zona de dropoff
        - `SR_Flag`: Viagem compartilhada (1) ou não (null)
        - `affiliated_base_number`: Base afiliada
        """)
    
    # Status dos dados
    if 'arrow_table' in st.session_state or 'df' in st.session_state:
        st.success("✅ Dados carregados")
        if 'arrow_table' in st.session_state:
            total_rows = len(st.session_state['arrow_table'])
        else:
            total_rows = len(st.session_state['df'])
        st.metric("Total de viagens", f"{total_rows:,}")
    else:
        st.warning("⚠️ Carregue os dados primeiro")

# -----------------------------------------
# PÁGINA: CARREGAR DADOS
# -----------------------------------------
if pagina == "🏠 Carregar Dados":
    st.title("📦 Carregar Dados do MinIO")
    
    # Listar arquivos
    def listar_parquets():
        try:
            all_files = fs.ls(bucket_path, detail=False)
            return [f for f in all_files if f.endswith(".parquet")]
        except Exception as e:
            st.error(f"❌ Erro ao listar arquivos: {str(e)}")
            return []
    
    parquets = listar_parquets()
    
    if not parquets:
        st.error(f"Nenhum arquivo encontrado em: `{bucket_path}`")
        st.stop()
    
    st.success(f"✅ Encontrados **{len(parquets)}** arquivos Parquet")
    
    with st.expander("Ver arquivos disponíveis"):
        for p in parquets:
            st.text(f"• {p.split('/')[-1]}")
    
    st.divider()
    
    # Opções de carregamento
    st.subheader("⚙️ Configurações de Carregamento")
    
    col1, col2 = st.columns(2)
    with col1:
        skip_errors = st.checkbox("⏭️ Pular arquivos com erro", value=True)
        use_arrow = st.checkbox("⚡ Usar PyArrow (recomendado)", value=True,
                               help="Muito mais rápido e eficiente em memória!")
    with col2:
        show_details = st.checkbox("📝 Mostrar detalhes do carregamento", value=False)
        unify_schemas = st.checkbox("🔧 Unificar schemas diferentes", value=True)
    
    # Seleção de quantidade
    st.markdown("**Quantos arquivos carregar?**")
    col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns(5)
    
    num_arquivos = 0
    with col_a1:
        if st.button("3 arquivos", use_container_width=True):
            num_arquivos = 3
    with col_a2:
        if st.button("6 arquivos (metade)", use_container_width=True):
            num_arquivos = len(parquets) // 2
    with col_a3:
        if st.button("9 arquivos", use_container_width=True):
            num_arquivos = 9
    with col_a4:
        if st.button("Todos (12)", use_container_width=True):
            num_arquivos = 0
    with col_a5:
        num_arquivos_manual = st.number_input("Outro", 0, len(parquets), 0, label_visibility="collapsed")
        if num_arquivos_manual > 0:
            num_arquivos = num_arquivos_manual
    
    arquivos_para_carregar = parquets if num_arquivos == 0 else parquets[:num_arquivos]
    
    st.info(f"📦 **{len(arquivos_para_carregar)} arquivos** serão carregados ({len(arquivos_para_carregar)/len(parquets)*100:.0f}% do total)")
    
    st.divider()
    
    # Botão de carregar
    if st.button("🚀 CARREGAR DADOS", type="primary", use_container_width=True):
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
            tables = []
            arquivos_ok = []
            arquivos_com_erro = []
            
            # Carrega cada arquivo
            for i, parquet_path in enumerate(arquivos_para_carregar):
                filename = parquet_path.split('/')[-1]
                status_text.text(f"Carregando {i+1}/{len(arquivos_para_carregar)}: {filename}")
                progress_bar.progress((i + 1) / len(arquivos_para_carregar))
                
                try:
                    with fs.open(parquet_path, "rb") as f:
                        file_info = fs.info(parquet_path)
                        file_size_mb = file_info['size'] / (1024 * 1024)
                        
                        first_bytes = f.read(4)
                        if first_bytes != b'PAR1':
                            raise ValueError(f"Arquivo não é Parquet válido")
                        f.seek(0)
                        
                        table = pq.read_table(f)
                        tables.append(table)
                        
                        arquivos_ok.append({
                            'arquivo': filename,
                            'linhas': len(table),
                            'tamanho_mb': f"{file_size_mb:.2f}"
                        })
                        
                        if show_details:
                            st.write(f"✅ {filename} - {len(table):,} linhas")
                            
                except Exception as e:
                    arquivos_com_erro.append({'arquivo': filename, 'erro': str(e)[:100]})
                    if show_details:
                        st.warning(f"⚠️ Erro em {filename}")
                    if not skip_errors:
                        raise
            
            if not tables:
                st.error("❌ Nenhum arquivo carregado!")
                st.stop()
            
            # Concatena
            status_text.text("Concatenando tabelas...")
            if unify_schemas:
                full_table = pa.concat_tables(tables, promote=True)
            else:
                full_table = pa.concat_tables(tables)
            
            progress_bar.progress(100)
            status_text.empty()
            
            # Salva no session state
            st.session_state['arrow_table'] = full_table
            st.session_state['arquivos_carregados'] = arquivos_ok
            st.session_state['arquivos_erro'] = arquivos_com_erro
            st.session_state['data_carregamento'] = datetime.now()
            
            st.success(f"✅ **{len(full_table):,} viagens** carregadas com sucesso!")
            
            # Estatísticas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Viagens", f"{len(full_table):,}")
            with col2:
                st.metric("Arquivos", f"{len(arquivos_ok)}/{len(arquivos_para_carregar)}")
            with col3:
                st.metric("Colunas", len(full_table.schema))
            with col4:
                st.metric("Memória", f"{full_table.nbytes / 1024**2:.0f} MB")
            
            if arquivos_com_erro:
                with st.expander(f"⚠️ {len(arquivos_com_erro)} arquivo(s) com erro"):
                    st.dataframe(pd.DataFrame(arquivos_com_erro))
            
            st.info("👈 Use o menu lateral para explorar os dados!")
            
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")
            import traceback
            with st.expander("Stack trace"):
                st.code(traceback.format_exc())

# -----------------------------------------
# FUNÇÕES AUXILIARES PARA EDA
# -----------------------------------------
@st.cache_data
def get_dataframe(_arrow_table, sample_size=None):
    """Converte Arrow para Pandas, com opção de amostragem"""
    if sample_size and len(_arrow_table) > sample_size:
        # Amostra aleatória
        indices = np.random.choice(len(_arrow_table), sample_size, replace=False)
        indices = sorted(indices)
        sampled = _arrow_table.take(indices)
        return sampled.to_pandas()
    return _arrow_table.to_pandas()

@st.cache_data
def processar_datas(_df):
    """Processa e extrai features temporais"""
    df = _df.copy()
    df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])
    df['dropoff_datetime'] = pd.to_datetime(df['dropoff_datetime'])
    df['trip_duration_min'] = (df['dropoff_datetime'] - df['pickup_datetime']).dt.total_seconds() / 60
    df['pickup_hour'] = df['pickup_datetime'].dt.hour
    df['pickup_day'] = df['pickup_datetime'].dt.day
    df['pickup_month'] = df['pickup_datetime'].dt.month
    df['pickup_dayofweek'] = df['pickup_datetime'].dt.dayofweek
    df['pickup_date'] = df['pickup_datetime'].dt.date
    return df

# -----------------------------------------
# PÁGINA: VISÃO GERAL
# -----------------------------------------
if pagina == "📈 Visão Geral":
    st.title("📈 Visão Geral dos Dados")
    
    if 'arrow_table' not in st.session_state:
        st.warning("⚠️ Carregue os dados primeiro na página inicial")
        st.stop()
    
    table = st.session_state['arrow_table']
    
    # KPIs principais
    st.subheader("📊 Principais Métricas")
    
    # Processa amostra para cálculos rápidos
    with st.spinner("Processando dados..."):
        df_sample = get_dataframe(table, sample_size=100000)
        df_sample = processar_datas(df_sample)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Viagens", f"{len(table):,}")
    with col2:
        total_bases = df_sample['dispatching_base_num'].nunique()
        st.metric("Bases Ativas", f"{total_bases:,}")
    with col3:
        avg_duration = df_sample['trip_duration_min'].mean()
        st.metric("Duração Média", f"{avg_duration:.1f} min")
    with col4:
        shared_pct = (df_sample['sr_flag'].notna().sum() / len(df_sample)) * 100
        st.metric("Viagens Compartilhadas", f"{shared_pct:.1f}%")
    
    st.divider()
    
    # Gráficos principais
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("📅 Viagens por Dia")
        viagens_dia = df_sample.groupby('pickup_date').size().reset_index(name='viagens')
        fig = px.line(viagens_dia, x='pickup_date', y='viagens', 
                     title="Evolução Diária de Viagens")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        st.subheader("⏰ Viagens por Hora do Dia")
        viagens_hora = df_sample.groupby('pickup_hour').size().reset_index(name='viagens')
        fig = px.bar(viagens_hora, x='pickup_hour', y='viagens',
                    title="Distribuição por Hora")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Top bases
    st.subheader("🏆 Top 10 Bases Mais Ativas")
    top_bases = df_sample['dispatching_base_num'].value_counts().head(10).reset_index()
    top_bases.columns = ['Base', 'Viagens']
    
    fig = px.bar(top_bases, x='Base', y='Viagens', 
                title="Bases com Mais Viagens")
    st.plotly_chart(fig, use_container_width=True)
    
    # Distribuições
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.subheader("⏱️ Distribuição de Duração")
        # Filtra outliers
        duration_clean = df_sample[
            (df_sample['trip_duration_min'] > 0) & 
            (df_sample['trip_duration_min'] < 120)
        ]['trip_duration_min']
        
        fig = px.histogram(duration_clean, nbins=50,
                          title="Duração das Viagens (até 120 min)")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_d2:
        st.subheader("📆 Viagens por Dia da Semana")
        dias_semana = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        viagens_dow = df_sample.groupby('pickup_dayofweek').size().reset_index(name='viagens')
        viagens_dow['dia'] = viagens_dow['pickup_dayofweek'].map(lambda x: dias_semana[x])
        
        fig = px.bar(viagens_dow, x='dia', y='viagens',
                    title="Distribuição Semanal")
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------
# PÁGINA: ANÁLISE TEMPORAL
# -----------------------------------------
elif pagina == "🗓️ Análise Temporal":
    st.title("🗓️ Análise Temporal Detalhada")
    
    if 'arrow_table' not in st.session_state:
        st.warning("⚠️ Carregue os dados primeiro")
        st.stop()
    
    table = st.session_state['arrow_table']
    
    with st.spinner("Processando análise temporal..."):
        df_sample = get_dataframe(table, sample_size=200000)
        df_sample = processar_datas(df_sample)
    
    # Filtros de data
    st.sidebar.subheader("🔍 Filtros Temporais")
    min_date = df_sample['pickup_date'].min()
    max_date = df_sample['pickup_date'].max()
    
    date_range = st.sidebar.date_input(
        "Período",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        df_filtered = df_sample[
            (df_sample['pickup_date'] >= date_range[0]) &
            (df_sample['pickup_date'] <= date_range[1])
        ]
    else:
        df_filtered = df_sample
    
    # Série temporal completa
    st.subheader("📈 Série Temporal Completa")
    
    agregacao = st.selectbox("Agregação", ["Hora", "Dia", "Semana"])
    
    if agregacao == "Hora":
        df_filtered['periodo'] = df_filtered['pickup_datetime'].dt.floor('H')
    elif agregacao == "Dia":
        df_filtered['periodo'] = df_filtered['pickup_datetime'].dt.date
    else:
        df_filtered['periodo'] = df_filtered['pickup_datetime'].dt.to_period('W').dt.start_time
    
    serie_temporal = df_filtered.groupby('periodo').size().reset_index(name='viagens')
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=serie_temporal['periodo'],
        y=serie_temporal['viagens'],
        mode='lines',
        name='Viagens',
        line=dict(color='#1f77b4', width=2)
    ))
    
    fig.update_layout(
        title=f"Viagens por {agregacao}",
        xaxis_title="Período",
        yaxis_title="Número de Viagens",
        hovermode='x unified',
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Análise por período do dia
    st.divider()
    st.subheader("🌅 Análise por Período do Dia")
    
    def periodo_dia(hora):
        if 5 <= hora < 12:
            return "Manhã"
        elif 12 <= hora < 18:
            return "Tarde"
        elif 18 <= hora < 22:
            return "Noite"
        else:
            return "Madrugada"
    
    df_filtered['periodo_dia'] = df_filtered['pickup_hour'].apply(periodo_dia)
    
    col1, col2 = st.columns(2)
    
    with col1:
        periodo_counts = df_filtered['periodo_dia'].value_counts()
        fig = px.pie(values=periodo_counts.values, names=periodo_counts.index,
                    title="Distribuição por Período do Dia")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Heatmap hora x dia da semana
        heatmap_data = df_filtered.groupby(['pickup_dayofweek', 'pickup_hour']).size().unstack(fill_value=0)
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
            colorscale='Blues'
        ))
        
        fig.update_layout(
            title="Heatmap: Dia da Semana x Hora",
            xaxis_title="Hora do Dia",
            yaxis_title="Dia da Semana"
        )
        
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------
# PÁGINA: ANÁLISE DE BASES
# -----------------------------------------
if pagina == "🚗 Análise de Bases":
    st.title("🚗 Análise de Bases de Despacho")
    
    if 'arrow_table' not in st.session_state:
        st.warning("⚠️ Carregue os dados primeiro")
        st.stop()
    
    table = st.session_state['arrow_table']
    
    with st.spinner("Processando análise de bases..."):
        df_sample = get_dataframe(table, sample_size=200000)
        df_sample = processar_datas(df_sample)
    
    # Estatísticas gerais
    st.subheader("📊 Estatísticas Gerais")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Bases", df_sample['dispatching_base_num'].nunique())
    with col2:
        st.metric("Bases Afiliadas", df_sample['affiliated_base_number'].nunique())
    with col3:
        bases_shared = df_sample[df_sample['sr_flag'].notna()]['dispatching_base_num'].nunique()
        st.metric("Bases c/ Shared Rides", bases_shared)
    with col4:
        avg_trips_per_base = len(df_sample) / df_sample['dispatching_base_num'].nunique()
        st.metric("Média viagens/base", f"{avg_trips_per_base:.0f}")
    
    st.divider()
    
    # Top bases
    st.subheader("🏆 Ranking de Bases")
    
    n_bases = st.slider("Número de bases a mostrar", 5, 50, 20)
    
    base_stats = df_sample.groupby('dispatching_base_num').agg({
        'pickup_datetime': 'count',
        'trip_duration_min': 'mean',
        'sr_flag': lambda x: x.notna().sum()
    }).reset_index()
    
    base_stats.columns = ['Base', 'Total_Viagens', 'Duracao_Media', 'Viagens_Compartilhadas']
    base_stats['Pct_Compartilhadas'] = (base_stats['Viagens_Compartilhadas'] / base_stats['Total_Viagens']) * 100
    base_stats = base_stats.sort_values('Total_Viagens', ascending=False).head(n_bases)
    
    fig = px.bar(base_stats, x='Base', y='Total_Viagens',
                title=f"Top {n_bases} Bases por Número de Viagens",
                hover_data=['Duracao_Media', 'Pct_Compartilhadas'])
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
    
    # Comparação de métricas
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.scatter(base_stats, x='Total_Viagens', y='Duracao_Media',
                        size='Total_Viagens', hover_name='Base',
                        title="Viagens vs Duração Média")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.scatter(base_stats, x='Total_Viagens', y='Pct_Compartilhadas',
                        size='Total_Viagens', hover_name='Base',
                        title="Viagens vs % Compartilhadas")
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabela detalhada
    st.subheader("📋 Dados Detalhados")
    st.dataframe(
        base_stats.style.format({
            'Total_Viagens': '{:,.0f}',
            'Duracao_Media': '{:.1f}',
            'Pct_Compartilhadas': '{:.1f}%'
        }),
        use_container_width=True,
        height=400
    )

# -----------------------------------------
# PÁGINA: DADOS DETALHADOS
# -----------------------------------------
elif pagina == "🔍 Dados Detalhados":
    st.title("🔍 Exploração Detalhada dos Dados")
    
    if 'arrow_table' not in st.session_state:
        st.warning("⚠️ Carregue os dados primeiro")
        st.stop()
    
    table = st.session_state['arrow_table']
    
    # Opções de visualização
    st.subheader("⚙️ Opções de Visualização")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        n_rows = st.number_input("Número de linhas", 10, 100000, 1000)
    with col2:
        random_sample = st.checkbox("Amostra aleatória", value=True)
    with col3:
        processar_dates = st.checkbox("Processar datas", value=True)
    
    # Buscar dados
    if st.button("🔍 Buscar Dados", type="primary"):
        with st.spinner("Carregando dados..."):
            if random_sample:
                df = get_dataframe(table, sample_size=n_rows)
            else:
                df = table.slice(0, n_rows).to_pandas()
            
            if processar_dates:
                df = processar_datas(df)
            
            st.session_state['df_view'] = df
    
    # Mostrar dados
    if 'df_view' in st.session_state:
        df = st.session_state['df_view']
        
        # Estatísticas básicas
        st.subheader("📊 Resumo Estatístico")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Informações Gerais**")
            st.write(f"- Linhas: {len(df):,}")
            st.write(f"- Colunas: {len(df.columns)}")
            st.write(f"- Memória: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
            st.write(f"- Dados faltantes: {df.isna().sum().sum():,}")
        
        with col2:
            st.write("**Tipos de Dados**")
            tipos = df.dtypes.value_counts()
            for tipo, count in tipos.items():
                st.write(f"- {tipo}: {count} coluna(s)")
        
        # Estatísticas descritivas
        with st.expander("📈 Estatísticas Descritivas"):
            st.dataframe(df.describe(), use_container_width=True)
        
        # Dados faltantes
        with st.expander("❓ Análise de Dados Faltantes"):
            missing = df.isna().sum()
            missing = missing[missing > 0].sort_values(ascending=False)
            if len(missing) > 0:
                missing_df = pd.DataFrame({
                    'Coluna': missing.index,
                    'Faltantes': missing.values,
                    '% Faltantes': (missing.values / len(df) * 100).round(2)
                })
                st.dataframe(missing_df, use_container_width=True)
            else:
                st.success("✅ Nenhum dado faltante!")
        
        # Filtros interativos
        st.divider()
        st.subheader("🔎 Filtros Interativos")
        
        # Mapeia nomes de colunas (case-insensitive)
        cols_lower = {col.lower(): col for col in df.columns}
        
        base_col = cols_lower.get('dispatching_base_num')
        sr_col = cols_lower.get('sr_flag')
        pickup_col = cols_lower.get('pulocationid') or cols_lower.get('pickup_location_id')
        
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            if base_col:
                bases = ['Todas'] + sorted(df[base_col].unique().tolist())
                base_selecionada = st.selectbox("Base de Despacho", bases)
            else:
                base_selecionada = None
        
        with col_f2:
            if sr_col:
                shared_filter = st.selectbox("Tipo de Viagem", 
                                            ["Todas", "Compartilhadas", "Não Compartilhadas"])
            else:
                shared_filter = None
        
        with col_f3:
            if pickup_col:
                zonas = ['Todas'] + sorted([str(z) for z in df[pickup_col].unique()])
                zona_selecionada = st.selectbox("Zona de Pickup", zonas)
            else:
                zona_selecionada = None
        
        # Aplicar filtros
        df_filtered = df.copy()
        
        if base_col and base_selecionada and base_selecionada != 'Todas':
            df_filtered = df_filtered[df_filtered[base_col] == base_selecionada]
        
        if sr_col and shared_filter:
            if shared_filter == "Compartilhadas":
                df_filtered = df_filtered[df_filtered[sr_col].notna()]
            elif shared_filter == "Não Compartilhadas":
                df_filtered = df_filtered[df_filtered[sr_col].isna()]
        
        if pickup_col and zona_selecionada and zona_selecionada != 'Todas':
            df_filtered = df_filtered[df_filtered[pickup_col] == int(zona_selecionada)]
        
        st.info(f"📊 Mostrando **{len(df_filtered):,}** de {len(df):,} registros")
        
        # Visualização dos dados
        st.divider()
        st.subheader("📋 Dados")
        
        # Opções de exibição
        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            colunas_exibir = st.multiselect(
                "Colunas a exibir",
                df_filtered.columns.tolist(),
                default=df_filtered.columns.tolist()[:7]
            )
        with col_d2:
            ordenar_por = st.selectbox("Ordenar por", ['Nenhum'] + df_filtered.columns.tolist())
        
        # Preparar visualização
        df_display = df_filtered[colunas_exibir] if colunas_exibir else df_filtered
        
        if ordenar_por != 'Nenhum':
            df_display = df_display.sort_values(ordenar_por, ascending=False)
        
        # Mostrar tabela
        st.dataframe(
            df_display,
            use_container_width=True,
            height=600
        )
        
        # Opções de download
        st.divider()
        st.subheader("💾 Download dos Dados Filtrados")
        
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        
        with col_dl1:
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar como CSV",
                data=csv,
                file_name=f"tlc_fhv_filtrado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_dl2:
            import io
            buffer = io.BytesIO()
            df_display.to_parquet(buffer, index=False)
            st.download_button(
                label="📥 Baixar como Parquet",
                data=buffer.getvalue(),
                file_name=f"tlc_fhv_filtrado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet",
                mime="application/octet-stream",
                use_container_width=True
            )
        
        with col_dl3:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df_display.to_excel(writer, index=False, sheet_name='Dados')
            st.download_button(
                label="📥 Baixar como Excel",
                data=excel_buffer.getvalue(),
                file_name=f"tlc_fhv_filtrado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        # Análise rápida da seleção
        if len(df_display) > 0:
            with st.expander("📊 Análise Rápida da Seleção"):
                col_a1, col_a2, col_a3 = st.columns(3)
                
                # Mapeia colunas
                cols_lower = {col.lower(): col for col in df_display.columns}
                duration_col = cols_lower.get('trip_duration_min')
                base_col = cols_lower.get('dispatching_base_num')
                pickup_col = cols_lower.get('pulocationid') or cols_lower.get('pickup_location_id')
                sr_col = cols_lower.get('sr_flag')
                
                with col_a1:
                    if duration_col:
                        st.metric("Duração Média", f"{df_display[duration_col].mean():.1f} min")
                        st.metric("Duração Mediana", f"{df_display[duration_col].median():.1f} min")
                
                with col_a2:
                    if base_col:
                        st.metric("Bases Únicas", df_display[base_col].nunique())
                    if pickup_col:
                        st.metric("Zonas de Pickup", df_display[pickup_col].nunique())
                
                with col_a3:
                    if sr_col:
                        shared = df_display[sr_col].notna().sum()
                        pct = (shared / len(df_display)) * 100
                        st.metric("Viagens Compartilhadas", f"{shared:,} ({pct:.1f}%)")
    
    else:
        st.info("👆 Clique no botão 'Buscar Dados' para visualizar os dados")

# -----------------------------------------
# RODAPÉ
# -----------------------------------------
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>TLC For-Hire Vehicle Trip Records - 2023</strong></p>
    <p>Dashboard de Análise Exploratória de Dados</p>
    <p style='font-size: 0.8em;'>Dados carregados do MinIO | Processamento com PyArrow e Pandas | Visualizações com Plotly</p>
</div>
""", unsafe_allow_html=True)