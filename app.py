import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gastos Familia", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def formatear_punto(valor):
    return f"$ {int(valor):,}".replace(",", ".")

# Carga de datos
df_presupuesto = conn.read(worksheet="Presupuesto", ttl="5m")
df_gastos_raw = conn.read(worksheet="Gastos", ttl="0")
df_gastos = df_gastos_raw.copy()

st.title("🏠 Gestión de Gastos y Planificación")

tabs = st.tabs(["🚀 Planificación", "➕ Registrar", "🏦 Conciliar", "📊 Resumen", "⚙️ Editar"])

# --- TAB 0: PLANIFICACIÓN MENSUAL ---
with tabs[0]:
    st.header(f"📅 Planificación - {datetime.now().strftime('%B %Y')}")
    
    col_uf, col_cuota = st.columns(2)
    with col_uf:
        uf_val = st.number_input("UF del día 1 del mes:", value=39796.31, step=0.1, format="%.2f")
    
    # Cálculo de cuota DEDE: Marzo 2026 (mes 3) es cuota 35. 
    # Fórmula: 35 + (mes_actual - 3)
    mes_actual = datetime.now().month
    cuota_actual = 35 + (mes_actual - 3)
    
    # 1. Cálculos de Deudas UF
    hipo_total = 20.77 * uf_val
    dede_total = 15.18 * uf_val
    
    # 2. Cálculo Gastos Bipersonal (del presupuesto)
    bipers_total = df_presupuesto["Monto_Mensual"].sum()
    
    # 3. Aplicación de Proporciones
    # Hipotecario (A: 74.8%, L: 25.2%)
    hipo_a, hipo_l = hipo_total * 0.748, hipo_total * 0.252
    # DEDE (50/50)
    dede_a, dede_l = dede_total * 0.5, dede_total * 0.5
    # Bipersonal (A: 85.8%, L: 14.2%)
    bipers_a, bipers_l = bipers_total * 0.858, bipers_total * 0.142
    
    total_a = hipo_a + dede_a + bipers_a
    total_l = hipo_l + dede_l + bipers_l

    # Visualización de Resultados
    c1, c2 = st.columns(2)
    c1.metric("Aporte Agustín", formatear_punto(total_a))
    c2.metric("Aporte Laura", formatear_punto(total_l))
    
    st.divider()
    st.subheader("Detalle de Transferencia")
    detalle = pd.DataFrame({
        "Ítem": ["🏠 Hipotecario (20.77 UF)", "📑 DEDE (15.18 UF)", "🧾 Presupuesto Casa"],
        "Total": [formatear_punto(hipo_total), formatear_punto(dede_total), formatear_punto(bipers_total)],
        "Agustín": [formatear_punto(hipo_a), formatear_punto(dede_a), formatear_punto(bipers_a)],
        "Laura": [formatear_punto(hipo_l), formatear_punto(dede_l), formatear_punto(bipers_l)]
    })
    st.table(detalle)
    
    st.info(f"📝 **Mensaje DEDE:**\n\nRepertorio 2497 del 2023 OT 786773 deuda Karen Andrea cuota {cuota_actual}")

# --- TAB 1: REGISTRO ---
with tabs[1]:
    with st.form("f_gasto", clear_on_submit=True):
        f = st.date_input("Fecha")
        cat = st.selectbox("Categoría", df_presupuesto["Categoria"].unique())
        m = st.number_input("Monto", min_value=0, step=1000)
        u = st.radio("Usuario", ["Agustín", "Laura"], horizontal=True)
        d = st.text_input("Nota")
        if st.form_submit_button("Guardar"):
            n = pd.DataFrame([{"Fecha": f.strftime("%Y-%m-%d"), "Categoria": cat, "Monto": m, "Descripcion": d, "Usuario": u, "Retirado": "No"}])
            conn.update(worksheet="Gastos", data=pd.concat([df_gastos_raw, n], ignore_index=True))
            st.rerun()

# --- TAB 2: CONCILIAR ---
with tabs[2]:
    pend = df_gastos[df_gastos['Retirado'] == 'No'].copy()
    if not pend.empty:
        pend["Monto_V"] = pend["Monto"].apply(formatear_punto)
        pend["Check"] = False
        ed = st.data_editor(pend[["Fecha", "Categoria", "Monto_V", "Usuario", "Check"]], use_container_width=True, hide_index=True)
        if st.button("Confirmar Retiros"):
            sel = ed[ed["Check"] == True].index
            df_gastos.loc[pend.index[sel], 'Retirado'] = 'Sí'
            conn.update(worksheet="Gastos", data=df_gastos)
            st.rerun()
    else: st.info("Sin pendientes.")

# --- TAB 3: RESUMEN ---
with tabs[3]:
    st.metric("Pendiente Bipersonal", formatear_punto(df_gastos[df_gastos['Retirado'] == 'No']['Monto'].sum()))
    res = pd.merge(df_presupuesto, df_gastos.groupby("Categoria")["Monto"].sum().reset_index(), on="Categoria", how="left").fillna(0)
    res["Disponible"] = res["Monto_Mensual"] - res["Monto"]
    for c in ["Monto_Mensual", "Monto", "Disponible"]: res[c] = res[c].apply(formatear_punto)
    st.table(res)

# --- TAB 4: EDITAR ---
with tabs[4]:
    df_ed = st.data_editor(df_gastos, num_rows="dynamic", use_container_width=True)
    if st.button("Guardar Cambios"):
        conn.update(worksheet="Gastos", data=df_ed)
        st.rerun()
