import streamlit as st
import google.generativeai as genai
import os
import PyPDF2
import json
import pandas as pd
import folium
import plotly.graph_objects as go
import plotly.express as px
from streamlit_folium import st_folium
from io import BytesIO, StringIO
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import datetime
import numpy as np
from PIL import Image
from pyproj import Transformer

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="InkaDrill - Cerebro IA", page_icon="✨", layout="wide")

# --- INYECCIÓN DE ESTÉTICA GEMINI (CSS Customizado) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Google Sans', sans-serif !important;
    }
    
    /* ---------------------------------------------------
       HACKS DE LA BARRA LATERAL (ESTILO GEMINI)
       --------------------------------------------------- */
    
    /* Ocultar los círculos nativos de Streamlit */
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    
    /* Darle forma de píldora a los elementos del menú */
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        padding: 10px 15px !important;
        border-radius: 30px !important;
        margin-bottom: 2px !important;
        transition: 0.2s !important;
        color: #e3e3e3 !important;
        cursor: pointer !important;
    }
    
    /* Efecto Hover (pasar el mouse) */
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
    }
    
    /* Estilo del elemento seleccionado (Activo) */
    [data-testid="stSidebar"] div[role="radiogroup"] > label[aria-checked="true"] {
        background-color: rgba(168, 199, 250, 0.12) !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[aria-checked="true"] > div:last-child {
        color: #a8c7fa !important;
        font-weight: 500 !important;
    }
    
    /* Botón "Nueva Conversación" */
    [data-testid="stSidebar"] .stButton>button {
        border-radius: 30px !important;
        background-color: #1e1f20 !important;
        border: 1px solid #444746 !important;
        color: #e3e3e3 !important;
        padding: 12px 20px !important;
        justify-content: flex-start !important;
        font-weight: 500 !important;
        transition: 0.3s !important;
    }
    [data-testid="stSidebar"] .stButton>button:hover {
        background-color: #444746 !important;
    }
    
    /* ---------------------------------------------------
       HACKS DEL CHAT Y BOTÓN FLOTANTE
       --------------------------------------------------- */
    .stChatInputContainer {
        border-radius: 30px !important;
        background-color: #1e1f20 !important;
        border: 1px solid #444746 !important;
        width: calc(100% - 60px) !important;
        margin-left: 60px !important;
    }
    .stChatInputContainer textarea {
        padding-left: 45px !important;
        font-size: 16px !important;
    }
    div[data-testid="stPopover"] {
        position: fixed !important;
        bottom: 27px !important;
        z-index: 999999 !important;
        width: auto !important;
    }
    div[data-testid="stPopover"] > button {
        width: 44px !important;
        height: 44px !important;
        border-radius: 50% !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: #1e1f20 !important;
        border: 1px solid #444746 !important;
        color: #e3e3e3 !important;
        font-size: 24px !important;
        line-height: 0 !important;
        transition: 0.3s;
    }
    div[data-testid="stPopover"] > button:hover {
        background-color: #444746 !important;
        border-color: #a8c7fa !important;
        color: #a8c7fa !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

ID_CARPETA_MEMORIA = "1L-6rI-3lu4m0PoXk8Y1brudQC9PrkGCn"

# --- 2. CONEXIÓN A LAS IA Y GOOGLE DRIVE ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    modelo = genai.GenerativeModel('gemini-1.5-flash')
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    token_dict = json.loads(st.secrets["GOOGLE_TOKEN"])
    creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
    
    drive_service = build('drive', 'v3', credentials=creds)
    conexion_exitosa = True
except Exception as e:
    conexion_exitosa = False
    st.error(f"Error de conexión con los servidores: {e}")

if "archivos_nube" not in st.session_state and conexion_exitosa:
    try:
        query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
        st.session_state.archivos_nube = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
    except:
        st.session_state.archivos_nube = []

# --- 3. BARRA LATERAL ESTILO GEMINI ---
with st.sidebar:
    st.markdown("<div style='display:flex; align-items:center; margin-bottom:15px;'><h2 style='color:#e3e3e3; font-weight:500; font-size:22px; margin:0;'>✨ InkaDrill IA</h2></div>", unsafe_allow_html=True)
    
    # Botón de Nueva Conversación
    if st.button("📝 Nueva conversación", use_container_width=True):
        st.session_state.mensajes_ia = [] # Limpia el historial del chat
        st.rerun()
        
    st.markdown("<p style='color:#888; font-size:13px; font-weight:500; margin-top:20px; margin-bottom:5px; padding-left:10px;'>Recientes</p>", unsafe_allow_html=True)
    
    pestaña = st.radio(
        "Navegación:",
        ["💬 Chat Asistente Operativo", "🧮 Cálculos Geomecánicos", "🗺️ Visor Topográfico", "🛢️ Visualizador 3D Sondajes", "📈 Dashboard Analíticas"],
        label_visibility="collapsed"
    )
    
    st.markdown("<br><br><br>", unsafe_allow_html=True) # Espaciador
    st.markdown("<p style='color:#888; font-size:13px; font-weight:500; margin-bottom:5px; padding-left:10px;'>📂 Archivo Activo en Memoria</p>", unsafe_allow_html=True)
    
    opciones_archivos = ["Base de datos general (Simulación)"]
    archivos_filtrados = []
    
    if "archivos_nube" in st.session_state:
        if pestaña in ["📈 Dashboard Analíticas", "🛢️ Visualizador 3D Sondajes", "🗺️ Visor Topográfico"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.csv', '.xlsx', '.xls', '.pdf'))]
        elif pestaña in ["💬 Chat Asistente Operativo"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.pdf', '.txt', '.png', '.jpg', '.jpeg', '.csv'))]
    
    for f in archivos_filtrados:
        opciones_archivos.append(f['name'])
        
    archivo_seleccionado = st.selectbox("Selecciona un documento para analizar:", opciones_archivos, label_visibility="collapsed")
    st.session_state.archivo_activo = archivo_seleccionado
    
    st.markdown("---")
    # Tu perfil simulado en la parte inferior
    st.markdown("""
        <div style='display:flex; align-items:center; padding-left:10px;'>
            <div style='width:30px; height:30px; border-radius:50%; background-color:#a8c7fa; color:#000; display:flex; justify-content:center; align-items:center; font-weight:bold; font-size:14px; margin-right:10px;'>J</div>
            <div><p style='margin:0; font-size:14px; color:#e3e3e3;'>Jean Kennedy</p><p style='margin:0; font-size:12px; color:#888;'>Ingeniería Pro</p></div>
        </div>
    """, unsafe_allow_html=True)

if conexion_exitosa:
    # ====================================================================
    # PESTAÑA 1: CHATBOT UNIFICADO
    # ====================================================================
    if pestaña == "💬 Chat Asistente Operativo":
        st.markdown("<h1 style='text-align: center; background: -webkit-linear-gradient(45deg, #4285f4, #d96570, #9b72cb); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 500; font-size: 46px; margin-top: 50px; margin-bottom: 30px;'>Hola, Jean</h1>", unsafe_allow_html=True)
        
        if st.session_state.archivo_activo != "Base de datos general (Simulación)":
            st.info(f"🔎 **Modo Enfoque:** El chat responderá basándose en el archivo: `{st.session_state.archivo_activo}`")
            
        with st.popover("➕"):
            st.markdown("#### 🛠️ Herramientas")
            tab1, tab2 = st.tabs(["📎 Subir Archivos", "📊 Extraer Tablas"])
            
            with tab1:
                archivo_subido = st.file_uploader("Arrastra PDFs, TXT, o Imágenes", type=["pdf", "txt", "png", "jpg", "jpeg"], key="uploader_normal")
                if st.button("Guardar en Nube InkaDrill", type="primary", use_container_width=True):
                    if archivo_subido:
                        with st.spinner("Subiendo..."):
                            st.success("Guardado correctamente.")
                            st.rerun()

            with tab2:
                archivo_tabla = st.file_uploader("Sube un PDF topográfico", type=["pdf"], key="extractor")
                if st.button("Procesar Tabla", type="primary", use_container_width=True):
                    if archivo_tabla:
                        with st.spinner("Procesando..."):
                            try:
                                media_pdf = MediaIoBaseUpload(BytesIO(archivo_tabla.getvalue()), mimetype='application/pdf', resumable=True)
                                metadata_pdf = {'name': archivo_tabla.name, 'parents': [ID_CARPETA_MEMORIA]}
                                drive_service.files().create(body=metadata_pdf, media_body=media_pdf, fields='id').execute()
                                
                                texto_pdf = ""
                                lector_pdf = PyPDF2.PdfReader(archivo_tabla)
                                for pagina in lector_pdf.pages: texto_pdf += pagina.extract_text() + "\n"
                                
                                instruccion_csv = f"""
                                Actúa como experto. Extrae ÚNICAMENTE la tabla "Coordenadas WGS84".
                                IGNORA "Demarcaciones", "Cartas" y "PSAD56".
                                Devuelve CSV con 3 columnas: Vertice,Norte,Este
                                No uses comas de miles. Texto:\n{texto_pdf}
                                """
                                respuesta_csv = modelo.generate_content(instruccion_csv)
                                datos_limpios = respuesta_csv.text.replace("```csv", "").replace("```", "").strip()
                                
                                nombre_csv = f"Datos_{archivo_tabla.name.replace('.pdf', '')}.csv"
                                media_csv = MediaIoBaseUpload(BytesIO(datos_limpios.encode('utf-8')), mimetype='text/csv', resumable=True)
                                metadata_csv = {'name': nombre_csv, 'parents': [ID_CARPETA_MEMORIA]}
                                drive_service.files().create(body=metadata_csv, media_body=media_csv, fields='id').execute()
                                
                                query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
                                st.session_state.archivos_nube = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
                                
                                st.success("¡Datos extraídos limpiamente!")
                                st.download_button(label="📥 Descargar CSV", data=datos_limpios, file_name=nombre_csv, mime="text/csv", use_container_width=True)
                            except Exception as e:
                                st.error(f"Error: {e}")

        # LÓGICA DEL CHAT
        if "mensajes_ia" not in st.session_state: st.session_state.mensajes_ia = []
        for mensaje in st.session_state.mensajes_ia:
            with st.chat_message(mensaje["rol"]): st.markdown(mensaje["contenido"])

        # INPUT DEL CHAT 
        pregunta = st.chat_input("Pregunta a Gemini")
        if pregunta:
            with st.chat_message("user"): st.markdown(pregunta)
            st.session_state.mensajes_ia.append({"rol": "user", "contenido": pregunta})
            with st.chat_message("assistant"):
                st.markdown("Procesando...")

    # ====================================================================
    # PESTAÑA 2: CÁLCULOS GEOMECÁNICOS
    # ====================================================================
    elif pestaña == "🧮 Cálculos Geomecánicos":
        st.title("Suite de Análisis Geomecánico 🪨")
        tab_rmr, tab_gsi = st.tabs(["Clasificación RMR", "Índice GSI"])
        with tab_rmr:
            col1, col2 = st.columns(2)
            with col1:
                p1 = st.number_input("Resistencia Compresión Simple (MPa)", value=50)
                p2 = st.slider("RQD (%)", 0, 100, 75)
            with col2:
                p4 = st.selectbox("Condición de Discontinuidades", ["Cerradas", "Rugosas", "Abiertas"])
            if st.button("Calcular RMR", type="primary"):
                val_rmr = (p2 * 0.2) + (p1 * 0.1) + 30
                st.success(f"**Puntaje RMR Estimado:** {val_rmr:.
