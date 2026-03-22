import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gastos Familia", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Carga de datos
df_presupuesto = conn.read(worksheet="Presupuesto", ttl="10m")
df_gastos = conn.read(worksheet="Gastos", ttl="0")

# Asegurar que la columna 'Retirado' existe
if 'Retirado' not in df_gastos.columns:
    df_gastos['Retirado'] = 'No'

st.title("🏠 Gestión de Gastos y Cuenta Bipersonal")

# --- NAVEGACIÓN POR PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["➕ Registrar Gasto", "🏦 Conciliar Cuenta", "📊 Resumen"])

with tab1:
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
                "Usuario": usuario,
                "Retirado": "No" # Por defecto entra como no retirado
            }])
            df_actualizado = pd.concat([df_gastos, nuevo], ignore_index=True)
            conn.update(worksheet="Gastos", data=df_actualizado)
            st.success("✅ Gasto registrado y pendiente de retiro")
            st.rerun()

with tab2:
    st.subheader("Pendientes de retiro (Cuenta Bipersonal)")
    # Filtrar solo lo que no se ha retirado
    pendientes = df_gastos[df_gastos['Retirado'] == 'No']
    
    if not pendientes.empty:
        # Usamos st.data_editor para permitir marcar el retiro directamente
        edited_df = st.data_editor(
            df_gastos,
            column_config={
                "Retirado": st.column_config.SelectboxColumn(
                    "¿Retirado?",
                    options=["Sí", "No"],
                    required=True,
                )
            },
            disabled=["Fecha", "Categoria", "Monto", "Usuario"], # Solo dejamos editar 'Retirado'
            use_container_width=True,
            hide_index=True
        )
        
        if st.button("Confirmar Retiros en Cuenta"):
            conn.update(worksheet="Gastos", data=edited_df)
            st.success("✅ Cuenta Bipersonal actualizada")
            st.rerun()
    else:
        st.info("Todo el dinero ya ha sido retirado de la cuenta.")

with tab3:
    st.subheader("Resumen Mensual")
    # Cálculos de saldos
    gastos_totales = df_gastos.groupby("Categoria")["Monto"].sum().reset_index()
    resumen = pd.merge(df_presupuesto, gastos_totales, on="Categoria", how="left").fillna(0)
    resumen["Disponible"] = resumen["Monto_Mensual"] - resumen["Monto"]
    
    st.dataframe(resumen, use_container_width=True, hide_index=True)
    
    # Mostrar cuánto dinero "debe" la cuenta bipersonal aún
    por_retirar = df_gastos[df_gastos['Retirado'] == 'No']['Monto'].sum()
    st.metric("Total por retirar de Cuenta Bipersonal", f"${int(por_retirar):,}")
