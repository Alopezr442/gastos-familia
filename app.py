import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gastos Familia", layout="wide")

# Inicialización de conexión con manejo de errores
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_presupuesto = conn.read(worksheet="Presupuesto", ttl="1s")
    df_gastos_raw = conn.read(worksheet="Gastos", ttl="1s")
except Exception as e:
    st.error("⚠️ Error de conexión. Reintenta en unos segundos.")
    st.stop()

def formatear_punto(valor):
    try:
        return f"$ {int(valor):,}".replace(",", ".")
    except:
        return "$ 0"

# Normalización de fechas
df_gastos_raw['Fecha'] = pd.to_datetime(df_gastos_raw['Fecha'], errors='coerce').dt.normalize()
df_gastos_raw = df_gastos_raw.dropna(subset=['Fecha'])

# --- LÓGICA DE TIEMPO REAL ---
hoy = datetime.now()

# Sidebar de Control Temporal (Mes actual por defecto)
st.sidebar.title("🗓️ Periodo de Control")
meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 
              7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}

mes_sel_nombre = st.sidebar.selectbox("Seleccionar Mes", list(meses_dict.values()), index=hoy.month-1)
anio_sel = st.sidebar.number_input("Año", value=hoy.year, step=1)
mes_sel_num = [k for k, v in meses_dict.items() if v == mes_sel_nombre][0]

# Filtrar Gastos por periodo
df_gastos = df_gastos_raw[
    (df_gastos_raw['Fecha'].dt.month == mes_sel_num) & 
    (df_gastos_raw['Fecha'].dt.year == anio_sel)
].copy()

if 'Retirado' not in df_gastos.columns:
    df_gastos['Retirado'] = 'No'

st.title(f"🏠 Gestión {mes_sel_nombre} {anio_sel}")

tabs = st.tabs(["🚀 Planificación", "➕ Registrar", "🏦 Conciliar", "📊 Balance", "⚙️ Editar Todo"])

# --- TAB 0: PLANIFICACIÓN (RESTAURADA TOTALMENTE) ---
with tabs[0]:
    st.header(f"📅 Planificación Mensual")
    # UF del día con valor sugerido dinámico aproximado
    col_uf = st.number_input("UF del día:", value=39796.31, step=0.1, format="%.2f")
    
    # Cuota DEDE dinámica (Base Marzo 2026 = 35)
    meses_dif = (anio_sel - 2026) * 12 + (mes_sel_num - 3)
    cuota_actual = 35 + meses_dif
    
    # Cálculos de Aportes
    hipo_t, dede_t = 20.77 * col_uf, 15.18 * col_uf
    bipers_t = df_presupuesto["Monto_Mensual"].sum()
    
    hipo_a, hipo_l = hipo_t * 0.748, hipo_t * 0.252
    dede_a, dede_l = dede_t * 0.5, dede_t * 0.5
    bipers_a, bipers_l = bipers_t * 0.858, bipers_t * 0.142
    
    total_a, total_l = hipo_a + dede_a + bipers_a, hipo_l + dede_l + bipers_l
    total_deposito = total_a + total_l

    c1, c2, c3 = st.columns(3)
    c1.metric("Aporte Agustín", formatear_punto(total_a))
    c2.metric("Aporte Laura", formatear_punto(total_l))
    c3.metric("Total Mes", formatear_punto(total_deposito))
    
    st.divider()
    
    if st.button("🚀 Iniciar este Mes (Cargar Créditos Agustín)"):
        fecha_ini = datetime(anio_sel, mes_sel_num, 1).strftime("%Y-%m-%d")
        deudas = pd.DataFrame([
            {"Fecha": fecha_ini, "Categoria": "Hipotecario", "Monto": hipo_t, "Descripcion": "Dividendo", "Usuario": "Agustín", "Retirado": "No"},
            {"Fecha": fecha_ini, "Categoria": "DEDE", "Monto": dede_t, "Descripcion": f"Cuota {cuota_actual}", "Usuario": "Agustín", "Retirado": "No"}
        ])
        df_subir = pd.concat([df_gastos_raw, deudas], ignore_index=True)
        df_subir['Fecha'] = pd.to_datetime(df_subir['Fecha']).dt.strftime('%Y-%m-%d')
        conn.update(worksheet="Gastos", data=df_subir)
        st.cache_data.clear()
        st.rerun()

    st.subheader("📊 Detalle de Transferencia")
    detalle = pd.DataFrame({
        "Ítem": ["Hipotecario (20.77 UF)", "DEDE (15.18 UF)", "Presupuesto Casa"],
        "Total": [formatear_punto(hipo_t), formatear_punto(dede_t), formatear_punto(bipers_t)],
        "Agustín": [formatear_punto(hipo_a), formatear_punto(dede_a), formatear_punto(bipers_a)],
        "Laura": [formatear_punto(hipo_l), formatear_punto(dede_l), formatear_punto(bipers_l)]
    })
    st.table(detalle)
    
    st.info(f"📝 **Mensaje DEDE:**\n\nRepertorio 2497 del 2023 OT 786773 deuda Karen Andrea cuota {cuota_actual}")

    with st.expander("🔍 Gestionar Categorías y Montos del Presupuesto"):
        st.caption("Añade filas al final o selecciona y presiona 'Suprimir' para borrar.")
        df_pres_edit = st.data_editor(
            df_presupuesto, 
            column_config={"Monto_Mensual": st.column_config.NumberColumn("Monto ($)", format="$ %d")}, 
            num_rows="dynamic", use_container_width=True, hide_index=True
        )
        if st.button("Guardar Estructura Presupuesto"):
            conn.update(worksheet="Presupuesto", data=df_pres_edit.dropna(subset=["Categoria"]))
            st.cache_data.clear()
            st.rerun()

