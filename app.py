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

# Normalización de fechas de gastos
df_gastos_raw['Fecha'] = pd.to_datetime(df_gastos_raw['Fecha'], errors='coerce').dt.normalize()
df_gastos_raw = df_gastos_raw.dropna(subset=['Fecha'])

# --- LÓGICA DE TIEMPO REAL ---
hoy = datetime.now()

# Sidebar de Control Temporal
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

# --- TAB 0: PLANIFICACIÓN ---
with tabs[0]:
    st.header(f"📅 Planificación Mensual")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💰 Ingresos Base para Proporcionalidad")
        s_agustin = st.number_input("Sueldo Agustín ($)", value=5200000, step=50000)
        s_laura = st.number_input("Sueldo Laura ($)", value=2900000, step=50000)
        
        # Recálculo instantáneo en memoria
        total_sueldos = s_agustin + s_laura
        p_agustin = s_agustin / total_sueldos if total_sueldos > 0 else 0.5
        p_laura = s_laura / total_sueldos if total_sueldos > 0 else 0.5

    with col2:
        st.subheader("📊 Porcentaje de Participación")
        st.metric("Participación Agustín", f"{p_agustin*100:.2f} %")
        st.metric("Participación Laura", f"{p_laura*100:.2f} %")

    st.divider()
    
    # Parámetros variables del mes (UF y montos de deudas en UF)
    st.subheader("⚙️ Parámetros y Deudas del Mes")
    c_uf, c_uf_hipo, c_uf_dede = st.columns(3)
    with c_uf:
        col_uf = st.number_input("Valor UF del día:", value=39796.31, step=0.1, format="%.2f")
    with c_uf_hipo:
        uf_hipotecario = st.number_input("Monto Hipotecario (UF):", value=20.77, step=0.01, format="%.2f")
    with c_uf_dede:
        uf_dede = st.number_input("Monto DEDE (UF):", value=15.18, step=0.01, format="%.2f")
    
    # Cuota DEDE dinámica (Base Marzo 2026 = 35)
    meses_dif = (anio_sel - 2026) * 12 + (mes_sel_num - 3)
    cuota_actual = 35 + meses_dif
    
    # Cálculos de Aportes dinámicos
    hipo_t = uf_hipotecario * col_uf
    dede_t = uf_dede * col_uf
    bipers_t = df_presupuesto["Monto_Mensual"].sum()
    
    hipo_a, hipo_l = hipo_t * p_agustin, hipo_t * p_laura
    dede_a, dede_l = dede_t * 0.5, dede_t * 0.5  # Mantiene acuerdo 50/50
    bipers_a, bipers_l = bipers_t * p_agustin, bipers_t * p_laura
    
    total_a, total_l = hipo_a + dede_a + bipers_a, hipo_l + dede_l + bipers_l
    total_deposito = total_a + total_l

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Aporte Agustín", formatear_punto(total_a))
    m2.metric("Aporte Laura", formatear_punto(total_l))
    m3.metric("Total Mes", formatear_punto(total_deposito))
    
    st.divider()
    
    if st.button("🚀 Iniciar este Mes (Cargar Créditos Agustín)"):
        fecha_ini = datetime(anio_sel, mes_sel_num, 1).strftime("%Y-%m-%d")
        deudas = pd.DataFrame([
            {"Fecha": fecha_ini, "Categoria": "Hipotecario", "Monto": hipo_t, "Descripcion": f"Dividendo ({uf_hipotecario} UF)", "Usuario": "Agustín", "Retirado": "No"},
            {"Fecha": fecha_ini, "Categoria": "DEDE", "Monto": dede_t, "Descripcion": f"Cuota {cuota_actual} ({uf_dede} UF)", "Usuario": "Agustín", "Retirado": "No"}
        ])
        df_subir = pd.concat([df_gastos_raw, deudas], ignore_index=True)
        df_subir['Fecha'] = pd.to_datetime(df_subir['Fecha']).dt.strftime('%Y-%m-%d')
        conn.update(worksheet="Gastos", data=df_subir)
        st.cache_data.clear()
        st.rerun()

    st.subheader("📊 Detalle de Transferencia")
    detalle = pd.DataFrame({
        "Ítem": [f"Hipotecario ({uf_hipotecario} UF)", f"DEDE ({uf_dede} UF)", "Presupuesto Casa"],
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

# --- TAB 1: REGISTRO ---
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

# --- TAB 2: CONCILIAR ---
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
    st.subheader("📊 Resumen de Proporcionalidad Aplicada")
    df_resumen_sueldos = pd.DataFrame({
        "Usuario": ["Agustín", "Laura"],
        "Sueldo Declarado": [formatear_punto(s_agustin), formatear_punto(s_laura)],
        "% de Participación": [f"{p_agustin*100:.2f} %", f"{p_laura*100:.2f} %"]
    })
    st.table(df_resumen_sueldos)
    st.divider()

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
