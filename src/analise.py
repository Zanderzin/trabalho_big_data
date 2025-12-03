import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuração de estilo visual para os gráficos ficarem mais atraentes
sns.set(style="whitegrid")

# ---------------------------------------------------------
# 1. Carregamento e Preparação dos Dados
# ---------------------------------------------------------
# Ler o arquivo CSV para um DataFrame (tabela)
df = pd.read_csv("data/VideoGames_Vendas.csv")

# Converter a coluna de data para o formato correto e extrair o Ano
df['release_date'] = pd.to_datetime(df['release_date'])
df['year'] = df['release_date'].dt.year

# ---------------------------------------------------------
# 2. Cálculo de KPIs (Métricas Principais)
# ---------------------------------------------------------
# Soma total da coluna de vendas
total_sales = df['total_sales(mil)'].sum()

# Média simples da coluna de notas
avg_score = df['critic_score'].mean()

# Encontrar o gênero que tem a maior soma de vendas
top_genre = df.groupby('genre')['total_sales(mil)'].sum().idxmax()

# Exibir os resultados no console
print("--- KPIs Principais ---")
print(f"Volume Total de Vendas: {total_sales:.2f} milhões")
print(f"Nota Média da Crítica: {avg_score:.2f}")
print(f"Gênero Mais Popular: {top_genre}")

# ---------------------------------------------------------
# 3. Geração dos Gráficos (Dashboard)
# ---------------------------------------------------------
# Criar uma 'moldura' (figure) que vai conter 4 gráficos (2 linhas, 2 colunas)
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Análise de Mercado de Games', fontsize=20)

# Gráfico A: Comparação de Gêneros (Barplot)
# Agrupa os dados por gênero, soma as vendas e ordena do maior para o menor
genre_data = df.groupby('genre')['total_sales(mil)'].sum().sort_values(ascending=False)
sns.barplot(x=genre_data.values, y=genre_data.index, ax=axes[0, 0], palette='viridis')
axes[0, 0].set_title('Vendas Totais por Gênero')
axes[0, 0].set_xlabel('Vendas (Milhões)')

# Gráfico B: Série Temporal (Lineplot)
# Agrupa por ano para ver a tendência
year_data = df.groupby('year')['total_sales(mil)'].sum()
sns.lineplot(x=year_data.index, y=year_data.values, ax=axes[0, 1], marker='o', color='blue')
axes[0, 1].set_title('Tendência de Vendas por Ano')
axes[0, 1].set_ylabel('Vendas (Milhões)')

# Gráfico C: Top Consoles (Barplot)
# Pega apenas os 10 primeiros consoles com mais vendas
console_data = df.groupby('console')['total_sales(mil)'].sum().sort_values(ascending=False).head(10)
sns.barplot(x=console_data.index, y=console_data.values, ax=axes[1, 0], palette='magma')
axes[1, 0].set_title('Top 10 Consoles')
axes[1, 0].set_ylabel('Vendas (Milhões)')

# Gráfico D: Correlação (Scatterplot)
# Cruza a nota da crítica com as vendas, colorindo por gênero
sns.scatterplot(data=df, x='critic_score', y='total_sales(mil)', ax=axes[1, 1], hue='genre', alpha=0.6)
axes[1, 1].set_title('Impacto da Nota nas Vendas')
axes[1, 1].set_xlabel('Nota da Crítica')
axes[1, 1].set_ylabel('Vendas (Milhões)')
# Move a legenda para fora para não poluir o gráfico
axes[1, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

# Ajusta o layout para nada ficar sobreposto e salva/mostra
plt.tight_layout()
plt.show() # Em um ambiente local, isso abre a janela com os gráficos