import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gastos Familia", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Carga de datos
df_presupuesto = conn.read(worksheet="Presupuesto", ttl="5m")
df_gastos_raw = conn.read(worksheet="Gastos", ttl="0")

# Preparación de datos
df_gastos = df_gastos_raw.copy()
if 'Retirado' not in df_gastos.columns:
    df_gastos['Retirado'] = 'No'

st.title("🏠 Gestión de Gastos y Cuenta Bipersonal")

tab1, tab2, tab3, tab4 = st.tabs(["➕ Registrar", "🏦 Conciliar", "📊 Resumen", "⚙️ Editar/Borrar"])

# --- TAB 1: REGISTRO ---
with tab1:
    with st.form("formulario_gasto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", value=datetime.now())
            categoria = st.selectbox("Categoría", df_presupuesto["Categoria"].unique())
        with col2:
            monto = st.number_input("Monto ($)", min_value=0, step=1000)
            usuario = st.radio("Pagado por", ["Agustin", "Laura"], horizontal=True)
        
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

# --- TAB 2: CONCILIACIÓN ---
with tab2:
    st.subheader("Pendientes de retiro")
    df_pendientes = df_gastos[df_gastos['Retirado'] == 'No'].copy()
    
    if not df_pendientes.empty:
        df_pendientes['Check_Retiro'] = False
        
        edited_pendientes = st.data_editor(
            df_pendientes[["Fecha", "Categoria", "Monto", "Usuario", "Descripcion", "Check_Retiro"]],
            column_config={
                # FORMATO MONEDA FORZADO (Punto como miles)
                "Monto": st.column_config.NumberColumn("Monto", format="$%d", step=1), 
                "Check_Retiro": st.column_config.CheckboxColumn("¿Retirar?", default=False)
            },
            disabled=["Fecha", "Categoria", "Monto", "Usuario", "Descripcion"],
            use_container_width=True, hide_index=True
        )
        
        if st.button("Confirmar Retiros Seleccionados"):
            indices_si = edited_pendientes[edited_pendientes['Check_Retiro'] == True].index
            df_gastos.loc[indices_si, 'Retirado'] = 'Sí'
            conn.update(worksheet="Gastos", data=df_gastos)
            st.success("✅ Movimientos conciliados")
            st.rerun()
    else:
        st.info("No hay retiros pendientes.")

# --- TAB 3: RESUMEN ---
with tab3:
    por_retirar = df_gastos[df_gastos['Retirado'] == 'No']['Monto'].sum()
    # Aquí usamos f-string para asegurar el punto manual en la métrica
    st.metric("Total por retirar de la Bipersonal", f"$ {int(por_retirar):,}".replace(",", "."))
    st.divider()
    
    gastos_totales = df_gastos.groupby("Categoria")["Monto"].sum().reset_index()
    resumen = pd.merge(df_presupuesto, gastos_totales, on="Categoria", how="left").fillna(0)
    resumen["Disponible"] = resumen["Monto_Mensual"] - resumen["Monto"]
    
    st.dataframe(
        resumen, 
        column_config={
            "Monto_Mensual": st.column_config.NumberColumn("Presupuesto", format="$%d"),
            "Monto": st.column_config.NumberColumn("Gastado", format="$%d"),
            "Disponible": st.column_config.NumberColumn("Disponible", format="$%d")
        },
        use_container_width=True, hide_index=True
    )

# --- TAB 4: EDICIÓN Y BORRADO ---
with tab4:
    st.subheader("Consola de Edición")
    
    df_editado = st.data_editor(
        df_gastos,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=False,
        column_config={
            "Monto": st.column_config.NumberColumn("Monto", format="$%d"), 
            "Retirado": st.column_config.SelectboxColumn("Estado Retiro", options=["Sí", "No"])
        }
    )
    
    if st.button("Guardar Cambios Maestros"):
        conn.update(worksheet="Gastos", data=df_editado)
        st.success("✅ Base de datos actualizada")
        st.rerun()
