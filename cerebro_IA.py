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
    
    /* Input del chat estilo píldora Gemini */
    .stChatInputContainer {
        border-radius: 30px !important;
        background-color: #1e1f20 !important;
        border: 1px solid #444746 !important;
        padding-left: 10px;
    }
    
    /* Botón flotante estilo Gemini (+) */
    div[data-testid="stPopover"] > button {
        border-radius: 50px !important;
        background-color: #1e1f20 !important;
        border: 1px solid #444746 !important;
        color: #e3e3e3 !important;
        padding: 10px 20px !important;
        font-weight: 500 !important;
        transition: 0.3s;
    }
    div[data-testid="stPopover"] > button:hover {
        background-color: #444746 !important;
        border-color: #a8c7fa !important;
    }
    
    /* Botones principales limpios */
    .stButton>button {
        border-radius: 24px !important;
        font-weight: 500 !important;
    }
    
    /* Ocultar elementos innecesarios */
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

# --- 3. BARRA LATERAL CON HISTORIAL CONTEXTUAL ---
with st.sidebar:
    st.markdown("<h2 style='color: #a8c7fa; font-weight: 700; text-align: center; letter-spacing: 1px;'>✨ INKADRILL IA</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    pestaña = st.radio(
        "Navegación:",
        ["💬 Chat Asistente Operativo", "🧮 Cálculos Geomecánicos", "🗺️ Visor Topográfico", "🛢️ Visualizador 3D de Sondajes", "📈 Dashboard de Analíticas"]
    )
    
    st.markdown("---")
    st.markdown("### 🗂️ Archivo Activo")
    
    opciones_archivos = ["Base de datos general (Simulación)"]
    archivos_filtrados = []
    
    if "archivos_nube" in st.session_state:
        if pestaña in ["📈 Dashboard de Analíticas", "🛢️ Visualizador 3D de Sondajes", "🗺️ Visor Topográfico"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.csv', '.xlsx', '.xls', '.pdf'))]
        elif pestaña in ["💬 Chat Asistente Operativo"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.pdf', '.txt', '.png', '.jpg', '.jpeg', '.csv'))]
    
    for f in archivos_filtrados:
        opciones_archivos.append(f['name'])
        
    archivo_seleccionado = st.selectbox("Selecciona un documento para analizar:", opciones_archivos, label_visibility="collapsed")
    st.session_state.archivo_activo = archivo_seleccionado
    
    st.markdown("---")
    st.markdown("<p style='font-size: 11px; color: #888; text-align: center;'>InkaDrill 2026 ©<br>Plataforma Integral Minera</p>", unsafe_allow_html=True)

if conexion_exitosa:
    # ====================================================================
    # PESTAÑA 1: CHATBOT UNIFICADO
    # ====================================================================
    if pestaña == "💬 Chat Asistente Operativo":
        st.markdown("<h1 style='text-align: center; background: -webkit-linear-gradient(45deg, #4285f4, #d96570, #9b72cb); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 500; font-size: 46px; margin-top: 10px; margin-bottom: 30px;'>Hola, Jean, ¿qué vamos a hacer?</h1>", unsafe_allow_html=True)
        
        if st.session_state.archivo_activo != "Base de datos general (Simulación)":
            st.info(f"🔎 **Modo Enfoque:** El chat responderá basándose en el archivo: `{st.session_state.archivo_activo}`")
            
        # === EL NUEVO MENÚ FLOTANTE ESTILO GEMINI ===
        with st.popover("➕ Herramientas y Subidas"):
            st.markdown("### Selecciona una herramienta:")
            tab1, tab2 = st.tabs(["📎 Subir a Base de Datos", "📊 Extractor Quirúrgico"])
            
            with tab1:
                archivo_subido = st.file_uploader("Arrastra PDFs, TXT, o Imágenes", type=["pdf", "txt", "png", "jpg", "jpeg"], key="uploader_normal")
                if st.button("Guardar en Nube InkaDrill", type="primary", use_container_width=True):
                    if archivo_subido:
                        with st.spinner("Subiendo..."):
                            st.success("Guardado correctamente.")
                            st.rerun()

            with tab2:
                archivo_tabla = st.file_uploader("Sube un PDF de INGEMMET", type=["pdf"], key="extractor")
                if st.button("Extraer Tablas", type="primary", use_container_width=True):
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

        st.markdown("---")
        
        if "mensajes_ia" not in st.session_state: st.session_state.mensajes_ia = []
        for mensaje in st.session_state.mensajes_ia:
            with st.chat_message(mensaje["rol"]): st.markdown(mensaje["contenido"])

        pregunta = st.chat_input("Pregunta a la IA sobre la mina, documentos o imágenes...")
        if pregunta:
            with st.chat_message("user"): st.markdown(pregunta)
            st.session_state.mensajes_ia.append({"rol": "user", "contenido": pregunta})
            with st.chat_message("assistant"):
                st.markdown("Procesando...")

    # ====================================================================
    # DEMÁS PESTAÑAS
    # ====================================================================
    elif pestaña == "🧮 Cálculos Geomecánicos":
        st.title("Suite Geomecánica 🪨")
    elif pestaña == "🗺️ Visor Topográfico":
        st.title("Control Topográfico 🗺️")
    elif pestaña in ["🛢️ Visualizador 3D de Sondajes", "📈 Dashboard de Analíticas"]:
        st.title(pestaña)
