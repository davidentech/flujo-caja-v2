import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import tempfile
import re
from dateutil import parser

TABLE_SETTINGS = {
    "flavor": "lattice",
    "strip_text": "\n"
}

def extract_bank_data(pdf_path):
    import camelot
    try:
        tables = camelot.read_pdf(
            pdf_path, 
            pages="all",
            **TABLE_SETTINGS
        )
        if len(tables) > 0:
            full_df = pd.concat([table.df for table in tables])
            clean_df = full_df[~full_df[0].str.contains("FECHA|DESCRIPCIÓN", na=False)]
            return clean_df
        else:
            st.error("No se pudieron detectar tablas en el PDF. Intente con otro archivo.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al procesar el PDF: {str(e)}")
        return pd.DataFrame()

def process_transactions(raw_df):
    if raw_df.empty:
        return pd.DataFrame()
    try:
        raw_df.columns = ["Fecha", "Descripción", "Sucursal", "Doc", "Valor", "Saldo"]
        # Convertir fechas solo si son válidas, usando errors='coerce'
        raw_df["Fecha"] = pd.to_datetime(raw_df["Fecha"], dayfirst=True, errors='coerce')
        raw_df = raw_df.dropna(subset=["Fecha"])
        currency_cols = ["Valor", "Saldo"]
        for col in currency_cols:
            if col in raw_df.columns:
                raw_df[col] = raw_df[col].astype(str).str.replace(r"[^\d\-.,]", "", regex=True)
                raw_df[col] = raw_df[col].str.replace(",", "").astype(float)
        patterns = {
            "Ingresos": r"PAGO INTERBANC|ABONO|DEPÓSITO|NÓMINA|TRANSFERENCIA A FAVOR",
            "Egresos": r"IMPUESTO|COMISIÓN|RETIRO|PAGO A PROVE|TRANSFERENCIA",
            "Servicios": r"CUOTA MANEJO|SEGUROS|TARJETA|AGUA|LUZ|GAS"
        }
        if "Descripción" in raw_df.columns:
            raw_df["Categoría"] = raw_df["Descripción"].apply(
                lambda x: next((k for k, v in patterns.items() if re.search(v, str(x))), "Otros")
            )
        raw_df["Ingresos"] = np.where(raw_df["Valor"] > 0, raw_df["Valor"], 0)
        raw_df["Egresos"] = np.where(raw_df["Valor"] < 0, abs(raw_df["Valor"]), 0)
        raw_df["Flujo Neto"] = raw_df["Valor"]
        raw_df = raw_df.sort_values("Fecha")
        raw_df["Saldo Acumulado"] = raw_df["Saldo"]
        return raw_df
    except Exception as e:
        st.error(f"Error al procesar las transacciones: {str(e)}")
        return pd.DataFrame()

def validate_balances(df):
    if df.empty or "Valor" not in df.columns or "Saldo" not in df.columns:
        return pd.DataFrame()
    calculated = df["Valor"].cumsum() + df["Saldo"].iloc[0] - df["Valor"].iloc[0]
    discrepancies = df[abs(calculated - df["Saldo"]) > 1]
    return discrepancies

def load_and_process_bank_statement(uploaded_file):
    if uploaded_file is not None:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            raw_data = extract_bank_data(tmp_path)
            processed_data = process_transactions(raw_data)
            os.unlink(tmp_path)
            if not processed_data.empty:
                discrepancies = validate_balances(processed_data)
                if not discrepancies.empty:
                    st.warning(f"Se encontraron {len(discrepancies)} registros con discrepancias en saldos. Puede afectar la precisión del análisis.")
                if "Fecha" in processed_data.columns and not processed_data["Fecha"].empty:
                    extracto_mes = processed_data["Fecha"].iloc[0].strftime("%B %Y")
                else:
                    extracto_mes = "Desconocido"
                processed_data["FechaStr"] = processed_data["Fecha"].dt.strftime("%Y-%m-%d")
                return processed_data, extracto_mes
            else:
                st.error("No se pudieron extraer datos válidos del extracto bancario.")
                return pd.DataFrame(), ""
        except Exception as e:
            st.error(f"Error procesando el extracto bancario: {str(e)}")
            return pd.DataFrame(), ""
    else:
        return pd.DataFrame(), ""

