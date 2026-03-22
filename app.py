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

# --- TAB 2: CONCILIACIÓN ---
with tab2:
    st.subheader("Pendientes de retiro")
    df_pendientes = df_gastos[df_gastos['Retirado'] == 'No'].copy()
    
    if not df_pendientes.empty:
        # Columna temporal para el check
        df_pendientes['Check_Retiro'] = False
        
        edited_pendientes = st.data_editor(
            df_pendientes[["Fecha", "Categoria", "Monto", "Usuario", "Descripcion", "Check_Retiro"]],
            column_config={"Check_Retiro": st.column_config.CheckboxColumn("¿Retirar?", default=False)},
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
    st.metric("Total por retirar de la Bipersonal", f"${int(por_retirar):,}")
    st.divider()
    gastos_totales = df_gastos.groupby("Categoria")["Monto"].sum().reset_index()
    resumen = pd.merge(df_presupuesto, gastos_totales, on="Categoria", how="left").fillna(0)
    resumen["Disponible"] = resumen["Monto_Mensual"] - resumen["Monto"]
    st.dataframe(resumen, use_container_width=True, hide_index=True)

# --- TAB 4: EDICIÓN Y BORRADO ---
with tab4:
    st.subheader("Consola de Edición")
    st.caption("Puedes editar cualquier celda directamente o seleccionar una fila y presionar 'Suprimir' en tu teclado para borrar.")
    
    # Editor completo (permite borrar filas y editar celdas)
    df_editado = st.data_editor(
        df_gastos,
        num_rows="dynamic", # Permite añadir/borrar filas
        use_container_width=True,
        hide_index=False,
        column_config={
            "Retirado": st.column_config.SelectboxColumn("Estado Retiro", options=["Sí", "No"])
        }
    )
    
    if st.button("Guardar Cambios Maestros"):
        conn.update(worksheet="Gastos", data=df_editado)
        st.success("✅ Base de datos actualizada correctamente")
        st.rerun()
