import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gastos Familia", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Carga de datos con cache de 10 min para eficiencia
df_presupuesto = conn.read(worksheet="Presupuesto", ttl="10m")
df_gastos = conn.read(worksheet="Gastos", ttl="0") # Gastos siempre fresco

st.title("🏠 Control de Gastos Compartidos")

# --- FORMULARIO ---
with st.expander("➕ REGISTRAR GASTO NUEVO", expanded=True):
    with st.form("formulario_gasto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", value=datetime.now())
            categoria = st.selectbox("Categoría", df_presupuesto["Categoria"].unique())
        with col2:
            monto = st.number_input("Monto ($)", min_value=0, step=1000)
            usuario = st.radio("Pagado por", ["Él", "Ella"], horizontal=True)
        
        descripcion = st.text_input("Nota (opcional)")
        
        if st.form_submit_button("Guardar Gasto"):
            nuevo = pd.DataFrame([{
                "Fecha": fecha.strftime("%Y-%m-%d"),
                "Categoria": categoria,
                "Monto": monto,
                "Descripcion": descripcion,
                "Usuario": usuario
            }])
            # Limpiar datos nulos si los hay
            df_gastos = df_gastos.dropna(how='all')
            df_actualizado = pd.concat([df_gastos, nuevo], ignore_index=True)
            conn.update(worksheet="Gastos", data=df_actualizado)
            st.success("✅ Gasto registrado")
            st.rerun()

# --- CÁLCULOS Y VISUALIZACIÓN ---
st.divider()
st.subheader("📊 Saldo del Mes")

# Agrupar gastos por categoría
gastos_totales = df_gastos.groupby("Categoria")["Monto"].sum().reset_index()
resumen = pd.merge(df_presupuesto, gastos_totales, on="Categoria", how="left").fillna(0)
resumen["Saldo"] = resumen["Monto_Mensual"] - resumen["Monto"]

# Mostrar métricas rápidas
cols = st.columns(len(resumen))
for i, row in resumen.iterrows():
    color = "normal" if row['Saldo'] >= 0 else "inverse"
    st.metric(label=row['Categoria'], value=f"${int(row['Monto']):,}", delta=f"${int(row['Saldo']):,}", delta_color=color)

st.divider()
st.subheader("📝 Historial Reciente")
st.dataframe(df_gastos.sort_index(ascending=False), use_container_width=True)
