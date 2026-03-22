import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuración de página
st.set_page_config(page_title="Presupuesto Familiar", layout="wide")

# Conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Leer datos existentes
df_presupuesto = conn.read(worksheet="Presupuesto")
df_gastos = conn.read(worksheet="Gastos")

st.title("🏠 Control de Gastos Compartidos")

# --- FORMULARIO DE INGRESO ---
with st.expander("➕ Registrar Nuevo Gasto"):
    with st.form("nuevo_gasto"):
        fecha = st.date_input("Fecha")
        categoria = st.selectbox("Categoría", df_presupuesto["Categoria"].tolist())
        monto = st.number_input("Monto", min_value=0, step=1000)
        desc = st.text_input("Descripción (opcional)")
        usuario = st.radio("Quién pagó", ["Él", "Ella"], horizontal=True)
        
        if st.form_submit_button("Guardar Gasto"):
            # Lógica para añadir fila (esto lo puliremos en el siguiente paso)
            st.success("Gasto registrado localmente (falta vincular escritura)")

# --- VISUALIZACIÓN ---
st.header("📊 Estado Actual")
# Aquí calculamos el total gastado vs presupuesto
resumen_gastos = df_gastos.groupby("Categoria")["Monto"].sum().reset_index()
comparativo = pd.merge(df_presupuesto, resumen_gastos, on="Categoria", how="left").fillna(0)
comparativo["Disponible"] = comparativo["Monto_Mensual"] - comparativo["Monto"]

st.dataframe(comparativo, use_container_width=True)