def cargar_datos_historicos():
    if not os.path.exists("datos_bancarios"):
        return pd.DataFrame()
    all_files = [os.path.join("datos_bancarios", f) for f in os.listdir("datos_bancarios") if f.endswith('.csv')]
    if not all_files:
        return pd.DataFrame()
    all_dfs = []
    for filename in all_files:
        try:
            df = pd.read_csv(filename)
            if "Fecha" in df.columns:
                df["Fecha"] = pd.to_datetime(df["Fecha"])
            all_dfs.append(df)
        except Exception as e:
            st.warning(f"Error al cargar {filename}: {str(e)}")
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=["Fecha", "Valor", "Descripción"])
        combined_df = combined_df.sort_values("Fecha")
        return combined_df
    else:
        return pd.DataFrame()

# Simulación de datos
def generar_datos():
    fechas = pd.date_range(datetime.today() - timedelta(days=30), periods=30)
    ingresos = pd.Series([round(x, 2) for x in np.random.uniform(200, 1500, size=30)])
    egresos = pd.Series([round(x, 2) for x in np.random.uniform(100, 1200, size=30)])
    df = pd.DataFrame({
        "Fecha": fechas,
        "Ingresos": ingresos,
        "Egresos": egresos,
    })
    df["Flujo Neto"] = df["Ingresos"] - df["Egresos"]
    df["Saldo Acumulado"] = df["Flujo Neto"].cumsum()
    return df

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Financiero", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="💰"
)

