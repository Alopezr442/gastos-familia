import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gastos Familia", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Carga de datos
df_presupuesto = conn.read(worksheet="Presupuesto", ttl="5m")
df_gastos_raw = conn.read(worksheet="Gastos", ttl="0")

# Limpieza y preparación de datos
df_gastos = df_gastos_raw.copy()
if 'Retirado' not in df_gastos.columns:
    df_gastos['Retirado'] = 'No'

# Convertimos a booleano para el editor
df_gastos['Retirado_Bool'] = df_gastos['Retirado'].map({'Sí': True, 'No': False}).fillna(False)

st.title("🏠 Gestión de Gastos y Cuenta Bipersonal")

tab1, tab2, tab3 = st.tabs(["➕ Registrar Gasto", "🏦 Conciliar (Pendientes)", "📊 Resumen"])

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
            df_actualizado = pd.concat([df_gastos_raw, nuevo], ignore_index=True)
            conn.update(worksheet="Gastos", data=df_actualizado)
            st.success("✅ Registrado")
            st.rerun()

with tab2:
    st.subheader("Ítems por retirar de la cuenta")
    
    # FILTRO: Solo mostrar lo que NO ha sido retirado
    df_pendientes = df_gastos[df_gastos['Retirado_Bool'] == False].copy()
    
    if not df_pendientes.empty:
        # Mostramos solo columnas relevantes para limpiar la vista
        cols_mostrar = ["Fecha", "Categoria", "Monto", "Usuario", "Descripcion", "Retirado_Bool"]
        
        edited_pendientes = st.data_editor(
            df_pendientes[cols_mostrar],
            column_config={
                "Retirado_Bool": st.column_config.CheckboxColumn(
                    "¿Retirar?",
                    help="Marca para confirmar que ya sacaste el dinero",
                    default=False,
                )
            },
            disabled=["Fecha", "Categoria", "Monto", "Usuario", "Descripcion"],
            use_container_width=True,
            hide_index=True
        )
        
        if st.button("Confirmar Retiros Seleccionados"):
            # 1. Identificar qué filas cambiaron a True
            indices_a_actualizar = edited_pendientes[edited_pendientes['Retirado_Bool'] == True].index
            
            # 2. Actualizar el dataframe original usando los índices
            df_gastos.loc[indices_a_actualizar, 'Retirado'] = 'Sí'
            
            # 3. Quitar la columna temporal y guardar
            df_final = df_gastos.drop(columns=['Retirado_Bool'])
            conn.update(worksheet="Gastos", data=df_final)
            
            st.success("✅ Ítems retirados. Ahora aparecerán solo en el Resumen.")
            st.rerun()
    else:
        st.info("👌 No hay retiros pendientes. ¡La cuenta bipersonal está al día!")

with tab3:
    # Métrica de dinero que aún "está" en la cuenta pero ya se gastó
    por_retirar = df_gastos[df_gastos['Retirado'] == 'No']['Monto'].sum()
    st.metric("Total por retirar de la Bipersonal", f"${int(por_retirar):,}")
    
    st.divider()
    st.subheader("Historial Completo")
    # Mostramos todo para auditoría, ordenado por fecha
    st.dataframe(df_gastos.drop(columns=['Retirado_Bool']).sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True)
