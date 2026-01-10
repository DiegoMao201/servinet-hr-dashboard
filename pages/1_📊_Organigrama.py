import streamlit as st
import graphviz
from modules.database import get_employees

st.title("Organigrama Dinámico SERVINET")

df = get_employees() # Asume columnas: 'NOMBRE', 'CARGO', 'Jefe_Directo'

# Crear el grafo
graph = graphviz.Digraph()
graph.attr(rankdir='TB') # Top to Bottom

for index, row in df.iterrows():
    # Nodo del empleado
    label = f"{row['Nombre']}\n({row['Cargo']})"
    graph.node(row['Nombre'], label=label, shape='box', style='filled', fillcolor='lightblue')
    
    # Conexión con el jefe
    if row['Jefe_Directo'] and row['Jefe_Directo'] in df['Nombre'].values:
        graph.edge(row['Jefe_Directo'], row['Nombre'])

st.graphviz_chart(graph)
