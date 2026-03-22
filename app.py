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

# Carga de datos
df_presupuesto = conn.read(worksheet="Presupuesto", ttl="0")
df_gastos_raw = conn.read(worksheet="Gastos", ttl="0")
df_gastos = df_gastos_raw.copy()

st.title("🏠 Gestión de Gastos y Planificación")

tabs = st.tabs(["🚀 Planificación", "➕ Registrar", "🏦 Conciliar", "📊 Balance y Resumen", "⚙️ Editar"])

# --- TAB 0: PLANIFICACIÓN MENSUAL ---
with tabs[0]:
    st.header(f"📅 Planificación - {datetime.now().strftime('%B %Y')}")
    
    col_uf, col_cuota = st.columns(2)
    with col_uf:
        # UF editable, por defecto la de marzo 2026 según tu dato
        uf_val = st.number_input("UF del día 1 del mes:", value=39796.31, step=0.1, format="%.2f")
    
    # Cálculo de cuota DEDE automática (Marzo 2026 = 35)
    mes_actual = datetime.now().month
    cuota_actual = 35 + (mes_actual - 3)
    
    # 1. Cálculos de Deudas UF y Presupuesto
    hipo_total = 20.77 * uf_val
    dede_total = 15.18 * uf_val
    bipers_total = df_presupuesto["Monto_Mensual"].sum()
    
    # 2. Proporciones exactas
    hipo_a, hipo_l = hipo_total * 0.748, hipo_total * 0.252
    dede_a, dede_l = dede_total * 0.5, dede_total * 0.5
    bipers_a, bipers_l = bipers_total * 0.858, bipers_total * 0.142
    
    total_a = hipo_a + dede_a + bipers_a
    total_l = hipo_l + dede_l + bipers_l
    total_deposito = total_a + total_l

    # Métricas de Aporte
    c1, c2, c3 = st.columns(3)
    c1.metric("Aporte Agustín", formatear_punto(total_a))
    c2.metric("Aporte Laura", formatear_punto(total_l))
    c3.metric("Total a Depositar", formatear_punto(total_deposito))
    
    st.divider()
    
    # Botón para cargar deudas al sistema de conciliación
    if st.button("🚀 Iniciar Mes: Cargar Deudas en Gastos"):
        deudas = pd.DataFrame([
            {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Categoria": "Hipotecario", "Monto": hipo_total, "Descripcion": "Dividendo Mes", "Usuario": "Bipersonal", "Retirado": "No"},
            {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Categoria": "DEDE", "Monto": dede_total, "Descripcion": f"Cuota {cuota_actual}", "Usuario": "Bipersonal", "Retirado": "No"}
        ])
        conn.update(worksheet="Gastos", data=pd.concat([df_gastos_raw, deudas], ignore_index=True))
        st.success("✅ Hipotecario y DEDE cargados como pendientes.")
        st.rerun()

    # DETALLE DE TRANSFERENCIA (Lo que me pediste recuperar)
    st.subheader("📊 Detalle de Transferencia")
    detalle = pd.DataFrame({
        "Ítem": ["🏠 Hipotecario (20.77 UF)", "📑 DEDE (15.18 UF)", "🧾 Presupuesto Casa"],
        "Total": [formatear_punto(hipo_total), formatear_punto(dede_total), formatear_punto(bipers_total)],
        "Agustín": [formatear_punto(hipo_a), formatear_punto(dede_a), formatear_punto(bipers_a)],
        "Laura": [formatear_punto(hipo_l), formatear_punto(dede_l), formatear_punto(bipers_l)]
    })
    st.table(detalle)

    # MENSAJE DEDE
    st.info(f"📝 **Mensaje DEDE:**\n\nRepertorio 2497 del 2023 OT 786773 deuda Karen Andrea cuota {cuota_actual}")

    # EDITABLE DEL PRESUPUESTO
    with st.expander("🔍 Gestionar Categorías y Montos del Presupuesto"):
        df_pres_edit = st.data_editor(df_presupuesto, column_config={"Monto_Mensual": st.column_config.NumberColumn("Monto ($)", format="$ %d")}, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("Guardar Estructura Presupuesto"):
            conn.update(worksheet="Presupuesto", data=df_pres_edit.dropna(subset=["Categoria"]))
            st.rerun()

# --- TAB 3: BALANCE (Cálculo dinámico de caja) ---
with tabs[3]:
    st.header("💰 Balance de Cuenta Bipersonal")
    monto_ya_retirado = df_gastos[df_gastos['Retirado'] == 'Sí']['Monto'].sum()
    monto_por_retirar = df_gastos[df_gastos['Retirado'] == 'No']['Monto'].sum()
    
    saldo_en_banco = total_deposito - monto_ya_retirado
    saldo_final_disponible = saldo_en_banco - monto_por_retirar

    cb1, cb2, cb3 = st.columns(3)
    cb1.metric("Saldo actual en Banco", formatear_punto(saldo_en_banco))
    cb2.metric("Pendiente por Retirar", formatear_punto(monto_por_retirar))
    cb3.metric("Saldo Final Disponible", formatear_punto(saldo_final_disponible))

    st.divider()
    res = pd.merge(df_presupuesto, df_gastos.groupby("Categoria")["Monto"].sum().reset_index(), on="Categoria", how="left").fillna(0)
    res["Disponible"] = res["Monto_Mensual"] - res["Monto"]
    res_v = res.copy()
    for c in ["Monto_Mensual", "Monto", "Disponible"]: res_v[c] = res_v[c].apply(formatear_punto)
    st.table(res_v)

# --- LAS DEMÁS PESTAÑAS (MANTIENEN FUNCIONALIDAD) ---
with tabs[1]: # Registrar
    with st.form("f_g"):
        f, cat = st.date_input("Fecha"), st.selectbox("Cat", df_presupuesto["Categoria"].unique())
        m, u = st.number_input("Monto", step=1000), st.radio("Usuario", ["Agustín", "Laura"])
        d = st.text_input("Nota")
        if st.form_submit_button("Guardar"):
            n = pd.DataFrame([{"Fecha": f.strftime("%Y-%m-%d"), "Categoria": cat, "Monto": m, "Descripcion": d, "Usuario": u, "Retirado": "No"}])
            conn.update(worksheet="Gastos", data=pd.concat([df_gastos_raw, n], ignore_index=True)); st.rerun()

with tabs[2]: # Conciliar
    pend = df_gastos[df_gastos['Retirado'] == 'No'].copy()
    if not pend.empty:
        pend["Monto_V"], pend["Check"] = pend["Monto"].apply(formatear_punto), False
        ed = st.data_editor(pend[["Fecha", "Categoria", "Monto_V", "Usuario", "Check"]], use_container_width=True, hide_index=True)
        if st.button("Confirmar Retiros"):
            sel = ed[ed["Check"] == True].index
            df_gastos.loc[pend.index[sel], 'Retirado'] = 'Sí'
            conn.update(worksheet="Gastos", data=df_gastos); st.rerun()
    else: st.info("Todo al día.")

with tabs[4]: # Editar
    df_ed = st.data_editor(df_gastos, num_rows="dynamic", use_container_width=True)
    if st.button("Guardar Cambios"): conn.update(worksheet="Gastos", data=df_ed); st.rerun()