# Estilos CSS modernos - Fase 1
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    :root {
        --primary: #2563EB;
        --primary-light: #3B82F6;
        --secondary: #22C55E;
        --secondary-light: #4ADE80;
        --background: #F7FAFC;
        --container: #FFFFFF;
        --text-main: #1A202C;
        --text-secondary: #64748B;
        --border: #E2E8F0;
        --success: #22C55E;
        --error: #EF4444;
        --warning: #FACC15;
    }

    /* Estilos generales */
    .main {
        background-color: var(--background) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-main);
        padding: 2rem;
    }

    [data-testid="stSidebar"] {
        background-color: var(--background) !important;
        color: var(--text-main) !important;
    }

    /* Asegurar que el contenedor principal tenga fondo claro */
    .stApp {
        background-color: var(--background) !important;
    }

    /* Asegurar que el contenedor de la barra lateral tenga fondo claro */
    section[data-testid="stSidebarContent"] {
        background-color: var(--background) !important;
        color: var(--text-main) !important;
    }

    /* Ajustar el color de texto para mejor contraste en fondo claro */
    .stMarkdown {
        color: var(--text-main) !important;
    }

    /* Asegurar que los encabezados tengan el color correcto en fondo claro */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-main) !important;
    }

    .sidebar .sidebar-content {
        background-color: var(--container) !important;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Headers */
    h1, h2, h3 {
        font-weight: 600;
        font-family: 'Inter', sans-serif;
    }

    h1 { font-size: 2rem; margin-bottom: 1rem; }
    h2 { font-size: 1.5rem; margin-bottom: 0.75rem; }
    h3 { font-size: 1.25rem; margin-bottom: 0.5rem; }

    /* Tarjetas métricas */
    .metric-card {
        background-color: var(--container);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid var(--border);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .metric-title {
        font-size: 0.875rem;
        color: var(--text-secondary);
        font-weight: 500;
        margin-bottom: 0.5rem;
    }

    .metric-value {
        font-size: 1.875rem;
        font-weight: 600;
        color: var(--text-main);
        line-height: 1.2;
    }

    /* Botones */
    .stButton>button {
        background-color: var(--primary) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.625rem 1.25rem !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }

    .stButton>button:hover {
        background-color: var(--primary-light) !important;
        box-shadow: 0 4px 6px rgba(37,99,235,0.1) !important;
    }

    /* Inputs y Selectbox */
    .stSelectbox [data-baseweb="select"], 
    .stDateInput > div {
        background-color: var(--container) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        transition: all 0.2s ease;
    }

    .stSelectbox [data-baseweb="select"]:focus-within,
    .stDateInput > div:focus-within {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 2px rgba(37,99,235,0.1) !important;
    }

    /* Contenedor de gráficos */
    .chart-container {
        background-color: var(--container);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid var(--border);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
    }

    /* Tabla de datos */
    .dataframe {
        width: 100% !important;
        background-color: var(--container) !important;
        border-radius: 8px !important;
        border: 1px solid var(--border) !important;
    }

    .dataframe th {
        background-color: var(--background) !important;
        color: var(--text-main) !important;
        font-weight: 600 !important;
        padding: 0.75rem 1rem !important;
        font-size: 0.875rem !important;
    }

    .dataframe td {
        padding: 0.75rem 1rem !important;
        font-size: 0.875rem !important;
        border-top: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
    }

    .dataframe tr:nth-child(even) {
        background-color: var(--background) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: none;
        color: var(--text-secondary);
        font-weight: 500;
        padding: 0.5rem 1rem;
        border-radius: 8px;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--primary) !important;
        color: white !important;
    }

    /* Balance card */
    .balance-card {
        background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary) 100%);
        color: white;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 4px 6px rgba(37,99,235,0.1);
    }

    .balance-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 1rem 0;
        color: #fff;
    }

    .balance-label {
        font-size: 1rem;
        opacity: 0.95;
        color: #fff;
    }

    .balance-secondary {
        color: rgba(255,255,255,0.85) !important;
        font-size: 1rem;
    }

    /* Eliminar la franja negra superior de Streamlit y unificar el fondo */
    header[data-testid="stHeader"] {
        background-color: var(--background) !important;
        box-shadow: none !important;
    }
    .st-emotion-cache-18ni7ap {
        background: var(--background) !important;
    }
    /* Ocultar la sombra o borde del header si existe */
    header[data-testid="stHeader"]::before {
        box-shadow: none !important;
        border: none !important;
    }
    /* Unificar color de fondo en toda la app */
    body, .stApp {
        background-color: var(--background) !important;
    }
    /* Ajustar el menú desplegable de Streamlit (kebab menu) */
    [data-testid="stDecoration"] {
        background-color: var(--background) !important;
    }
    /* Ajustar el color del texto del header */
    header[data-testid="stHeader"] * {
        color: var(--text-main) !important;
    }
    /* Solo textos, títulos y labels del sidebar en color oscuro */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] h6,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stText,
    [data-testid="stSidebar"] .st-bb,
    [data-testid="stSidebar"] .st-c3 {
        color: var(--text-main) !important;
    }
    /* Forzar color negro puro y opacidad total en los labels del radio de fuente de datos del sidebar, incluso deshabilitados */
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stRadio div[role="radio"][aria-disabled="true"] label,
    [data-testid="stSidebar"] .stRadio div[role="radio"][aria-checked] label {
        color: #000 !important;
        opacity: 1 !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        letter-spacing: 0.01em;
    }
    /* Hacer el texto de los selectbox del sidebar blanco para legibilidad en fondo oscuro */
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] *,
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
        color: #fff !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- PROCESAMIENTO SEGÚN LA FUENTE DE DATOS ---
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None
if 'fuente_datos' not in st.session_state:
    st.session_state['fuente_datos'] = 'Histórico'

# Procesamiento de la fuente de datos y definición de df_dashboard
if st.session_state['fuente_datos'] == "Nuevo extracto PDF" and st.session_state['uploaded_file'] is not None:
    df_pdf, extracto_mes = load_and_process_bank_statement(st.session_state['uploaded_file'])
    if not df_pdf.empty:
        df_dashboard = df_pdf.copy()
    else:
        df_dashboard = cargar_datos_historicos()
elif st.session_state['fuente_datos'] == "Histórico":
    df_dashboard = cargar_datos_historicos()
    if df_dashboard.empty:
        df_dashboard = generar_datos()