# --- TAB 1: REGISTRO (CON FECHA ACTUAL) ---
with tabs[1]:
    with st.form("f_reg", clear_on_submit=True):
        f = st.date_input("Fecha Gasto", value=hoy)
        cat = st.selectbox("Categoría", df_presupuesto["Categoria"].unique())
        m = st.number_input("Monto", min_value=0, step=1000)
        u = st.radio("Pagado por", ["Agustín", "Laura"], horizontal=True)
        d = st.text_input("Nota")
        if st.form_submit_button("Guardar"):
            nuevo = pd.DataFrame([{"Fecha": f.strftime("%Y-%m-%d"), "Categoria": cat, "Monto": m, "Descripcion": d, "Usuario": u, "Retirado": "No"}])
            df_subir = pd.concat([df_gastos_raw, nuevo], ignore_index=True)
            df_subir['Fecha'] = pd.to_datetime(df_subir['Fecha']).dt.strftime('%Y-%m-%d')
            conn.update(worksheet="Gastos", data=df_subir)
            st.cache_data.clear()
            st.rerun()

# --- TAB 2: CONCILIAR (LÓGICA SEGURA CONTRA INDEXERROR) ---
with tabs[2]:
    st.subheader("🏦 Conciliación de Retiros")
    df_pend = df_gastos[df_gastos['Retirado'] == 'No'].copy()
    
    if not df_pend.empty:
        ca, cl = st.columns(2)
        ca.metric("Por retirar Agustín", formatear_punto(df_pend[df_pend['Usuario'] == 'Agustín']['Monto'].sum()))
        cl.metric("Por retirar Laura", formatear_punto(df_pend[df_pend['Usuario'] == 'Laura']['Monto'].sum()))
        
        st.divider()
        u_f = st.radio("Ver gastos de:", ["Ambos", "Agustín", "Laura"], horizontal=True)
        df_v = df_pend[df_pend['Usuario'] == u_f].copy() if u_f != "Ambos" else df_pend.copy()
        
        if u_f != "Ambos" and st.button(f"Marcar TODO de {u_f} como retirado"):
            df_gastos_raw.loc[df_v.index, 'Retirado'] = 'Sí'
            df_subir = df_gastos_raw.copy()
            df_subir['Fecha'] = pd.to_datetime(df_subir['Fecha']).dt.strftime('%Y-%m-%d')
            conn.update(worksheet="Gastos", data=df_subir)
            st.cache_data.clear()
            st.rerun()

        df_v["Confirmar"] = False
        df_v["Fecha_V"] = df_v["Fecha"].dt.strftime("%d/%m/%Y")
        ed = st.data_editor(
            df_v[["Fecha_V", "Categoria", "Monto", "Usuario", "Confirmar"]],
            column_config={"Monto": st.column_config.NumberColumn(format="$ %d"), "Confirmar": st.column_config.CheckboxColumn()},
            disabled=["Fecha_V", "Categoria", "Usuario"], use_container_width=True
        )
        
        if st.button("Confirmar Selección"):
            for idx in ed.index:
                row = ed.loc[idx]
                df_gastos_raw.at[idx, "Monto"] = row["Monto"]
                if row["Confirmar"]: 
                    df_gastos_raw.at[idx, "Retirado"] = "Sí"
            
            df_subir = df_gastos_raw.copy()
            df_subir['Fecha'] = pd.to_datetime(df_subir['Fecha']).dt.strftime('%Y-%m-%d')
            conn.update(worksheet="Gastos", data=df_subir)
            st.cache_data.clear()
            st.rerun()
    else: 
        st.info("Sin retiros pendientes.")

# --- TAB 3: BALANCE ---
with tabs[3]:
    m_si = df_gastos[df_gastos['Retirado'] == 'Sí']['Monto'].sum()
    m_no = df_gastos[df_gastos['Retirado'] == 'No']['Monto'].sum()
    s_ba = total_deposito - m_si
    s_di = s_ba - m_no
    cb1, cb2, cb3 = st.columns(3)
    cb1.metric("Saldo en Banco", formatear_punto(s_ba))
    cb2.metric("Pendiente Retiro", formatear_punto(m_no))
    cb3.metric("Saldo Disponible", formatear_punto(s_di))
    
    st.divider()
    res = pd.merge(df_presupuesto, df_gastos.groupby("Categoria")["Monto"].sum().reset_index(), on="Categoria", how="left").fillna(0)
    res["Disponible"] = res["Monto_Mensual"] - res["Monto"]
    for c in ["Monto_Mensual", "Monto", "Disponible"]: res[c] = res[c].apply(formatear_punto)
    st.table(res)

# --- TAB 4: EDITAR TODO ---
with tabs[4]:
    df_ed_v = df_gastos_raw.copy()
    df_ed_v['Fecha'] = df_ed_v['Fecha'].dt.strftime("%Y-%m-%d")
    df_ed = st.data_editor(df_ed_v, num_rows="dynamic", use_container_width=True)
    if st.button("Guardar Cambios Maestros"):
        df_ed['Fecha'] = pd.to_datetime(df_ed['Fecha']).dt.strftime('%Y-%m-%d')
        conn.update(worksheet="Gastos", data=df_ed)
        st.cache_data.clear()
        st.rerun()
