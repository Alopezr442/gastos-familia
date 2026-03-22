import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gastos Familia", layout="wide")

# Sustituimos el enlace de visualización por el de exportación directa a CSV
SHEET_ID = "1VufHMJ8RUUih7zNrz9SigztkG7WvtKibG1d29-Nhlw0"
url_presupuesto = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Presupuesto"
url_gastos = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Gastos"

st.title("🏠 Control de Gastos Compartidos")

try:
    # Lectura directa con Pandas
    df_presupuesto = pd.read_csv(url_presupuesto)
    df_gastos = pd.read_csv(url_gastos)
    
    st.subheader("Presupuesto Mensual")
    st.dataframe(df_presupuesto, use_container_width=True)
    
    st.subheader("Historial de Gastos")
    st.dataframe(df_gastos, use_container_width=True)

except Exception as e:
    st.error("No se pudo leer el Excel.")
    st.info("Verifica que en el Excel las pestañas se llamen exactamente: Presupuesto y Gastos")
    st.write(f"Error técnico: {e}")
