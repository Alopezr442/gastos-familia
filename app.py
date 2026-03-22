import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gastos Familia", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. Función para formatear a miles con punto (Devuelve Texto)
def formatear_punto(valor):
    return f"$ {int(valor):,}".replace(",", ".")

# Carga de datos
df_presupuesto = conn.read(worksheet="Presupuesto", ttl="5m")
df_gastos_raw = conn.read(worksheet="Gastos", ttl="0")
df_gastos = df_gastos_raw.copy()

if 'Retirado' not in df_gastos.columns:
    df_gastos['Retirado'] = 'No'

st.title("🏠 Gestión de Gastos")

tab1, tab2, tab3, tab4 = st.tabs(["➕ Registrar", "🏦 Conciliar", "📊 Resumen", "⚙️ Editar/Borrar"])

# --- TAB 1: REGISTRO (Sigue igual, procesa números) ---
with tab1:
    with st.form("formulario_gasto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", value=datetime.now())
            categoria = st.selectbox("Categoría", df_presupuesto["Categoria"].unique())
        with col2:
            monto = st.number_input("Monto ($)", min_value=0, step=1000)
            usuario = st.radio("Pagado por", ["Agustín", "Laura"], horizontal=True)
        descripcion = st.text_input("Nota (opcional)")
        
        if st.form_submit_button("Guardar Gasto"):
            nuevo = pd.DataFrame([{"Fecha": fecha.strftime("%Y-%m-%d"), "Categoria": categoria, "Monto": monto, "Descripcion": descripcion, "Usuario": usuario, "Retirado": "No"}])
            conn.update(worksheet="Gastos", data=pd.concat([df_gastos_raw, nuevo], ignore_index=True))
            st.success("✅ Registrado")
            st.rerun()

# --- TAB 2: CONCILIACIÓN (Vista formateada) ---
with tab2:
    df_pendientes = df_gastos[df_gastos['Retirado'] == 'No'].copy()
    if not df_pendientes.empty:
        # TRUCO: Formateamos el monto como texto para la vista
        df_ver = df_pendientes.copy()
        df_ver["Monto"] = df_ver["Monto"].apply(formatear_punto)
        df_ver["Check"] = False
        
        edited = st.data_editor(df_ver[["Fecha", "Categoria", "Monto", "Usuario", "Check"]], 
                                disabled=["Fecha", "Categoria", "Monto", "Usuario"], 
                                use_container_width=True, hide_index=True)
        
        if st.button("Confirmar Retiros"):
            indices_seleccionados = edited[edited["Check"] == True].index
            real_indices = df_pendientes.index[indices_seleccionados]
            df_gastos.loc[real_indices, 'Retirado'] = 'Sí'
            conn.update(worksheet="Gastos", data=df_gastos)
            st.rerun()
    else:
        st.info("No hay retiros pendientes.")

# --- TAB 3: RESUMEN (Métrica y Tabla con puntos forzados) ---
with tab3:
    por_retirar = df_gastos[df_gastos['Retirado'] == 'No']['Monto'].sum()
    st.metric("Total por retirar de la Bipersonal", formatear_punto(por_retirar))
    
    st.divider()
    gastos_totales = df_gastos.groupby("Categoria")["Monto"].sum().reset_index()
    resumen = pd.merge(df_presupuesto, gastos_totales, on="Categoria", how="left").fillna(0)
    resumen["Disponible"] = resumen["Monto_Mensual"] - resumen["Monto"]
    
    # Aplicamos formato de texto a toda la tabla para asegurar los puntos
    resumen_ver = resumen.copy()
    for col in ["Monto_Mensual", "Monto", "Disponible"]:
        resumen_ver[col] = resumen_ver[col].apply(formatear_punto)
    
    st.table(resumen_ver) # Usamos st.table que es más estricta con el formato de texto

# --- TAB 4: EDICIÓN (Aquí se mantienen números para poder editar) ---
with tab4:
    st.caption("En edición se ven sin puntos para permitir el ingreso numérico.")
    df_editado = st.data_editor(df_gastos, num_rows="dynamic", use_container_width=True)
    if st.button("Guardar Cambios Maestros"):
        conn.update(worksheet="Gastos", data=df_editado)
        st.success("✅ Base de datos actualizada")
        st.rerun()