elif st.session_state['fuente_datos'] == "Datos de prueba 2024":
    def generar_datos_2024():
        fechas = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
        np.random.seed(42)
        ingresos = np.random.uniform(500, 2000, size=len(fechas))
        egresos = np.random.uniform(300, 1800, size=len(fechas))
        df = pd.DataFrame({
            "Fecha": fechas,
            "Ingresos": np.round(ingresos, 2),
            "Egresos": np.round(egresos, 2)
        })
        df["Flujo Neto"] = df["Ingresos"] - df["Egresos"]
        df["Saldo Acumulado"] = df["Flujo Neto"].cumsum()
        return df
    df_dashboard = generar_datos_2024()
else:
    df_dashboard = generar_datos()

# --- UNIFICAR COLUMNAS PARA EL DASHBOARD ---
columnas_requeridas = ["Fecha", "Ingresos", "Egresos", "Flujo Neto", "Saldo Acumulado"]
for col in columnas_requeridas:
    if col not in df_dashboard.columns:
        df_dashboard[col] = 0
if "Fecha" in df_dashboard.columns:
    df_dashboard["Fecha"] = pd.to_datetime(df_dashboard["Fecha"], errors='coerce')
df_dashboard = df_dashboard.sort_values("Fecha")

# --- SIDEBAR: carga de PDF, selección de fuente y filtros ---
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; margin-bottom: 1.5rem;'>
        <svg width="40" height="32" viewBox="0 0 40 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="20" width="6" height="8" rx="2" fill="#2563EB"/>
            <rect x="12" y="12" width="6" height="16" rx="2" fill="#22C55E"/>
            <rect x="20" y="6" width="6" height="22" rx="2" fill="#60A5FA"/>
            <rect x="28" y="2" width="6" height="26" rx="2" fill="#A5B4FC"/>
        </svg>
        <div style='font-weight: 700; font-size: 1.25rem; margin-top: 0.5rem; font-family: Inter, sans-serif;'>
            Control de Flujo de Caja
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### 📄 Cargar Extracto Bancario (PDF)")
    uploaded_file = st.file_uploader("Selecciona un archivo PDF", type=["pdf"])
    if uploaded_file is not None:
        st.session_state['uploaded_file'] = uploaded_file
    fuente_datos = st.radio(
        "Fuente de datos",
        ["Histórico", "Simulado", "Nuevo extracto PDF", "Datos de prueba 2024"],
        index=0
    )
    st.session_state['fuente_datos'] = fuente_datos
    st.markdown("### Periodo a visualizar")
    periodo_opcion = st.selectbox(
        "Selecciona el periodo",
        ["Mes", "Trimestre", "Semestre", "Año completo"],
        index=0
    )
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    trimestres = ["1er Trimestre", "2do Trimestre", "3er Trimestre", "4to Trimestre"]
    semestres = ["1er Semestre", "2do Semestre"]
    anio_actual = datetime.now().year
    mes_seleccionado = None
    trimestre_seleccionado = None
    semestre_seleccionado = None
    if periodo_opcion == "Mes":
        mes_seleccionado = st.selectbox("Mes", meses, index=datetime.now().month-1)
    elif periodo_opcion == "Trimestre":
        trimestre_seleccionado = st.selectbox("Trimestre", trimestres)
    elif periodo_opcion == "Semestre":
        semestre_seleccionado = st.selectbox("Semestre", semestres)
    anio_seleccionado = st.selectbox("Año", [anio_actual-2, anio_actual-1, anio_actual], index=2)
    datos_actualizados = st.button("Actualizar datos", key="refresh_button")

# --- Resetear fechas al cambiar la fuente de datos ---
if 'fuente_datos_anterior' not in st.session_state or st.session_state['fuente_datos_anterior'] != st.session_state['fuente_datos']:
    st.session_state['fecha_min'] = df_dashboard["Fecha"].min().date() if not df_dashboard.empty else datetime.today() - timedelta(days=30)
    st.session_state['fecha_max'] = df_dashboard["Fecha"].max().date() if not df_dashboard.empty else datetime.today()
    st.session_state['fuente_datos_anterior'] = st.session_state['fuente_datos']

