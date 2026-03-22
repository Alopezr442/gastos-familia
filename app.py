import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gastos Familia", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def formatear_punto(valor):
    try:
        return f"$ {int(valor):,}".replace(",", ".")
    except:
        return "$ 0"

# --- CARGA DE DATOS ---
df_presupuesto = conn.read(worksheet="Presupuesto", ttl="0")
df_gastos_raw = conn.read(worksheet="Gastos", ttl="0")

# Normalización de fechas al leer para evitar el error de horas
df_gastos_raw['Fecha'] = pd.to_datetime(df_gastos_raw['Fecha'], errors='coerce').dt.normalize()
df_gastos_raw = df_gastos_raw.dropna(subset=['Fecha'])

# Sidebar de Control
st.sidebar.title("🗓️ Periodo")
meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 
              7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
mes_sel_nombre = st.sidebar.selectbox("Mes", list(meses_dict.values()), index=datetime.now().month-1)
anio_sel = st.sidebar.number_input("Año", value=datetime.now().year, step=1)
mes_sel_num = [k for k, v in meses_dict.items() if v == mes_sel_nombre][0]

# Filtro por periodo
df_gastos = df_gastos_raw[
    (df_gastos_raw['Fecha'].dt.month == mes_sel_num) & 
    (df_gastos_raw['Fecha'].dt.year == anio_sel)
].copy()

if 'Retirado' not in df_gastos.columns:
    df_gastos['Retirado'] = 'No'

st.title(f"🏠 Gestión {mes_sel_nombre} {anio_sel}")
tabs = st.tabs(["🚀 Planificación", "➕ Registrar", "🏦 Conciliar", "📊 Balance", "⚙️ Editar Todo"])

# --- TAB 0: PLANIFICACIÓN ---
with tabs[0]:
    st.header(f"📅 Plan Mensual")
    col_uf = st.number_input("UF del día 1:", value=39796.31, step=0.1, format="%.2f")
    meses_dif = (anio_sel - 2026) * 12 + (mes_sel_num - 3)
    cuota_actual = 35 + meses_dif
    
    hipo_t, dede_t = 20.77 * col_uf, 15.18 * col_uf
    bipers_t = df_presupuesto["Monto_Mensual"].sum()
    
    hipo_a, hipo_l = hipo_t * 0.748, hipo_t * 0.252
    dede_a, dede_l = dede_t * 0.5, dede_t * 0.5
    bipers_a, bipers_l = bipers_t * 0.858, bipers_t * 0.142
    
    total_a, total_l = hipo_a + dede_a + bipers_a, hipo_l + dede_l + bipers_l
    total_deposito = total_a + total_l

    c1, c2, c3 = st.columns(3)
    c1.metric("Agustín", formatear_punto(total_a))
    c2.metric("Laura", formatear_punto(total_l))
    c3.metric("Total Mes", formatear_punto(total_deposito))
    
    if st.button("🚀 Iniciar Mes (Cargar Créditos)"):
        fecha_ini = datetime(anio_sel, mes_sel_num, 1).strftime("%Y-%m-%d")
        nuevas_deudas = pd.DataFrame([
            {"Fecha": fecha_ini, "Categoria": "Hipotecario", "Monto": hipo_t, "Descripcion": "Dividendo", "Usuario": "Agustín", "Retirado": "No"},
            {"Fecha": fecha_ini, "Categoria": "DEDE", "Monto": dede_t, "Descripcion": f"Cuota {cuota_actual}", "Usuario": "Agustín", "Retirado": "No"}
        ])
        # Unir, resetear índice y forzar fecha string antes de subir
        df_subir = pd.concat([df_gastos_raw, nuevas_deudas], ignore_index=True)
        df_subir['Fecha'] = df_subir['Fecha'].dt.strftime('%Y-%m-%d')
        conn.update(worksheet="Gastos", data=df_subir)
        st.cache_data.clear()
        st.rerun()

    st.table(pd.DataFrame({
        "Ítem": ["Hipotecario", "DEDE", "Presupuesto"],
        "Total": [formatear_punto(hipo_t), formatear_punto(dede_t), formatear_punto(bipers_t)],
        "Agustín": [formatear_punto(hipo_a), formatear_punto(dede_a), formatear_punto(bipers_a)],
        "Laura": [formatear_punto(hipo_l), formatear_punto(dede_l), formatear_punto(bipers_l)]
    }))

