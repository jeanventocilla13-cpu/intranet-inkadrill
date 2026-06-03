import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io  # <- Nueva librería para procesar el Excel en memoria
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- 2. CONFIGURACIÓN DE LA INTELIGENCIA ARTIFICIAL Y SECRETOS ---
# Leemos la clave de Gemini desde la nube
genai.configure(api_key=st.secrets["GEMINI_API_KEY"]) 
modelo = genai.GenerativeModel('gemini-1.5-flash')
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# IDs de Drive
DOC_WORD_1_ID = '1zaJVdGMqmKAf-GTQx6oY8fkCTOX_Lvaj3uwB1RDwOso'
DOC_WORD_2_ID = '1lNIfPGcq7gS5uYgw_Qd_R3Emz2D8TEz34teJ3ysECGs'
EXCEL_DATOS_ID = '18qcBENgyhsEh340d-AINcKfh4sArAWz-OBchn5HCFZY'

# Truco maestro: Crear el token de Drive temporalmente en la nube usando el secreto
if "GOOGLE_TOKEN" in st.secrets:
    with open('token.json', 'w') as f:
        f.write(st.secrets["GOOGLE_TOKEN"])
# --- 2. CSS PARA EL DISEÑO CORPORATIVO ---
estilo_dashboard = """
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #e9ecef; }
    .top-nav {
        background-color: white; padding: 15px 30px; display: flex; align-items: center;
        justify-content: space-between; border-bottom: 2px solid #105c24;
        margin-top: -60px; margin-left: -4rem; margin-right: -4rem; margin-bottom: 20px;
    }
    .logo-text { color: #105c24; font-size: 24px; font-weight: 900; }
    .nav-links span { margin: 0 15px; color: #333; font-weight: bold; cursor: pointer; }
    .nav-links span.active { color: white; background-color: #105c24; padding: 10px 15px; border-radius: 5px; }
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
</style>
"""
st.markdown(estilo_dashboard, unsafe_allow_html=True)

# --- 3. BARRA SUPERIOR ---
st.markdown("""
<div class="top-nav">
    <div class="logo-text">⛏️ INKADRILL <span style="font-size:12px; color:#666;">INTRANET</span></div>
    <div class="nav-links">
        <span class="active">🏠 Inicio</span><span>📍 Topografía</span><span>🗄️ Datos</span>
    </div>
    <div><strong>Perfil</strong><br><span style="font-size: 12px;">Usuario InkaDrill</span></div>
</div>
""", unsafe_allow_html=True)

# --- 4. FUNCIÓN PARA DESCARGAR DATOS DE DRIVE ---
@st.cache_data(ttl=300)
def cargar_datos_excel():
    try:
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        service = build('drive', 'v3', credentials=creds)
        respuesta = service.files().export_media(fileId=EXCEL_DATOS_ID, mimeType='text/csv').execute()
        df = pd.read_csv(io.StringIO(respuesta.decode('utf-8')))
        return df, service
    except Exception as e:
        # ¡Ahora Streamlit nos mostrará el error exacto en pantalla!
        st.error(f"Error técnico exacto: {e}") 
        return None, None
    
# Cargamos la base de datos maestra
datos_reales, drive_service = cargar_datos_excel()

# --- 5. BUSCADOR INTELIGENTE CON IA (Leyendo 2 Documentos) ---
col_busq1, col_busq2, col_busq3 = st.columns([1, 3, 1])

with col_busq2:
    with st.form(key='formulario_ia'):
        pregunta_usuario = st.text_input("Buscar en la intranet...", placeholder="Consulta operativa a la IA...", label_visibility="collapsed")
        boton_buscar = st.form_submit_button("Consultar Documentos 🧠")
        
    if boton_buscar and pregunta_usuario:
        with st.spinner("Analizando múltiples documentos operativos..."):
            if drive_service:
                try:
                    # Descargamos ambos documentos
                    doc1 = drive_service.files().export_media(fileId=DOC_WORD_1_ID, mimeType='text/plain').execute().decode('utf-8')
                    doc2 = drive_service.files().export_media(fileId=DOC_WORD_2_ID, mimeType='text/plain').execute().decode('utf-8')
                    
                    # Unimos la información para la IA
                    instruccion = f"""
                    Eres el asistente inteligente minero de InkaDrill.
                    Responde a la consulta basándote ÚNICAMENTE en estos dos documentos:
                    
                    --- DOCUMENTO 1 ---
                    {doc1}
                    
                    --- DOCUMENTO 2 ---
                    {doc2}
                    
                    PREGUNTA DEL USUARIO: {pregunta_usuario}
                    """
                    respuesta_ia = modelo.generate_content(instruccion)
                    st.success("✅ Respuesta generada a partir de los 2 documentos:")
                    st.info(respuesta_ia.text)
                except Exception as e:
                    st.error(f"Error al leer los documentos de texto: {e}")
            else:
                st.error("No se pudo conectar a Google Drive.")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<h2 style='color: #2c3e50; font-family: sans-serif; font-weight: 800; font-size: 22px;'>PANEL DE DATOS EN TIEMPO REAL (Desde Google Sheets)</h2>", unsafe_allow_html=True)

# --- 6. GRÁFICOS Y TABLAS ALIMENTADOS POR EL EXCEL ---
if datos_reales is not None:
    # Fila 1
    fila1_col1, fila1_col2 = st.columns(2)

    with fila1_col1:
        with st.container(border=True):
            st.subheader("Resumen Topográfico")
            m1, m2 = st.columns(2)
            # Contamos cuántas filas (puntos) hay en el Excel
            m1.metric("Puntos Capturados (Total)", f"{len(datos_reales)}")
            m2.metric("Estado de Conexión", "Online (Drive)")

    with fila1_col2:
        with st.container(border=True):
            st.subheader("Avance Topográfico")
            # Graficamos directamente desde las columnas 'Día' y 'Metros' del Excel
            if 'Día' in datos_reales.columns and 'Metros' in datos_reales.columns:
                fig_barras = px.bar(datos_reales, x="Día", y="Metros", color_discrete_sequence=['#105c24'])
                fig_barras.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200)
                st.plotly_chart(fig_barras, use_container_width=True)
            else:
                st.warning("El Excel no tiene las columnas 'Día' y 'Metros'.")

    # Fila 2
    fila2_col1, fila2_col2 = st.columns(2)

    with fila2_col1:
        with st.container(border=True):
            st.subheader("Datos Crudos de Perforación")
            # Mostramos toda la tabla del Excel
            st.dataframe(datos_reales, hide_index=True, use_container_width=True)

    with fila2_col2:
        with st.container(border=True):
            st.subheader("Distribución de Coordenadas (UTM)")
            # Mapeamos los puntos usando las coordenadas del Excel
            if 'Coordenada E' in datos_reales.columns and 'Coordenada N' in datos_reales.columns:
                fig_dispersion = px.scatter(datos_reales, x="Coordenada E", y="Coordenada N", color_discrete_sequence=['#e67e22'])
                fig_dispersion.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=220)
                st.plotly_chart(fig_dispersion, use_container_width=True)
            else:
                st.warning("El Excel no tiene las columnas 'Coordenada E' y 'Coordenada N'.")
else:
    st.error("No se pudo cargar la base de datos de Google Sheets. Verifica el ID.")