# --- FILTRADO DE FECHAS Y USO EN DASHBOARD ---
# Filtrado según periodo seleccionado
if periodo_opcion == "Mes" and mes_seleccionado:
    mes_idx = meses.index(mes_seleccionado) + 1
    df_filtrado = df_dashboard[(df_dashboard["Fecha"].dt.month == mes_idx) & (df_dashboard["Fecha"].dt.year == anio_seleccionado)].copy()
elif periodo_opcion == "Trimestre" and trimestre_seleccionado:
    trimestre_map = {
        "1er Trimestre": [1,2,3],
        "2do Trimestre": [4,5,6],
        "3er Trimestre": [7,8,9],
        "4to Trimestre": [10,11,12]
    }
    meses_trimestre = trimestre_map[trimestre_seleccionado]
    df_filtrado = df_dashboard[(df_dashboard["Fecha"].dt.month.isin(meses_trimestre)) & (df_dashboard["Fecha"].dt.year == anio_seleccionado)].copy()
elif periodo_opcion == "Semestre" and semestre_seleccionado:
    semestre_map = {
        "1er Semestre": [1,2,3,4,5,6],
        "2do Semestre": [7,8,9,10,11,12]
    }
    meses_semestre = semestre_map[semestre_seleccionado]
    df_filtrado = df_dashboard[(df_dashboard["Fecha"].dt.month.isin(meses_semestre)) & (df_dashboard["Fecha"].dt.year == anio_seleccionado)].copy()
else:  # Año completo
    df_filtrado = df_dashboard[df_dashboard["Fecha"].dt.year == anio_seleccionado].copy()

# Contenedor principal
st.markdown('<div style="padding: 10px">', unsafe_allow_html=True)

# Encabezado con estadísticas principales
st.markdown('<div style="display: flex; justify-content: space-between; align-items: center;">', unsafe_allow_html=True)
st.markdown("# 💰 Dashboard Financiero")
st.markdown("</div>", unsafe_allow_html=True)
st.markdown('<p style="color: #666; margin-bottom: 30px;">Actualizado: ' + datetime.now().strftime("%d/%m/%Y %H:%M") + '</p>', unsafe_allow_html=True)

# KPIs en tarjetas modernas
st.markdown("## Resumen Financiero")
kpi_cols = st.columns(4)

with kpi_cols[0]:
    total_ingresos = df_filtrado["Ingresos"].sum()
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Total Ingresos</div>
        <div class="metric-value" style="color: var(--success);">${total_ingresos:,.2f}</div>
        <div style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 0.5rem;">
            Periodo actual
        </div>
    </div>
    """, unsafe_allow_html=True)

with kpi_cols[1]:
    total_egresos = df_filtrado["Egresos"].sum()
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Total Egresos</div>
        <div class="metric-value" style="color: var(--error);">${total_egresos:,.2f}</div>
        <div style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 0.5rem;">
            Periodo actual
        </div>
    </div>
    """, unsafe_allow_html=True)

with kpi_cols[2]:
    flujo_neto = total_ingresos - total_egresos
    color = "var(--success)" if flujo_neto >= 0 else "var(--error)"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Flujo Neto</div>
        <div class="metric-value" style="color: {color};">${flujo_neto:,.2f}</div>
        <div style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 0.5rem;">
            {(flujo_neto/total_ingresos)*100:.1f}% del ingreso
        </div>
    </div>
    """, unsafe_allow_html=True)

with kpi_cols[3]:
    if not df_filtrado.empty:
        saldo_actual = df_filtrado["Saldo Acumulado"].iloc[-1]
        fecha_max = df_filtrado["Fecha"].max().strftime("%d/%m/%Y")
    else:
        saldo_actual = 0
        fecha_max = "-"
    color = "var(--success)" if saldo_actual >= 0 else "var(--error)"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Saldo Actual</div>
        <div class="metric-value" style="color: {color};">${saldo_actual:,.2f}</div>
        <div style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 0.5rem;">
            al {fecha_max}
        </div>
    </div>
    """, unsafe_allow_html=True)

