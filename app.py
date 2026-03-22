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

st.title("🏠 Gestión de Gastos y Balance")

tabs = st.tabs(["🚀 Planificación", "➕ Registrar", "🏦 Conciliar", "📊 Balance y Resumen", "⚙️ Editar"])

# --- TAB 0: PLANIFICACIÓN (Calcula Aportes) ---
with tabs[0]:
    st.header(f"📅 Planificación - {datetime.now().strftime('%B %Y')}")
    col_uf, col_cuota = st.columns(2)
    with col_uf:
        uf_val = st.number_input("UF del día 1:", value=39796.31, step=0.1, format="%.2f")
    
    # Cálculos UF
    hipo_t = 20.77 * uf_val
    dede_t = 15.18 * uf_val
    bipers_t = df_presupuesto["Monto_Mensual"].sum()
    
    # Totales por persona
    total_a = (hipo_t * 0.748) + (dede_t * 0.5) + (bipers_t * 0.858)
    total_l = (hipo_t * 0.252) + (dede_t * 0.5) + (bipers_t * 0.142)
    total_deposito = total_a + total_l

    c1, c2, c3 = st.columns(3)
    c1.metric("Aporte Agustín", formatear_punto(total_a))
    c2.metric("Aporte Laura", formatear_punto(total_l))
    c3.metric("Total a Depositar", formatear_punto(total_deposito))

    if st.button("🚀 Iniciar Mes: Cargar Deudas y Presupuesto en Gastos"):
        # Esta función crea los registros de deuda en la hoja de Gastos como pendientes
        deudas = pd.DataFrame([
            {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Categoria": "Hipotecario", "Monto": hipo_t, "Descripcion": "Pago UF Mes", "Usuario": "Bipersonal", "Retirado": "No"},
            {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Categoria": "DEDE", "Monto": dede_t, "Descripcion": f"Cuota {35+(datetime.now().month-3)}", "Usuario": "Bipersonal", "Retirado": "No"}
        ])
        df_actualizado = pd.concat([df_gastos_raw, deudas], ignore_index=True)
        conn.update(worksheet="Gastos", data=df_actualizado)
        st.success("✅ Deudas cargadas en lista de conciliación.")
        st.rerun()

    with st.expander("🔍 Configurar Presupuesto Casa"):
        df_pres_edit = st.data_editor(df_presupuesto, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("Guardar Estructura"):
            conn.update(worksheet="Presupuesto", data=df_pres_edit.dropna(subset=["Categoria"]))
            st.rerun()

# --- TAB 3: BALANCE Y RESUMEN (TU SOLICITUD) ---
with tabs[3]:
    st.header("💰 Balance de Cuenta Bipersonal")
    
    # Lógica de Balance:
    # 1. Depósito Total esperado (Lo que entró al inicio del mes)
    # 2. Monto ya retirado (Lo que dice "Sí" en el Excel)
    # 3. Monto por retirar (Lo que dice "No" en el Excel)
    
    monto_ya_retirado = df_gastos[df_gastos['Retirado'] == 'Sí']['Monto'].sum()
    monto_por_retirar = df_gastos[df_gastos['Retirado'] == 'No']['Monto'].sum()
    
    # El saldo que DEBERÍA haber en el banco ahora mismo
    saldo_en_banco = total_deposito - monto_ya_retirado
    # Lo que quedará después de pagar todo lo pendiente
    saldo_final_disponible = saldo_en_banco - monto_por_retirar

    colb1, colb2, colb3 = st.columns(3)
    colb1.metric("Saldo actual en Banco", formatear_punto(saldo_en_banco))
    colb2.metric("Pendiente por Retirar", formatear_punto(monto_por_retirar), delta_color="inverse")
    colb3.metric("Saldo Final Disponible", formatear_punto(saldo_final_disponible))

    st.divider()
    st.subheader("Estado por Categoría de Presupuesto")
    res = pd.merge(df_presupuesto, df_gastos.groupby("Categoria")["Monto"].sum().reset_index(), on="Categoria", how="left").fillna(0)
    res["Disponible"] = res["Monto_Mensual"] - res["Monto"]
    res_v = res.copy()
    for c in ["Monto_Mensual", "Monto", "Disponible"]: res_v[c] = res_v[c].apply(formatear_punto)
    st.table(res_v)

# --- LAS DEMÁS PESTAÑAS (MANTIENEN LÓGICA) ---
with tabs[1]: # Registrar
    with st.form("f_g"):
        f, cat = st.date_input("Fecha"), st.selectbox("Cat", df_presupuesto["Categoria"].unique())
        m, u = st.number_input("Monto", step=1000), st.radio("Usuario", ["Agustín", "Laura"])
        if st.form_submit_button("Guardar"):
            n = pd.DataFrame([{"Fecha": f.strftime("%Y-%m-%d"), "Categoria": cat, "Monto": m, "Usuario": u, "Retirado": "No"}])
            conn.update(worksheet="Gastos", data=pd.concat([df_gastos_raw, n], ignore_index=True)); st.rerun()

with tabs[2]: # Conciliar
    pend = df_gastos[df_gastos['Retirado'] == 'No'].copy()
    if not pend.empty:
        pend["Monto_V"], pend["Check"] = pend["Monto"].apply(formatear_punto), False
        ed = st.data_editor(pend[["Fecha", "Categoria", "Monto_V", "Check"]], use_container_width=True, hide_index=True)
        if st.button("Confirmar Retiros"):
            sel = ed[ed["Check"] == True].index
            df_gastos.loc[pend.index[sel], 'Retirado'] = 'Sí'
            conn.update(worksheet="Gastos", data=df_gastos); st.rerun()
    else: st.info("Todo al día.")

with tabs[4]: # Editar
    df_ed = st.data_editor(df_gastos, num_rows="dynamic", use_container_width=True)
    if st.button("Guardar"): conn.update(worksheet="Gastos", data=df_ed); st.rerun()
