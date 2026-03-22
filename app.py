import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuración de página e interfaz
st.set_page_config(page_title="Gastos Familia", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def formatear_punto(valor):
    try:
        return f"$ {int(valor):,}".replace(",", ".")
    except:
        return "$ 0"

# CARGA INMEDIATA (Sin caché)
df_presupuesto = conn.read(worksheet="Presupuesto", ttl="0")
df_gastos_raw = conn.read(worksheet="Gastos", ttl="0")
df_gastos = df_gastos_raw.copy()

if 'Retirado' not in df_gastos.columns:
    df_gastos['Retirado'] = 'No'

st.title("🏠 Gestión de Gastos y Planificación")

tabs = st.tabs(["🚀 Planificación", "➕ Registrar", "🏦 Conciliar", "📊 Balance y Resumen", "⚙️ Editar"])

# --- TAB 0: PLANIFICACIÓN MENSUAL ---
with tabs[0]:
    st.header(f"📅 Planificación - {datetime.now().strftime('%B %Y')}")
    col_uf = st.number_input("UF del día 1 del mes:", value=39796.31, step=0.1, format="%.2f")
    
    mes_actual = datetime.now().month
    cuota_actual = 35 + (mes_actual - 3)
    
    # 1. Cálculos Base
    hipo_total = 20.77 * col_uf
    dede_total = 15.18 * col_uf
    bipers_total = df_presupuesto["Monto_Mensual"].sum()
    
    # 2. Proporciones
    hipo_a, hipo_l = hipo_total * 0.748, hipo_total * 0.252
    dede_a, dede_l = dede_total * 0.5, dede_total * 0.5
    bipers_a, bipers_l = bipers_total * 0.858, bipers_total * 0.142
    
    total_a = hipo_a + dede_a + bipers_a
    total_l = hipo_l + dede_l + bipers_l
    total_deposito = total_a + total_l

    c1, c2, c3 = st.columns(3)
    c1.metric("Aporte Agustín", formatear_punto(total_a))
    c2.metric("Aporte Laura", formatear_punto(total_l))
    c3.metric("Total a Depositar", formatear_punto(total_deposito))
    
    st.divider()
    
    if st.button("🚀 Iniciar Mes: Cargar Deudas en Gastos"):
        deudas = pd.DataFrame([
            {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Categoria": "Hipotecario", "Monto": hipo_total, "Descripcion": "Dividendo (Cuota Flexible)", "Usuario": "Bipersonal", "Retirado": "No"},
            {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Categoria": "DEDE", "Monto": dede_total, "Descripcion": f"Cuota {cuota_actual}", "Usuario": "Bipersonal", "Retirado": "No"}
        ])
        conn.update(worksheet="Gastos", data=pd.concat([df_gastos_raw, deudas], ignore_index=True))
        st.cache_data.clear()
        st.rerun()

    st.subheader("📊 Detalle de Transferencia")
    detalle = pd.DataFrame({
        "Ítem": ["🏠 Hipotecario", "📑 DEDE", "🧾 Presupuesto Casa"],
        "Total": [formatear_punto(hipo_total), formatear_punto(dede_total), formatear_punto(bipers_total)],
        "Agustín": [formatear_punto(hipo_a), formatear_punto(dede_a), formatear_punto(bipers_a)],
        "Laura": [formatear_punto(hipo_l), formatear_punto(dede_l), formatear_punto(bipers_l)]
    })
    st.table(detalle)
    st.info(f"📝 **Mensaje DEDE:** Repertorio 2497 del 2023 OT 786773 deuda Karen Andrea cuota {cuota_actual}")

    with st.expander("🔍 Gestionar Categorías y Montos del Presupuesto"):
        df_pres_edit = st.data_editor(df_presupuesto, column_config={"Monto_Mensual": st.column_config.NumberColumn("Monto ($)", format="$ %d")}, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("Guardar Estructura"):
            conn.update(worksheet="Presupuesto", data=df_pres_edit.dropna(subset=["Categoria"]))
            st.cache_data.clear()
            st.rerun()

# --- TAB 1: REGISTRAR ---
with tabs[1]:
    with st.form("f_reg", clear_on_submit=True):
        f = st.date_input("Fecha", value=datetime.now())
        cat = st.selectbox("Categoría", df_presupuesto["Categoria"].unique())
        m = st.number_input("Monto", min_value=0, step=1000)
        u = st.radio("Pagado por", ["Agustín", "Laura"], horizontal=True)
        d = st.text_input("Nota")
        if st.form_submit_button("Guardar Gasto"):
            n = pd.DataFrame([{"Fecha": f.strftime("%Y-%m-%d"), "Categoria": cat, "Monto": m, "Descripcion": d, "Usuario": u, "Retirado": "No"}])
            conn.update(worksheet="Gastos", data=pd.concat([df_gastos_raw, n], ignore_index=True))
            st.cache_data.clear()
            st.rerun()

# --- TAB 2: CONCILIAR (Editable para Cuota Flexible) ---
with tabs[2]:
    st.subheader("Pendientes de retiro")
    df_pend = df_gastos[df_gastos['Retirado'] == 'No'].copy()
    if not df_pend.empty:
        df_pend["Confirmar"] = False
        ed_puntos = st.data_editor(
            df_pend[["Fecha", "Categoria", "Monto", "Descripcion", "Confirmar"]],
            column_config={
                "Monto": st.column_config.NumberColumn("Monto ($)", format="$ %d"),
                "Confirmar": st.column_config.CheckboxColumn("¿Retirar?", default=False)
            },
            disabled=["Fecha", "Categoria", "Descripcion"],
            use_container_width=True, hide_index=True, key="ed_concilia"
        )
        if st.button("Confirmar y Actualizar Balance"):
            for i, row in ed_puntos.iterrows():
                real_idx = df_pend.index[i]
                df_gastos.at[real_idx, "Monto"] = row["Monto"]
                if row["Confirmar"]: df_gastos.at[real_idx, "Retirado"] = "Sí"
            conn.update(worksheet="Gastos", data=df_gastos)
            st.cache_data.clear()
            st.rerun()
    else: st.info("Sin retiros pendientes.")

# --- TAB 3: BALANCE ---
with tabs[3]:
    m_ya = df_gastos[df_gastos['Retirado'] == 'Sí']['Monto'].sum()
    m_po = df_gastos[df_gastos['Retirado'] == 'No']['Monto'].sum()
    s_ba = total_deposito - m_ya
    s_fi = s_ba - m_po
    cb1, cb2, cb3 = st.columns(3)
    cb1.metric("Saldo actual en Banco", formatear_punto(s_ba))
    cb2.metric("Pendiente por Retirar", formatear_punto(m_po))
    cb3.metric("Saldo Final Disponible", formatear_punto(s_fi))
    
    st.divider()
    res = pd.merge(df_presupuesto, df_gastos.groupby("Categoria")["Monto"].sum().reset_index(), on="Categoria", how="left").fillna(0)
    res["Disponible"] = res["Monto_Mensual"] - res["Monto"]
    res_v = res.copy()
    for c in ["Monto_Mensual", "Monto", "Disponible"]: res_v[c] = res_v[c].apply(formatear_punto)
    st.table(res_v)

# --- TAB 4: EDICIÓN MAESTRA ---
with tabs[4]:
    df_ed = st.data_editor(df_gastos, num_rows="dynamic", use_container_width=True)
    if st.button("Guardar Cambios Maestros"):
        conn.update(worksheet="Gastos", data=df_ed)
        st.cache_data.clear()
        st.rerun()