# --- TAB 1: REGISTRAR ---
with tabs[1]:
    with st.form("f_reg", clear_on_submit=True):
        f = st.date_input("Fecha Gasto", value=datetime(anio_sel, mes_sel_num, 1))
        cat = st.selectbox("Categoría", df_presupuesto["Categoria"].unique())
        m = st.number_input("Monto", min_value=0, step=1000)
        u = st.radio("Pagado por", ["Agustín", "Laura"], horizontal=True)
        d = st.text_input("Nota")
        if st.form_submit_button("Guardar"):
            n = pd.DataFrame([{"Fecha": f.strftime("%Y-%m-%d"), "Categoria": cat, "Monto": m, "Descripcion": d, "Usuario": u, "Retirado": "No"}])
            df_subir = pd.concat([df_gastos_raw, n], ignore_index=True)
            # Asegurar formato fecha string para evitar horas en Sheets
            df_subir['Fecha'] = pd.to_datetime(df_subir['Fecha']).dt.strftime('%Y-%m-%d')
            conn.update(worksheet="Gastos", data=df_subir)
            st.cache_data.clear()
            st.rerun()

# --- TAB 2: CONCILIAR ---
with tabs[2]:
    df_pend = df_gastos[df_gastos['Retirado'] == 'No'].copy()
    if not df_pend.empty:
        ca, cl = st.columns(2)
        ca.metric("Pendiente Agustín", formatear_punto(df_pend[df_pend['Usuario'] == 'Agustín']['Monto'].sum()))
        cl.metric("Pendiente Laura", formatear_punto(df_pend[df_pend['Usuario'] == 'Laura']['Monto'].sum()))
        
        user_f = st.radio("Filtrar:", ["Ambos", "Agustín", "Laura"], horizontal=True)
        df_v = df_pend[df_pend['Usuario'] == user_f].copy() if user_f != "Ambos" else df_pend.copy()
        
        if user_f != "Ambos" and st.button(f"Retirar TODO de {user_f}"):
            df_gastos_raw.loc[df_pend[df_pend['Usuario'] == user_f].index, 'Retirado'] = 'Sí'
            df_subir = df_gastos_raw.copy()
            df_subir['Fecha'] = df_subir['Fecha'].dt.strftime('%Y-%m-%d')
            conn.update(worksheet="Gastos", data=df_subir)
            st.cache_data.clear()
            st.rerun()

        df_v["Check"] = False
        df_v["Fecha_V"] = df_v["Fecha"].dt.strftime("%d/%m/%Y")
        ed = st.data_editor(df_v[["Fecha_V", "Categoria", "Monto", "Usuario", "Check"]], 
                            column_config={"Monto": st.column_config.NumberColumn(format="$ %d")},
                            use_container_width=True, hide_index=True)
        if st.button("Confirmar Manual"):
            for i, row in ed.iterrows():
                idx_orig = df_v.index[i]
                df_gastos_raw.at[idx_orig, "Monto"] = row["Monto"]
                if row["Check"]: df_gastos_raw.at[idx_orig, "Retirado"] = "Sí"
            df_subir = df_gastos_raw.copy()
            df_subir['Fecha'] = df_subir['Fecha'].dt.strftime('%Y-%m-%d')
            conn.update(worksheet="Gastos", data=df_subir)
            st.cache_data.clear()
            st.rerun()
    else: st.info("Nada pendiente.")

# --- TAB 3: BALANCE ---
with tabs[3]:
    m_si = df_gastos[df_gastos['Retirado'] == 'Sí']['Monto'].sum()
    m_no = df_gastos[df_gastos['Retirado'] == 'No']['Monto'].sum()
    s_ban = total_deposito - m_si
    s_dis = s_ban - m_no
    cb1, cb2, cb3 = st.columns(3)
    cb1.metric("En Banco", formatear_punto(s_ban))
    cb2.metric("Por Retirar", formatear_punto(m_no))
    cb3.metric("Disponible", formatear_punto(s_dis))
    
    st.divider()
    g_cat = df_gastos.groupby("Categoria")["Monto"].sum().reset_index()
    res = pd.merge(df_presupuesto, g_cat, on="Categoria", how="left").fillna(0)
    res["Disponible"] = res["Monto_Mensual"] - res["Monto"]
    for c in ["Monto_Mensual", "Monto", "Disponible"]: res[c] = res[c].apply(formatear_punto)
    st.table(res)

# --- TAB 4: EDITAR TODO ---
with tabs[4]:
    df_ed_view = df_gastos_raw.copy()
    df_ed_view['Fecha'] = df_ed_view['Fecha'].dt.strftime("%Y-%m-%d")
    df_ed = st.data_editor(df_ed_view, num_rows="dynamic", use_container_width=True)
    if st.button("Guardar Cambios Maestros"):
        conn.update(worksheet="Gastos", data=df_ed)
        st.cache_data.clear()
        st.rerun()