# Visualización principal - Sección de gráficos
st.markdown("## Análisis de Flujo de Caja")

# Pestañas para diferentes análisis
tab1, tab2, tab3 = st.tabs(["💵 Ingresos vs Egresos", "📊 Saldo Acumulado", "📈 Tendencias"])

with tab1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    
    # Actualizar gráfico principal
    def crear_grafico_ingresos_egresos(df):
        fig = go.Figure()
        
        # Configuración de colores moderna
        fig.add_bar(
            name="Ingresos",
            x=df["Fecha"],
            y=df["Ingresos"],
            marker_color='#22C55E',
            opacity=0.9
        )
        
        fig.add_bar(
            name="Egresos",
            x=df["Fecha"],
            y=df["Egresos"],
            marker_color='#EF4444',
            opacity=0.9
        )
        
        fig.add_scatter(
            name="Flujo Neto",
            x=df["Fecha"],
            y=df["Flujo Neto"],
            line=dict(color='#2563EB', width=2.5)
        )
        
        fig.update_layout(
            template='plotly_white',
            height=400,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(
                family="Inter, sans-serif",
                size=12,
                color="#1A202C"  # Color más oscuro para mejor legibilidad
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='rgba(0,0,0,0.1)',
                borderwidth=1,
                font=dict(
                    size=12,
                    color="#1A202C"
                )
            ),
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                tickformat="%d %b",
                tickfont=dict(size=11, color="#1A202C"),
                title_font=dict(size=12, color="#1A202C")
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                tickformat="$,.0f",
                tickfont=dict(size=11, color="#1A202C"),
                title_font=dict(size=12, color="#1A202C")
            )
        )
        
        return fig
    
    fig = crear_grafico_ingresos_egresos(df_filtrado)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    # Crear área sombreada para el saldo
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df_filtrado["Fecha"],
        y=df_filtrado["Saldo Acumulado"],
        mode='lines',
        fill='tozeroy',
        name='Saldo',
        line=dict(color='#22C55E', width=3),
        fillcolor='rgba(34, 197, 94, 0.18)'
    ))
    # Línea de referencia en cero
    fig2.add_shape(
        type="line",
        x0=df_filtrado["Fecha"].min(),
        y0=0,
        x1=df_filtrado["Fecha"].max(),
        y1=0,
        line=dict(color="rgba(0,0,0,0.3)", width=1, dash="dash")
    )
    # Estilo mejorado y legible
    fig2.update_layout(
        height=400,
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
        title="Evolución del Saldo",
        font=dict(
            family="Inter, sans-serif",
            size=12,
            color="#1A202C"
        ),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor='rgba(0,0,0,0.1)',
            tickformat="%d %b",
            tickfont=dict(size=11, color="#1A202C"),
            title_font=dict(size=12, color="#1A202C")
        ),
        yaxis=dict(
            title="Saldo ($)",
            showgrid=True,
            gridcolor='rgba(0,0,0,0.1)',
            zeroline=False,
            tickfont=dict(size=11, color="#1A202C"),
            title_font=dict(size=12, color="#1A202C")
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    # Análisis de tendencias con medias móviles
    df_tendencias = df_filtrado.copy()
    if len(df_tendencias) >= 7:  # Solo calcular si hay suficientes datos
        df_tendencias["MA7_Ingresos"] = df_tendencias["Ingresos"].rolling(window=7).mean()
        df_tendencias["MA7_Egresos"] = df_tendencias["Egresos"].rolling(window=7).mean()
        fig3 = go.Figure()
        # Ingresos puntuales y tendencia
        fig3.add_scatter(
            x=df_tendencias["Fecha"],
            y=df_tendencias["Ingresos"],
            mode='markers',
            name='Ingresos',
            marker=dict(color='#22C55E', size=8, opacity=0.5),
            showlegend=True
        )
        fig3.add_scatter(
            x=df_tendencias["Fecha"],
            y=df_tendencias["MA7_Ingresos"],
            mode='lines',
            name='Media móvil (Ingresos)',
            line=dict(color='#22C55E', width=3),
            showlegend=True
        )
        # Egresos puntuales y tendencia
        fig3.add_scatter(
            x=df_tendencias["Fecha"],
            y=df_tendencias["Egresos"],
            mode='markers',
            name='Egresos',
            marker=dict(color='#EF4444', size=8, opacity=0.5),
            showlegend=True
        )
        fig3.add_scatter(
            x=df_tendencias["Fecha"],
            y=df_tendencias["MA7_Egresos"],
            mode='lines',
            name='Media móvil (Egresos)',
            line=dict(color='#EF4444', width=3),
            showlegend=True
        )
        # Estilo mejorado y legible
        fig3.update_layout(
            height=400,
            template="plotly_white",
            margin=dict(l=20, r=20, t=40, b=20),
            title="Análisis de Tendencias (Media Móvil 7 días)",
            font=dict(
                family="Inter, sans-serif",
                size=12,
                color="#1A202C"
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='rgba(0,0,0,0.1)',
                borderwidth=1,
                font=dict(
                    size=12,
                    color="#1A202C"
                )
            ),
            xaxis=dict(
                title="",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                tickformat="%d %b",
                tickfont=dict(size=11, color="#1A202C"),
                title_font=dict(size=12, color="#1A202C")
            ),
            yaxis=dict(
                title="Monto ($)",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                tickfont=dict(size=11, color="#1A202C"),
                title_font=dict(size=12, color="#1A202C")
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("Se necesitan al menos 7 días de datos para mostrar tendencias.")
    st.markdown('</div>', unsafe_allow_html=True)

# Sección inferior - Tarjetas y tabla
col1, col2 = st.columns([1, 2])

with col1:
    # Tarjeta de balance estilo moderno
    st.markdown("### Balance Actual")
    try:
        if not df_filtrado.empty:
            saldo_actual = df_filtrado["Saldo Acumulado"].iloc[-1]
            promedio_saldo = df_filtrado["Saldo Acumulado"].mean()
            ultima_fecha = df_filtrado["Fecha"].max().strftime("%d/%m/%Y")
        else:
            saldo_actual = 0
            promedio_saldo = 0
            ultima_fecha = datetime.now().strftime("%d/%m/%Y")
    except (IndexError, AttributeError):
        saldo_actual = 0
        promedio_saldo = 0
        ultima_fecha = datetime.now().strftime("%d/%m/%Y")
    balance_color = '#9CFFA3' if saldo_actual >= 0 else '#FFCDD2'
    balance_icon = '↗' if saldo_actual >= 0 else '↘'
    st.markdown(f"""
    <div class="balance-card">
        <div class="balance-label">Saldo disponible</div>
        <div class="balance-value">{balance_icon} ${saldo_actual:,.2f}</div>
        <div style="display: flex; justify-content: space-between; align-items: center;" class="balance-secondary">
            <span>Promedio: ${promedio_saldo:,.2f}</span>
            <span>{ultima_fecha}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Timeline de eventos financieros
    st.markdown("### Próximos eventos")
    
    st.markdown("""
    <div class="timeline">
        <div class="timeline-item">
            <div class="timeline-dot" style="background-color: #F44336;"></div>
            <div class="timeline-text">
                <strong>Pago de proveedores</strong><br>
                <span style="color: #777;">28/04/2025</span>
            </div>
        </div>
        <div class="timeline-item">
            <div class="timeline-dot" style="background-color: #4CAF50;"></div>
            <div class="timeline-text">
                <strong>Cobro de factura #1234</strong><br>
                <span style="color: #777;">30/04/2025</span>
            </div>
        </div>
        <div class="timeline-item">
            <div class="timeline-dot" style="background-color: #2196F3;"></div>
            <div class="timeline-text">
                <strong>Cierre contable mensual</strong><br>
                <span style="color: #777;">01/05/2025</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    # Tabla de transacciones recientes
    st.markdown("### Transacciones recientes")
    
    # Formatear datos para la tabla
    tabla_df = df_filtrado.tail(10).copy()
    tabla_df["Tipo"] = np.where(tabla_df["Flujo Neto"] >= 0, "Ingreso", "Egreso")
    tabla_df["Estado"] = np.random.choice(["Completado", "Pendiente", "En proceso"], size=len(tabla_df))
    
    # Crear columnas con íconos para mejor visualización
    def formato_tabla(df):
        # Formatear montos
        formato = {
            "Ingresos": "${:,.2f}", 
            "Egresos": "${:,.2f}", 
            "Flujo Neto": "${:,.2f}"
        }
        
        # Aplicar formato solo a las columnas que existen
        formato_existente = {k: v for k, v in formato.items() if k in df.columns}
        df = df.style.format(formato_existente)
        
        # Aplicar colores según valores solo para la columna Flujo Neto si existe
        if "Flujo Neto" in df.columns:
            df = df.map(lambda x: 'color: #4CAF50' if isinstance(x, (int, float)) and x > 0 else 
                       ('color: #F44336' if isinstance(x, (int, float)) and x < 0 else ''), 
                       subset=['Flujo Neto'])
        
        return df
    
    # Mostrar solo las columnas que queremos en la tabla
    columnas_mostrar = ["Fecha", "Ingresos", "Egresos", "Flujo Neto", "Tipo", "Estado"]
    columnas_existentes = [col for col in columnas_mostrar if col in tabla_df.columns]
    st.dataframe(formato_tabla(tabla_df[columnas_existentes]), height=300)

# Sección final - Estadísticas comparativas
st.markdown("## Comparativa de Períodos")

try:
    # Datos comparativos entre periodos
    periodo_actual = df_filtrado["Flujo Neto"].sum()
    periodo_anterior = df_filtrado["Flujo Neto"].mean() * 0.8  # Simular datos del periodo anterior

    # Calcular variaciones
    variacion = ((periodo_actual - periodo_anterior) / abs(periodo_anterior)) * 100 if periodo_anterior != 0 else 0
    variacion_color = "#4CAF50" if variacion >= 0 else "#F44336"
    variacion_icono = "↑" if variacion >= 0 else "↓"
except Exception:
    periodo_actual = 0
    periodo_anterior = 0
    variacion = 0
    variacion_color = "#4CAF50"
    variacion_icono = "-"

comp_cols = st.columns(4)

with comp_cols[0]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">INGRESOS VS PERIODO ANTERIOR</div>
        <div class="metric-value" style="color: {variacion_color};">{variacion_icono} {abs(variacion):.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with comp_cols[1]:
    # Simulación de otra métrica comparativa
    var_egresos = -5.2  # Simulación
    var_color = "#4CAF50" if var_egresos <= 0 else "#F44336"
    var_icono = "↓" if var_egresos <= 0 else "↑"
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">EGRESOS VS PERIODO ANTERIOR</div>
        <div class="metric-value" style="color: {var_color};">{var_icono} {abs(var_egresos):.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with comp_cols[2]:
    # Métrica de eficiencia
    try:
        eficiencia = (periodo_actual / total_ingresos) * 100 if total_ingresos > 0 else 0
    except Exception:
        eficiencia = 0
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">EFICIENCIA FINANCIERA</div>
        <div class="metric-value">{eficiencia:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with comp_cols[3]:
    # Días de liquidez estimados
    try:
        gasto_diario = df_filtrado["Egresos"].mean() if len(df_filtrado) > 0 else 0
        dias_liquidez = int(saldo_actual / gasto_diario) if gasto_diario > 0 else 0
    except Exception:
        dias_liquidez = 0
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">DÍAS DE LIQUIDEZ</div>
        <div class="metric-value">{dias_liquidez}</div>
    </div>
    """, unsafe_allow_html=True)

# Pie de página
st.markdown("""
<div style="text-align: center; margin-top: 50px; padding: 20px; color: #666;">
    <p>Desarrollado por Willo con ❤️ usando Streamlit</p>
    <p style="font-size: 12px;">Actualizado el {}</p>
</div>
""".format(datetime.now().strftime("%d/%m/%Y %H:%M")), unsafe_allow_html=True)