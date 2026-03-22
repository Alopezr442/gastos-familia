import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Gastos Familia", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_presupuesto = conn.read(worksheet="Presupuesto")
    df_gastos = conn.read(worksheet="Gastos")
    
    st.title("🏠 Control de Gastos")
    
    if not df_presupuesto.empty:
        st.subheader("Resumen de Presupuesto")
        st.write(df_presupuesto)
    else:
        st.warning("La pestaña 'Presupuesto' está vacía.")
        
except Exception as e:
    st.error(f"Error de conexión: Verifica que las pestañas se llamen 'Presupuesto' y 'Gastos'")
    st.info("Asegúrate de que el enlace en Secrets termine en /edit")
