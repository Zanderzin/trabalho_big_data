
# Dashboard Interativo de Vendas de Video Games

Este repositório contém um dashboard interativo desenvolvido em **Streamlit** para análise exploratória de dados de vendas globais de jogos de videogame.

---

## 📌 Funcionalidades

- Filtros interativos (Ano, Plataforma, Gênero, Publisher)
- KPIs globais e regionais
- Séries temporais de vendas
- Comparação entre regiões (NA, EU, JP, Outros)
- Ranking de jogos e publishers
- Treemap por gênero
- Visualizações dinâmicas com Plotly

---

## 📂 Estrutura do Repositório

```

├── data/
│   ├── VideoGames_Vendas.csv
├── docs/
│   ├── relatorio_dashboard.pdf
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## ▶️ Como Executar

```
1. Acessar a VM
2. cd /opt/ceub-bigdata/streamlit
3. Ajustar Dockerfile de acordo com o do repositório
4. docker-compose build 
5. docker-compose up -d
```

Acesse em:  
http://localhost:8501

---

## 📝 Descrição Técnica

O dashboard utiliza:
- **Pandas** para tratamento de dados
- **Streamlit** para interface interativa
- **Plotly Express** para gráficos dinâmicos
- Padronização de colunas para adequação ao modelo do dashboard

---

## 📄 Relatório Final

O relatório acadêmico está disponível no arquivo:

- `relatorio_dashboard.pdf`

---