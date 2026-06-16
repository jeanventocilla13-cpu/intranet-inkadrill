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
       HACKS DE LA BARRA LATERAL (ESTILO GEMINI)
       --------------------------------------------------- */
       
    /* FORZAR LA ALINEACIÓN A LA IZQUIERDA EN EL CONTENIDO DEL BOTÓN */
    [data-testid="stSidebar"] .stButton button div[data-testid="stMarkdownContainer"] {
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        width: 100% !important;
    }
    
    [data-testid="stSidebar"] .stButton button p {
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
        padding: 4px 10px !important;
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
        font-size: 13.5px !important; 
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
    
    opciones_nav = [
        "💬 Chat Asistente Operativo", 
        "🧮 Cálculos Geomecánicos", 
        "🗺️ Visor Topográfico", 
        "🛢️ Visualizador 3D Sondajes", 
        "📈 Dashboard Analíticas"
    ]
    
    for opt in opciones_nav:
        # Quitamos los espacios raros. Solo mostramos el ícono azul si está activo.
        etiqueta = f"🔹 {opt}" if st.session_state.pestaña_activa == opt else f"{opt}"
        if st.button(etiqueta, key=opt, type="secondary", use_container_width=True):
            st.session_state.pestaña_activa = opt
            st.rerun()
    
    pestaña = st.session_state.pestaña_activa
    
    st.markdown("<br>", unsafe_allow_html=True) 
    st.markdown("<p style='color:#888; font-size:13px; font-weight:500; margin-bottom:5px; padding-left:10px;'>Recientes (Archivo Activo)</p>", unsafe_allow_html=True)
    
    opciones_archivos = ["Base de datos general (Simulación)"]
    archivos_filtrados = []
    
    if "archivos_nube" in st.session_state:
        if pestaña in ["📈 Dashboard Analíticas", "🛢️ Visualizador 3D Sondajes", "🗺️ Visor Topográfico"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.csv', '.xlsx', '.xls', '.pdf'))]
        elif pestaña in ["💬 Chat Asistente Operativo"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.pdf', '.txt', '.png', '.jpg', '.jpeg', '.csv'))]
    
    for f in archivos_filtrados:
        opciones_archivos.append(f['name'])
        
    # Renderizamos la lista de archivos con iconos simples, alineados a la izquierda
    for arch in opciones_archivos:
        icono = "📌" if st.session_state.archivo_activo == arch else "📄"
        if st.button(f"{icono} {arch}", key=f"file_{arch}", type="secondary", use_
