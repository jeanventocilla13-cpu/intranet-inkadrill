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

# Inicializamos variables en la memoria
if "pestaña_activa" not in st.session_state:
    st.session_state.pestaña_activa = "💬 Chat Asistente Operativo"
if "archivo_activo" not in st.session_state:
    st.session_state.archivo_activo = "Base de datos general (Simulación)"

# --- INYECCIÓN DE ESTÉTICA GEMINI (CSS Customizado) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Google Sans', sans-serif !important;
    }
    
    /* ---------------------------------------------------
       HACKS DE LA BARRA LATERAL (ALINEACIÓN ESTRICTA)
       --------------------------------------------------- */
       
    /* FORZAR LA ALINEACIÓN A LA IZQUIERDA EN TODOS LOS BOTONES */
    [data-testid="stSidebar"] .stButton > button {
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        padding-left: 12px !important; 
    }
    
    [data-testid="stSidebar"] .stButton > button div[data-testid="stMarkdownContainer"] {
        width: 100% !important;
        display: flex !important;
        justify-content: flex-start !important;
    }
    
    [data-testid="stSidebar"] .stButton > button p {
        text-align: left !important;
        margin: 0 !important;
        width: 100% !important;
    }

    /* Botón "Nueva Conversación" (Tipo Primary) */
    [data-testid="stSidebar"] button[kind="primary"] {
        border-radius: 30px !important;
        background-color: #1e1f20 !important;
        border: 1px solid #444746 !important;
        color: #e3e3e3 !important;
        padding: 8px 15px !important;
        font-weight: 500 !important;
        transition: 0.3s !important;
    }
    [data-testid="stSidebar"] button[kind="primary"]:hover {
        background-color: #333639 !important;
    }
    
    /* Enlaces Sueltos del Historial (Tipo Secondary) */
    [data-testid="stSidebar"] button[kind="secondary"] {
        background-color: transparent !important;
        border: none !important;
        color: #c4c7c5 !important;
        font-weight: 400 !important;
        padding: 6px 12px !important;
        border-radius: 8px !important;
        margin-bottom: 2px !important;
        height: auto !important;
        min-height: 32px !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
        color: #e3e3e3 !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"] p {
        font-size: 14px !important; 
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
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
    if st.button("📝 Nueva conversación", type="primary", use_container_width=True):
        st.session_state.mensajes_ia = [] 
        st.session_state.pestaña_activa = "💬 Chat Asistente Operativo"
        st.rerun()
        
    st.markdown("<p style='color:#888; font-size:13px; font-weight:500; margin-top:20px; margin-bottom:5px; padding-left:10px;'>Navegación</p>", unsafe_allow_html=True)
    
    # 1. Definimos la lista PRIMERO
    opciones_nav = [
        "💬 Chat Asistente Operativo", 
        "🧮 Cálculos Geomecánicos", 
        "🗺️ Visor Topográfico", 
        "🛢️ Visualizador 3D Sondajes", 
        "📈 Dashboard Analíticas"
    ]
    
    # 2. Hacemos el bucle DESPUÉS (sin rombos, para alineación recta perfecta)
    for opt in opciones_nav:
        if st.button(opt, key=f"nav_{opt}", type="secondary", use_container_width=True):
            st.session_state.pestaña_activa = opt
            st.rerun()
    
    pestaña = st.session_state.pestaña_activa
    
    st.markdown("<br>", unsafe_allow_html=True) 
    st.markdown("<p style='color:#888; font-size:13px; font-weight:500; margin-bottom:5px; padding-left:10px;'>Recientes</p>", unsafe_allow_html=True)
    
    opciones_archivos = ["Base de datos general (Simulación)"]
    archivos_filtrados = []
    
    if "archivos_nube" in st.session_state:
        if pestaña in ["📈 Dashboard Analíticas", "🛢️ Visualizador 3D Sondajes", "🗺️ Visor Topográfico"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.csv', '.xlsx', '.xls', '.pdf'))]
        elif pestaña in ["💬 Chat Asistente Operativo"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.pdf', '.txt', '.png', '.jpg', '.jpeg', '.csv'))]
    
    for f in archivos_filtrados:
        opciones_archivos.append(f['name'])
        
    # Renderizamos la lista de archivos limpios
    for arch in opciones_archivos:
        icono = "📌" if st.session_state.archivo_activo == arch else "📄"
        if st.button(f"{icono} {arch}", key=f"file_{arch}", type="secondary", use_container_width=True):
            st.session_state.archivo_activo = arch
            st.rerun()
    
    st.markdown("---")
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

        if "mensajes_ia" not in st.session_state: st.session_state.mensajes_ia = []
        for mensaje in st.session_state.mensajes_ia:
            with st.chat_message(mensaje["rol"]): st.markdown(mensaje["contenido"])

        pregunta = st.chat_input("Pregunta a Gemini")
        if pregunta:
            with st.chat_message("user"): st.markdown(pregunta)
            st.session_state.
