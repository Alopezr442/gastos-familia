import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gastos Familia", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Carga de datos sin caché para evitar desfases en conciliación
df_presupuesto = conn.read(worksheet="Presupuesto", ttl="5m")
df_gastos = conn.read(worksheet="Gastos", ttl="0")

# Asegurar columna Retirado
if 'Retirado' not in df_gastos.columns:
    df_gastos['Retirado'] = False

# Convertir a booleano para el checkbox de la interfaz
df_gastos['Retirado'] = df_gastos['Retirado'].map({'Sí': True, 'No': False}).fillna(False)

st.title("🏠 Gestión de Gastos y Cuenta Bipersonal")

tab1, tab2, tab3 = st.tabs(["➕ Registrar Gasto", "🏦 Conciliar (Check)", "📊 Resumen"])

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
                "Retirado": "No"
            }])
            df_actualizado = pd.concat([df_gastos.replace({True: 'Sí', False: 'No'}), nuevo], ignore_index=True)
            conn.update(worksheet="Gastos", data=df_actualizado)
            st.success("✅ Registrado")
            st.rerun()

with tab2:
    st.subheader("Selecciona los ítems ya retirados de la cuenta")
    
    # Editor de datos con checkboxes
    edited_df = st.data_editor(
        df_gastos,
        column_config={
            "Retirado": st.column_config.CheckboxColumn(
                "¿Retirado?",
                help="Marca los que ya sacaste de la cuenta bipersonal",
                default=False,
            )
        },
        disabled=["Fecha", "Categoria", "Monto", "Usuario", "Descripcion"],
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("Confirmar y Actualizar Cuenta"):
        # Convertir de nuevo a texto para el Excel
        df_final = edited_df.copy()
        df_final['Retirado'] = df_final['Retirado'].map({True: 'Sí', False: 'No'})
        
        conn.update(worksheet="Gastos", data=df_final)
        st.success("✅ Movimientos confirmados en el Excel")
        st.rerun()

with tab3:
    # Métricas de control
    por_retirar = df_gastos[df_gastos['Retirado'] == False]['Monto'].sum()
    st.metric("Pendiente por retirar de la Bipersonal", f"${int(por_retirar):,}")
    
    st.divider()
    gastos_totales = df_gastos.groupby("Categoria")["Monto"].sum().reset_index()
    resumen = pd.merge(df_presupuesto, gastos_totales, on="Categoria", how="left").fillna(0)
    resumen["Disponible"] = resumen["Monto_Mensual"] - resumen["Monto"]
    st.table(resumen)
