import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_gsheets import GSheetsConnection

COLUMNAS = ["fecha", "concepto", "categoria", "monto"]
CATEGORIAS = ["Comida", "Combustible", "Alquiler", "Expensas", "Internet", "Salidas", "Otros"]


def hoy():
    """Fecha de hoy en Argentina (el servidor online usa otra zona horaria)."""
    return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()


def formato(n):
    """Formato argentino: $1.000.000"""
    return f"${n:,.0f}".replace(",", ".")


def pedir_clave():
    if st.session_state.get("autenticado"):
        return
    clave = st.text_input("Contraseña", type="password")
    if clave:
        if clave == st.secrets["clave_app"]:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")
    st.stop()


conn = st.connection("gsheets", type=GSheetsConnection)


def cargar_gastos():
    df = conn.read(ttl=0).reindex(columns=COLUMNAS).dropna(how="all")
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["monto"] = pd.to_numeric(df["monto"])
    return df


def agregar_gasto(df, concepto, categoria, monto, fecha):
    nuevo = pd.DataFrame([{
        "fecha": fecha, "concepto": concepto, "categoria": categoria, "monto": monto
    }])
    df = pd.concat([df, nuevo], ignore_index=True)
    df["fecha"] = pd.to_datetime(df["fecha"])
    guardar = df.copy()
    guardar["fecha"] = guardar["fecha"].dt.strftime("%Y-%m-%d")
    conn.update(data=guardar)
    return df


def totales_por_categoria(df):
    return df.groupby("categoria")["monto"].sum().sort_values(ascending=False)


# --- APP ---
st.title("Control de gastos")
st.markdown("""
<style>
    /* Texto general más grande */
    html, body, [class*="css"] { font-size: 30px !important; }

    /* Título principal */
    h1 { font-size: 40px !important; }

    /* Pestañas (Cargar gasto / Gastos del día / Acumulado) */
    button[data-baseweb="tab"] p { font-size: 30px !important; }

    /* Etiquetas de los campos (Concepto, Categoría, Monto, Fecha) */
    label p { font-size: 30px !important; }

    /* Campos de texto, número y select */
    input, textarea, .stSelectbox div, .stNumberInput input { font-size: 30px !important; }

    /* Botón Agregar */
    button[kind="secondaryFormSubmit"] p, button[kind="primary"] p { font-size: 30px !important; }

    /* Números grandes (Gasto total del día, Acumulado) */
    [data-testid="stMetricValue"] { font-size: 60px !important; }
    [data-testid="stMetricLabel"] { font-size: 25px !important; }
</style>
""", unsafe_allow_html=True)
pedir_clave()
df = cargar_gastos()

tab1, tab2, tab3 = st.tabs(["Cargar gasto", "Gastos del día", "Acumulado"])

with tab1:
    with st.form("nuevo_gasto", clear_on_submit=True):
        concepto = st.text_input("Concepto")
        categoria = st.selectbox("Categoría", CATEGORIAS)
        monto = st.number_input(
            "Monto ($)", min_value=0.0, value=None, step=1000.0, placeholder="Ej: 30000"
        )
        fecha = st.date_input("Fecha", value=hoy())
        if st.form_submit_button("Agregar"):
            if not concepto or monto is None:
                st.warning("Completá el concepto y el monto.")
            else:
                df = agregar_gasto(df, concepto, categoria, monto, fecha)
                st.success(f"Gasto de {concepto} agregado")

with tab2:
    del_dia = df[df["fecha"].dt.date == hoy()]
    if del_dia.empty:
        st.info("Todavía no cargaste gastos hoy.")
    else:
        for cat, total in totales_por_categoria(del_dia).items():
            st.write(f"**{cat}:** {formato(total)}")
        st.metric("Gasto total del día", formato(del_dia["monto"].sum()))

with tab3:
    if df.empty:
        st.info("No hay gastos cargados.")
    else:
        st.metric("Gasto total acumulado", formato(df["monto"].sum()))
        st.bar_chart(totales_por_categoria(df))
        st.dataframe(df.sort_values("fecha", ascending=False))
