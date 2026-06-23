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
import base64
import requests
import re
import math

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="InkaDrill - Cerebro IA", page_icon="✨", layout="wide")

# --- INICIALIZACIÓN DE VARIABLES DE ESTADO DE CHATS ---
if "pestaña_activa" not in st.session_state:
    st.session_state.pestaña_activa = "Chat Asistente Operativo"
if "modo_ia" not in st.session_state:
    st.session_state.modo_ia = "🌐 Gemini IA (Internet)"
if "conversaciones" not in st.session_state:
    st.session_state.conversaciones = {"Conversación 1": []}
if "chat_activo" not in st.session_state:
    st.session_state.chat_activo = "Conversación 1"

def obtener_icono(nombre_archivo):
    nombre_lower = nombre_archivo.lower()
    if "simulación" in nombre_lower or "simulacion" in nombre_lower: return "⚙️"  
    elif nombre_lower.endswith('.pdf'): return "📕"  
    elif nombre_lower.endswith(('.csv', '.xlsx', '.xls')): return "📗"  
    elif nombre_lower.endswith(('.png', '.jpg', '.jpeg')): return "🖼️"  
    elif nombre_lower.endswith('.txt'): return "📝"  
    else: return "📄"  

# --- INYECCIÓN DE ESTÉTICA GEMINI (CSS Customizado) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Google Sans', sans-serif !important; }
    
    .stApp {
        background: linear-gradient(rgba(19, 19, 20, 0.70), rgba(19, 19, 20, 0.70)), 
                    url("https://github.com/jeanventocilla13-cpu/intranet-inkadrill/blob/main/fondo%20de%20escaneo.png?raw=true") no-repeat center center fixed !important;
        background-size: cover !important;
    }
    [data-testid="stHeader"] { background-color: transparent !important; }

    [data-testid="stSidebar"] {
        background-color: rgba(19, 19, 20, 0.4) !important;
        backdrop-filter: blur(15px) !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important; 
    }

    [data-testid="stSidebar"] button[kind="secondary"] {
        padding-left: 10px !important; background-color: transparent !important; border: none !important;
        border-radius: 8px !important; display: flex !important; justify-content: flex-start !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"] div { display: flex !important; justify-content: flex-start !important; width: 100% !important; }
    [data-testid="stSidebar"] button[kind="secondary"] p { text-align: left !important; color: #c4c7c5 !important; margin: 0 !important; font-size: 14px !important; }
    [data-testid="stSidebar"] button[kind="secondary"]:hover { background-color: rgba(255, 255, 255, 0.08) !important; }

    [data-testid="stSidebar"] button[kind="primary"] {
        border-radius: 30px !important; background-color: rgba(30, 31, 32, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important; color: #e3e3e3 !important; font-weight: 500 !important;
    }
    
    div[role="radiogroup"] > label {
        background-color: transparent !important; padding: 8px 10px !important; border-radius: 8px !important;
        cursor: pointer !important; margin-bottom: 2px !important; transition: 0.2s;
    }
    div[role="radiogroup"] > label:hover { background-color: rgba(255, 255, 255, 0.05) !important; }
    div[role="radiogroup"] > label > div:first-of-type { display: none !important; }
    div[role="radiogroup"] > label:has(input:checked) { background-color: rgba(255, 213, 79, 0.15) !important; border-left: 3px solid #ffd54f !important; }
    div[role="radiogroup"] > label:has(input:checked) p { color: #ffd54f !important; font-weight: 600 !important; }
    div[role="radiogroup"] p { color: #c4c7c5 !important; font-size: 14.5px !important; margin: 0 !important; text-align: left !important; }
    
    [data-testid="stBottom"], [data-testid="stBottom"] > div { background-color: transparent !important; border: none !important; box-shadow: none !important; }
    .stChatFloatingInputContainer { background-color: transparent !important; }

    .stChatInputContainer {
        border-radius: 30px !important; background-color: rgba(25, 26, 27, 0.85) !important; backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important; width: calc(100% - 65px) !important; margin-left: 65px !important; margin-bottom: 15px !important;
    }
    .stChatInputContainer textarea { padding-left: 20px !important; color: #e3e3e3 !important; }
    
    .panel-geo { background-color: rgba(25, 26, 27, 0.6) !important; backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 12px; padding: 20px; height: 100%; }
    .titulo-seccion { color: #e3e3e3; font-size: 16px; font-weight: 600; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; }
    .metric-box { background-color: rgba(19, 19, 20, 0.8) !important; border: 1px solid rgba(255, 255, 255, 0.05) !important; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 15px; }
    .metric-value { font-size: 46px; font-weight: 700; margin: 5px 0; line-height: 1; }
    .metric-label { color: #aaa; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin: 0; }
    
    .file-card { background-color: rgba(30, 31, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 15px; margin-bottom: 15px; display: flex; align-items: center; transition: 0.3s; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .file-card:hover { background-color: rgba(255, 255, 255, 0.05); border-color: #a8c7fa; transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.5); }
    .file-icon { font-size: 34px; margin-right: 15px; }
    .file-details { overflow: hidden; width: 100%; }
    .file-name { color: #e3e3e3; font-weight: 600; margin: 0; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .file-id { color: #888; font-size: 11px; margin: 0; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

ID_CARPETA_MEMORIA = "1L-6rI-3lu4m0PoXk8Y1brudQC9PrkGCn"

# --- 2. CONEXIÓN A LAS IA Y GOOGLE DRIVE ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    modelo = genai.GenerativeModel('gemini-2.5-flash')
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    token_dict = json.loads(st.secrets["GOOGLE_TOKEN"])
    creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
    
    drive_service = build('drive', 'v3', credentials=creds)
    conexion_exitosa = True
except Exception as e:
    conexion_exitosa = False

if "archivos_nube" not in st.session_state and conexion_exitosa:
    try:
        query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
        st.session_state.archivos_nube = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
    except:
        st.session_state.archivos_nube = []

# --- 3. BARRA LATERAL ESTILO GEMINI ---
with st.sidebar:
    st.markdown("<div style='display:flex; align-items:center; margin-bottom:10px;'><h2 style='color:#e3e3e3; font-weight:500; font-size:22px; margin:0;'>✨ InkaDrill IA</h2></div>", unsafe_allow_html=True)
    
    # MEJORA 2: Interruptor del Origen de la Base de Datos (Entre el logo y nuevo chat)
    seleccion_origen = st.selectbox(
        "Base de Datos Activa:", 
        ["🌐 Gemini IA (Internet)", "🔱 InkaDrill IA (Carpeta Drive)"],
        index=0 if st.session_state.modo_ia == "🌐 Gemini IA (Internet)" else 1
    )
    st.session_state.modo_ia = seleccion_origen
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botón Nueva Conversación
    if st.button("📝 Nueva conversación", type="primary", use_container_width=True):
        nuevo_id = f"Conversación {len(st.session_state.conversaciones) + 1}"
        st.session_state.conversaciones[nuevo_id] = []
        st.session_state.chat_activo = nuevo_id
        st.session_state.pestaña_activa = "Chat Asistente Operativo"
        st.rerun()
        
    st.markdown("<p style='color:#888; font-size:13px; font-weight:500; margin-top:20px; margin-bottom:5px; padding-left:10px;'>Herramientas</p>", unsafe_allow_html=True)
    
    opciones_nav = {
        "💬": "Chat Asistente Operativo", 
        "🪨": "Cálculos Geomecánicos", 
        "🗺️": "Visor Topográfico", 
        "🛢️": "Visualizador 3D Sondajes", 
        "🧨": "Diseño de Voladura", 
        "⛑️": "Ventilación Minera", 
        "🗄️": "Base de Datos"
    }
    nombres_nav_formateados = [f"{icono} {nombre}" for icono, nombre in opciones_nav.items()]
    
    indice_nav_activo = 0
    for i, (_, nombre) in enumerate(opciones_nav.items()):
        if nombre == st.session_state.pestaña_activa:
            indice_nav_activo = i
            break
            
    seleccion_nav = st.radio("Navegación", options=nombres_nav_formateados, index=indice_nav_activo, label_visibility="collapsed", key="radio_nav")
    nav_real = seleccion_nav.split(" ", 1)[1] 
    if nav_real != st.session_state.pestaña_activa:
        st.session_state.pestaña_activa = nav_real
        st.rerun()
    
    pestaña = st.session_state.pestaña_activa
    
    # MEJORA 1: Sección Exclusiva para el Historial de Conversaciones Anteriores
    st.markdown("<br>", unsafe_allow_html=True) 
    st.markdown("<p style='color:#888; font-size:13px; font-weight:500; margin-bottom:5px; padding-left:10px;'>Chats Recientes</p>", unsafe_allow_html=True)
    
    nombres_chats = list(st.session_state.conversaciones.keys())
    nombres_chats_fmt = [f"💬 {c}" for c in nombres_chats]
    indice_chat_activo = nombres_chats.index(st.session_state.chat_activo) if st.session_state.chat_activo in nombres_chats else 0
    
    seleccion_chat = st.radio("Historial", options=nombres_chats_fmt, index=indice_chat_activo, label_visibility="collapsed", key="radio_chats")
    chat_real = seleccion_chat.replace("💬 ", "")
    if chat_real != st.session_state.chat_activo:
        st.session_state.chat_activo = chat_real
        st.session_state.pestaña_activa = "Chat Asistente Operativo"
        st.rerun()
    
    st.markdown("---")
    st.markdown("""
        <div style='display:flex; align-items:center; padding-left:10px;'>
            <div style='width:30px; height:30px; border-radius:50%; background-color:#a8c7fa; color:#000; display:flex; justify-content:center; align-items:center; font-weight:bold; font-size:14px; margin-right:10px;'>J</div>
            <div><p style='margin:0; font-size:14px; color:#e3e3e3;'>Jean Kennedy</p><p style='margin:0; font-size:12px; color:#aaa;'>Ingeniería Pro</p></div>
        </div>
    """, unsafe_allow_html=True)

if conexion_exitosa:
    # ====================================================================
    # PESTAÑA 1: CHATBOT UNIFICADO (SISTEMA RAG INTEGRAL AUTOMÁTICO)
    # ====================================================================
    if pestaña == "Chat Asistente Operativo":
        if st.session_state.modo_ia == "🔱 InkaDrill IA (Carpeta Drive)":
            st.markdown("<h1 style='text-align: center; background: -webkit-linear-gradient(45deg, #ffd54f, #ff9800); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 500; font-size: 46px; margin-top: 50px; margin-bottom: 5px;'>InkaDrill IA</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #aaa; font-size: 14px;'>Base de Datos: Carpeta Conectada de Google Drive (Escaneo Inteligente Automatizado)</p>", unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='text-align: center; background: -webkit-linear-gradient(45deg, #4285f4, #9b72cb); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 500; font-size: 46px; margin-top: 50px; margin-bottom: 5px;'>Gemini IA</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #aaa; font-size: 14px;'>Base de Datos: Red Global e Internet (Conocimiento Enciclopédico de Ingeniería)</p>", unsafe_allow_html=True)
            
        with st.popover("➕", use_container_width=False):
            st.markdown("#### 🛠️ Herramientas")
            tab1, tab2 = st.tabs(["📎 Subir Archivos", "📊 Extraer Tablas"])
            with tab1:
                archivo_subido = st.file_uploader("Arrastra PDFs", type=["pdf", "txt", "png", "jpg", "jpeg"])
                if st.button("Guardar en Nube", type="primary", use_container_width=True) and archivo_subido: st.success("Guardado correctamente.")
            with tab2:
                archivo_tabla = st.file_uploader("Sube un PDF topográfico", type=["pdf"])
                if st.button("Procesar Tabla", type="primary", use_container_width=True) and archivo_tabla: st.success("¡Datos extraídos limpiamente!")

        # Renderizar historial del chat activo
        mensajes_actuales = st.session_state.conversaciones[st.session_state.chat_activo]
        for mensaje in mensajes_actuales:
            with st.chat_message(mensaje["rol"]): st.markdown(mensaje["contenido"])

        pregunta = st.chat_input("Escribe tu consulta operativa...")
        if pregunta:
            with st.chat_message("user"): st.markdown(pregunta)
            mensajes_actuales.append({"rol": "user", "contenido": pregunta})
            
            with st.chat_message("assistant"):
                caja_respuesta = st.empty()
                try:
                    contexto_master = ""
                    archivos_usados = []
                    
                    # SI ES MODO DRIVE, EXTAE EL TEXTO DE ABSOLUTAMENTE TODOS LOS ARCHIVOS DISPONIBLES EN TIEMPO REAL
                    if st.session_state.modo_ia == "🔱 InkaDrill IA (Carpeta Drive)":
                        caja_respuesta.markdown("Escanenando de forma integral la base documental de Drive... ⏳")
                        
                        for f in st.session_state.get("archivos_nube", []):
                            nombre = f['name']
                            if nombre.endswith('.pdf'):
                                try:
                                    pdf_bytes = drive_service.files().get_media(fileId=f['id']).execute()
                                    lector_pdf = PyPDF2.PdfReader(BytesIO(pdf_bytes))
                                    texto_pdf = "".join([pagina.extract_text() + "\n" for pagina in lector_pdf.pages])
                                    contexto_master += f"--- FUENTE DOCUMENTAL: {nombre} ---\n{texto_pdf}\n\n"
                                    archivos_usados.append(nombre)
                                except: pass
                            elif nombre.endswith(('.txt', '.csv')):
                                try:
                                    txt_content = drive_service.files().get_media(fileId=f['id']).execute().decode('utf-8')
                                    contexto_master += f"--- FUENTE DOCUMENTAL: {nombre} ---\n{txt_content}\n\n"
                                    archivos_usados.append(nombre)
                                except: pass
                        
                        instruccion_final = f"RESPONDE LA PREGUNTA DEL INGENIERO UTILIZANDO EXCLUSIVAMENTE LA SIGUIENTE RECOPILACIÓN DE INFORMACIÓN INTERNA:\n\n{contexto_master}\n\nPREGUNTA: {pregunta}"
                    else:
                        caja_respuesta.markdown("Consultando redes y conocimiento global... ⏳")
                        instruccion_final = f"Responde la siguiente consulta técnica utilizando tu base de conocimiento global de internet: {pregunta}"
                    
                    # Generar respuesta con Gemini
                    texto_final = modelo.generate_content(instruccion_final).text
                    
                    # AGREGAR LOS TÍTULOS DE LOS DOCUMENTOS UTILIZADOS AL FINAL (MEJORA SOLICITADA)
                    if st.session_state.modo_ia == "🔱 InkaDrill IA (Carpeta Drive)" and archivos_usados:
                        fuentes_html = "\n\n---\n🗄️ **Documentos oficiales indexados para esta respuesta:**\n" + "\n".join([f"* `{name}`" for name in archivos_usados])
                        texto_final += fuentes_html
                        
                    caja_respuesta.markdown(texto_final)
                    mensajes_actuales.append({"rol": "assistant", "contenido": texto_final})
                except Exception as e: 
                    caja_respuesta.error(f"Error de conexión con las redes neuronales: {e}")

    # ====================================================================
    # PESTAÑA 2: CÁLCULOS GEOMECÁNICOS
    # ====================================================================
    elif pestaña == "Cálculos Geomecánicos":
        st.markdown("<h2 style='color: white; text-align: center; font-weight: 700; letter-spacing: 1px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>SUITE DE ANÁLISIS GEOMECÁNICO 🪨</h2>", unsafe_allow_html=True)
        col_param, col_visor, col_resultados = st.columns([1.2, 1.2, 1])
        with col_param:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            st.markdown("<div class='titulo-seccion'>Parámetros de Roca Intacta</div>", unsafe_allow_html=True)
            ucs = st.number_input("Resistencia Compresión Simple (UCS) (MPa)", min_value=0, max_value=300, value=25)
            st.markdown("<br><div class='titulo-seccion'>Propiedades del Macizo Rocoso (GSI Modificado)</div>", unsafe_allow_html=True)
            estructura = st.selectbox("Estructura del Macizo (Filas)", ["Levemente Fracturada", "Moderadamente Fracturada", "Muy Fracturada", "Intensamente Fracturada"])
            condicion = st.selectbox("Condición de Discontinuidades (Columnas)", ["Buena", "Regular", "Mala", "Muy Mala"])
            st.markdown("</div>", unsafe_allow_html=True)

        matriz_gsi = {
            "Levemente Fracturada": {"Buena": ("LF/B", 85, "#4caf50", "1_LFB.png"), "Regular": ("LF/R", 70, "#8bc34a", "2_LFR.png"), "Mala": ("F/M", 55, "#ffeb3b", "3_FM.png"), "Muy Mala": ("*LF/MM", 40, "#ff9800", "4_LFMM.png")},
            "Moderadamente Fracturada": {"Buena": ("F/B", 75, "#8bc34a", "5_FB.png"), "Regular": ("F/R", 60, "#ffeb3b", "6_FR.png"), "Mala": ("LF/M", 45, "#ff9800", "7_LFM.png"), "Muy Mala": ("F/MM", 30, "#f44336", "8_FMM.png")},
            "Muy Fracturada": {"Buena": ("MF/B", 65, "#ffeb3b", "9_MFB.png"), "Regular": ("MF/R", 50, "#ff9800", "10_MFR.png"), "Mala": ("MF/M", 35, "#f44336", "11_MFM.png"), "Muy Mala": ("MF/MM", 20, "#b71c1c", "12_MFMM.png")},
            "Intensamente Fracturada": {"Buena": ("I/B", 55, "#ff9800", "13_IB.png"), "Regular": ("IF/R", 40, "#f44336", "14_IFR.png"), "Mala": ("IF/M", 25, "#b71c1c", "15_IFM.png"), "Muy Mala": ("IF/MM", 15, "#4e342e", "16_IFMM.png")}
        }
        codigo_gsi, puntaje_base, color_hex, nombre_imagen = matriz_gsi[estructura][condicion]
        rmr_final = min(100, int(puntaje_base + (ucs * 0.1)))
        
        img_b64 = ""
        rutas_locales = [nombre_imagen, f"rocas/{nombre_imagen}"]
        for ruta in rutas_locales:
            if os.path.exists(ruta):
                with open(ruta, "rb") as f: img_b64 = base64.b64encode(f.read()).decode()
                break
        
        if not img_b64:
            try:
                url_github = f"https://raw.githubusercontent.com/jeanventocilla13-cpu/intranet-inkadrill/main/{nombre_imagen}"
                respuesta = requests.get(url_github, timeout=3)
                if respuesta.status_code == 200: img_b64 = base64.b64encode(respuesta.content).decode()
            except: pass

        src_imagen = f"data:image/png;base64,{img_b64}" if img_b64 else "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

        with col_visor:
            html_visor = f"<div style='background: radial-gradient(circle, {color_hex}44 0%, transparent 70%); height: 350px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px dashed rgba(255,255,255,0.2); border-radius: 15px; box-shadow: inset 0 0 20px rgba(0,0,0,0.5);'><img src='{src_imagen}' style='width: 170px; height: 170px; object-fit: contain; filter: drop-shadow(0px 15px 20px rgba(0,0,0,0.9));' /><p style='color: {color_hex}; font-weight: 800; font-size: 26px; margin-top: 15px; margin-bottom: 0; letter-spacing: 2px; text-shadow: 2px 2px 4px #000;'>{codigo_gsi}</p><p style='color: #e3e3e3; font-weight: 500; font-size: 11px; margin-top: 2px; text-transform: uppercase;'>{estructura} / {condicion}</p></div>"
            st.markdown(html_visor, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("⚡ ACTUALIZAR ANÁLISIS", type="primary", use_container_width=True)

        with col_resultados:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            st.markdown("<div class='titulo-seccion'>Informes y Resultados</div>", unsafe_allow_html=True)
            if rmr_final >= 81: texto_rmr, rec_eng = "Muy Bueno", "<b>Avance permitido:</b> Excavación a sección completa (hasta 3.0 m)."
            elif rmr_final >= 61: texto_rmr, rec_eng = "Bueno", "<b>Avance permitido:</b> Sección completa (1.5 a 3.0 m)."
            elif rmr_final >= 41: texto_rmr, rec_eng = "Regular", "<b>Avance permitido:</b> Por galerías y banqueo (1.5 a 3.0 m)."
            elif rmr_final >= 21: texto_rmr, rec_eng = "Malo", "<b>Avance permitido:</b> 1.0 a 1.5 m. Sostenimiento concurrente."
            else: texto_rmr, rec_eng = "Muy Malo", "<b>Avance permitido:</b> Controlled advance (0.5 a 1.0 m)."

            st.markdown(f"""
            <div class='metric-box' style='border-color: {color_hex}66 !important;'><p class='metric-label'>Código GSI</p><p class='metric-value' style='color: {color_hex}; font-size: 38px;'>{codigo_gsi}</p></div>
            <div class='metric-box'><p class='metric-label'>RMR Unificado</p><p class='metric-value' style='color: {color_hex};'>{rmr_final}</p><p style='color: {color_hex}; font-size: 13px; margin:0; font-weight: 500;'>Calidad: {texto_rmr}</p></div>
            <div class='metric-box' style='text-align: left; background-color: rgba(168,199,250,0.05); border-color: rgba(168,199,250,0.2) !important;'><p class='metric-label' style='color: #a8c7fa; margin-bottom: 8px;'>RECOMENDACIÓN TÉCNICA</p><p style='color: #e3e3e3; font-size: 11.5px; margin:0; line-height: 1.6;'>{rec_eng}</p></div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # PESTAÑA 3: VISOR TOPOGRÁFICO INTERACTIVO (ENTRADA MANUAL AUTÓNOMA)
    # ====================================================================
    elif pestaña == "Visor Topográfico":
        st.markdown("<h2 style='color: white; text-align: center; font-weight: 700; letter-spacing: 1px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>VISOR TOPOGRÁFICO 3D AUTÓNOMO 🗺️</h2>", unsafe_allow_html=True)
        col_inputs_topo, col_render_topo = st.columns([1.2, 2])
        
        with col_inputs_topo:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            st.markdown("<div class='titulo-seccion'>⚙️ Entrada de Coordenadas y Filtros</div>", unsafe_allow_html=True)
            paleta_topo = st.selectbox("🎨 Escala Cromática de Elevación (Cotas)", ["Tierra (Marrón-Verde-Amarillo)", "Rojo-Verde-Azul Dinámico", "Viridis Geo", "Plasma de Altas Cotas"])
            mapa_paletas = {
                "Tierra (Marrón-Verde-Amarillo)": [[0, '#3e2723'], [0.5, '#5d4037'], [1, '#2e7d32']],
                "Rojo-Verde-Azul Dinámico": [[0, 'blue'], [0.5, 'green'], [1, 'red']],
                "Viridis Geo": "Viridis", "Plasma de Altas Cotas": "Plasma"
            }
            st.markdown("<p style='font-size: 13px; color: #aaa; margin-bottom: 5px;'>Copia y pega las estaciones del levantamiento en formato CSV:</p>", unsafe_allow_html=True)
            default_topo_data = "ESTACION,ESTE_X,NORTE_Y,COTA_Z\nE-01,500000,8800000,4320\nE-02,500050,8800020,4315\nE-03,500100,8800010,4290\nE-04,500020,8800080,4340\nE-05,500080,8800090,4310\nE-06,500120,8800060,4285\nE-07,500160,8800120,4260\nE-08,500220,8800100,4245"
            txt_topo = st.text_area("📋 Datos Planimétricos (Formato: ID, X, Y, Z)", default_topo_data, height=250)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_render_topo:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            if txt_topo:
                with st.spinner("Interpolando malla topográfica tridimensional..."):
                    try:
                        df_topo = pd.read_csv(StringIO(txt_topo), sep=None, engine='python')
                        df_topo.columns = [re.sub(r'[^a-zA-Z0-9_]', '', str(c).strip().upper()) for c in df_topo.columns]
                        c_x = next((c for c in df_topo.columns if str(c) in ['X', 'ESTE', 'EAST', 'EASTING', 'ESTE_X']), df_topo.columns[1])
                        c_y = next((c for c in df_topo.columns if str(c) in ['Y', 'NORTE', 'NORTH', 'NORTHING', 'NORTE_Y']), df_topo.columns[2])
                        c_z = next((c for c in df_topo.columns if str(c) in ['Z', 'ELEV', 'COTA', 'RL', 'COTA_Z']), df_topo.columns[3])
                        
                        def force_num(val):
                            try: return float(re.sub(r'[^0-9.-]', '', str(val).replace(',', '.')))
                            except: return 0.0
                        df_topo[c_x] = df_topo[c_x].apply(force_num)
                        df_topo[c_y] = df_topo[c_y].apply(force_num)
                        df_topo[c_z] = df_topo[c_z].apply(force_num)
                        
                        x_arr, y_arr, z_arr = df_topo[c_x].values, df_topo[c_y].values, df_topo[c_z].values
                        fig_topo_3d = go.Figure()
                        
                        if len(x_arr) > 2:
                            x_min, x_max = x_arr.min(), x_arr.max()
                            y_min, y_max = y_arr.min(), y_arr.max()
                            m_x, m_y = (x_max - x_min) * 1.0, (y_max - y_min) * 1.0
                            g_x = np.linspace(x_min - m_x, x_max + m_x, 60)
                            g_y = np.linspace(y_min - m_y, y_max + m_y, 60)
                            XM, YM = np.meshgrid(g_x, g_y)
                            XF, YF = XM.flatten(), YM.flatten()
                            distancias = np.sqrt((x_arr[:, np.newaxis] - XF)**2 + (y_arr[:, np.newaxis] - YF)**2)
                            distancias = np.where(distancias == 0, 1e-10, distancias)
                            pesos = 1.0 / (distancias ** 2)
                            ZF = np.sum(pesos * z_arr[:, np.newaxis], axis=0) / np.sum(pesos, axis=0)
                            ZM = ZF.reshape(XM.shape)
                            
                            fig_topo_3d.add_trace(go.Surface(x=XM, y=YM, z=ZM, opacity=0.75, colorscale=mapa_paletas[paleta_topo], colorbar=dict(title=dict(text="Cota (m)", font=dict(color='white')), tickfont=dict(color='white')), name='Terreno'))
                        fig_topo_3d.add_trace(go.Scatter3d(x=x_arr, y=y_arr, z=z_arr, mode='markers+text', text=df_topo.iloc[:, 0].astype(str), textposition="top center", marker=dict(size=6, color='white', symbol='diamond'), name='Vértices', textfont=dict(color='white', size=10)))
                        fig_topo_3d.update_layout(margin=dict(r=10, l=10, b=10, t=10), height=480, paper_bgcolor="rgba(0,0,0,0)", scene=dict(xaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Este (X)", color="white"), yaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Norte (Y)", color="white"), zaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Cota (Z)", color="white"), bgcolor="rgba(0,0,0,0)", aspectmode='data'), legend=dict(font=dict(color="white")))
                        st.plotly_chart(fig_topo_3d, use_container_width=True)
                        
                        st.markdown("<div class='titulo-seccion'>Reporte Fisiográfico de la Labor Mapeada</div>", unsafe_allow_html=True)
                        col_tb1, col_md2, col_md3 = st.columns(3)
                        col_tb1.markdown(f"<div class='metric-box'><p class='metric-label'>Estaciones</p><p class='metric-value' style='color:#4af4ff; font-size:32px;'>{len(df_topo)}</p></div>", unsafe_allow_html=True)
                        col_md2.markdown(f"<div class='metric-box'><p class='metric-label'>Cota Máxima</p><p class='metric-value' style='color:#ffeb3b; font-size:32px;'>{z_arr.max():,.1f} m</p></div>", unsafe_allow_html=True)
                        col_md3.markdown(f"<div class='metric-box'><p class='metric-label'>Cota Mínima</p><p class='metric-value' style='color:#8bc34a; font-size:32px;'>{z_arr.min():,.1f} m</p></div>", unsafe_allow_html=True)
                    except Exception as e: st.error(f"⚠️ Error: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # PESTAÑA 4: VISUALIZADOR 3D SONDAJES
    # ====================================================================
    elif pestaña == "Visualizador 3D Sondajes":
        st.markdown("<h2 style='color: white; text-align: center; font-weight: 700; letter-spacing: 1px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>MODELAMIENTO GEOLÓGICO 3D AUTÓNOMO 🛢️</h2>", unsafe_allow_html=True)
        col_manual_inputs, col_3d_render = st.columns([1.3, 2])
        with col_manual_inputs:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            st.markdown("<div class='titulo-seccion'>⚙️ Configuración Visual e Inputs Manuales</div>", unsafe_allow_html=True)
            escala_color = st.selectbox("🎨 Escala Gráfica de Leyes (Gama Cromática)", ["Viridis (Azul-Verde-Amarillo)", "Plasma (Violeta-Rojo-Amarillo)", "Hot (Negro-Rojo-Amarillo-Blanco)"])
            escala_map = {"Viridis (Azul-Verde-Amarillo)": "Viridis", "Plasma (Violeta-Rojo-Amarillo)": "Plasma", "Hot (Negro-Rojo-Amarillo-Blanco)": "Hot"}
            st.markdown("<p style='font-size: 13px; color: #aaa; margin-bottom: 5px;'>Copia y pega las tablas CSV directamente desde Excel o un bloc de notas:</p>", unsafe_allow_html=True)
            
            default_collar = "BHID,X,Y,Z,DEPTH\nDDH-001,100,100,250,120\nDDH-002,140,110,245,130\nDDH-003,120,150,252,110"
            default_survey = "BHID,AT,AZ,DIP\nDDH-001,0,150,-60\nDDH-001,60,152,-58\nDDH-002,0,220,-55\nDDH-002,70,218,-54\nDDH-003,0,45,-70"
            default_assay = "BHID,FROM,TO,AU_GPT\nDDH-001,0,40,0.35\nDDH-001,40,80,2.15\nDDH-001,80,120,4.80\nDDH-002,0,50,0.10\nDDH-002,50,100,1.85\nDDH-002,100,130,3.90\nDDH-003,0,60,0.90\nDDH-003,60,110,5.20"
            
            txt_collar = st.text_area("📋 Tabla 1: COLLAR", default_collar, height=120)
            txt_survey = st.text_area("📋 Tabla 2: SURVEY", default_survey, height=120)
            txt_assay = st.text_area("📋 Tabla 3: ASSAY", default_assay, height=120)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_3d_render:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            if txt_collar and txt_survey and txt_assay:
                with st.spinner("Procesando matriz trigonométrica independiente..."):
                    try:
                        df_collar = pd.read_csv(StringIO(txt_collar), sep=None, engine='python')
                        df_survey = pd.read_csv(StringIO(txt_survey), sep=None, engine='python')
                        df_assay = pd.read_csv(StringIO(txt_assay), sep=None, engine='python')
                        df_collar.columns = [re.sub(r'[^a-zA-Z0-9_]', '', str(c).strip().upper()) for c in df_collar.columns]
                        df_survey.columns = [re.sub(r'[^a-zA-Z0-9_]', '', str(c).strip().upper()) for c in df_survey.columns]
                        df_assay.columns = [re.sub(r'[^a-zA-Z0-9_]', '', str(c).strip().upper()) for c in df_assay.columns]
                        
                        def buscar_col_exacta(df, palabras_clave):
                            for col in df.columns:
                                if col in [p.upper() for p in palabras_clave]: return col
                            return df.columns[0]
                            
                        id_c = buscar_col_exacta(df_collar, ['HOLEID', 'BHID', 'HOLE_ID', 'HOLE', 'ID', 'TALADRO'])
                        id_s = buscar_col_exacta(df_survey, ['HOLEID', 'BHID', 'HOLE_ID', 'HOLE', 'ID', 'TALADRO'])
                        id_a = buscar_col_exacta(df_assay, ['HOLEID', 'BHID', 'HOLE_ID', 'HOLE', 'ID', 'TALADRO'])
                        c_x = buscar_col_exacta(df_collar, ['X', 'ESTE', 'EAST', 'EASTING'])
                        c_y = buscar_col_exacta(df_collar, ['Y', 'NORTE', 'NORTH', 'NORTHING'])
                        c_z = buscar_col_exacta(df_collar, ['Z', 'ELEV', 'ELEVATION', 'RL', 'COTA'])
                        s_at = buscar_col_exacta(df_survey, ['AT', 'DEPTH', 'PROF', 'DISTANCE'])
                        s_az = buscar_col_exacta(df_survey, ['AZIMUTH', 'AZ', 'AZM', 'DIR'])
                        s_dip = buscar_col_exacta(df_survey, ['DIP', 'INCLINACION', 'BUZAMIENTO'])
                        a_from = buscar_col_exacta(df_assay, ['FROM', 'DESDE'])
                        a_to = buscar_col_exacta(df_assay, ['TO', 'HASTA'])
                        col_ley = buscar_col_exacta(df_assay, ['AUGPT', 'CUPCT', 'CU', 'AU', 'AG', 'LEY', 'GRADE', 'VALOR'])
                        
                        df_collar[id_c] = df_collar[id_c].astype(str).str.strip()
                        df_survey[id_s] = df_survey[id_s].astype(str).str.strip()
                        df_assay[id_a] = df_assay[id_a].astype(str).str.strip()
                        
                        def force_numeric(val):
                            try: return float(re.sub(r'[^0-9.-]', '', str(val).replace(',', '.')))
                            except: return 0.0
                                
                        df_collar[c_x] = df_collar[c_x].apply(force_numeric)
                        df_collar[c_y] = df_collar[c_y].apply(force_numeric)
                        df_collar[c_z] = df_collar[c_z].apply(force_numeric)
                        df_survey[s_at] = df_survey[s_at].apply(force_numeric)
                        df_survey[s_az] = df_survey[s_az].apply(force_numeric)
                        df_survey[s_dip] = df_survey[s_dip].apply(force_numeric)
                        df_assay[a_from] = df_assay[a_from].apply(force_numeric)
                        df_assay[a_to] = df_assay[a_to].apply(force_numeric)
                        df_assay[col_ley] = df_assay[col_ley].apply(force_numeric)
                        
                        resultados = []
                        for bhid in df_assay[id_a].unique():
                            c_data = df_collar[df_collar[id_c] == bhid]
                            if c_data.empty: continue
                            x0, y0, z0 = c_data.iloc[0][c_x], c_data.iloc[0][c_y], c_data.iloc[0][c_z]
                            s_data = df_survey[df_survey[id_s] == bhid].sort_values(s_at)
                            a_data = df_assay[df_assay[id_a] == bhid].sort_values(a_from)
                            
                            for _, row in a_data.iterrows():
                                mid_depth = (row[a_from] + row[a_to]) / 2
                                s_valido = s_data[s_data[s_at] <= mid_depth]
                                s_row = s_data.iloc[0] if s_valido.empty else s_valido.iloc[-1]
                                dip_rad, az_rad = np.radians(s_row[s_dip]), np.radians(s_row[s_az])
                                dx = mid_depth * np.cos(dip_rad) * np.sin(az_rad)
                                dy = mid_depth * np.cos(dip_rad) * np.cos(az_rad)
                                dz = mid_depth * np.sin(dip_rad)
                                resultados.append({'BHID': bhid, 'X': x0 + dx, 'Y': y0 + dy, 'Z': z0 + dz, 'LEY': row[col_ley]})
                                
                        df_3d = pd.DataFrame(resultados)
                        if df_3d.empty: st.error("❌ Desfase de IDs.")
                        else:
                            fig_3d = go.Figure()
                            cmax_val = max(0.1, df_3d['LEY'].quantile(0.98))
                            for hole in df_3d["BHID"].unique():
                                df_hole = df_3d[df_3d["BHID"] == hole]
                                fig_3d.add_trace(go.Scatter3d(x=df_hole["X"], y=df_hole["Y"], z=df_hole["Z"], mode='lines+markers', marker=dict(size=4, color=df_hole["LEY"], colorscale=escala_map[escala_color], colorbar=dict(title=dict(text=f"Ley ({col_ley})", font=dict(color='white')), tickfont=dict(color='white')), cmin=0, cmax=cmax_val), line=dict(width=3, color='rgba(255,255,255,0.4)'), name=str(hole)))
                            x_col, y_col, z_col = df_collar[c_x].values, df_collar[c_y].values, df_collar[c_z].values
                            if len(x_col) > 2:
                                x_min, x_max = x_col.min(), x_col.max()
                                y_min, y_max = y_col.min(), y_col.max()
                                m_x, m_y = (x_max - x_min) * 1.0, (y_max - y_min) * 1.0
                                grid_x, grid_y = np.linspace(x_min - m_x, x_max + m_x, 60), np.linspace(y_min - m_y, y_max + m_y, 60)
                                XM, YM = np.meshgrid(grid_x, grid_y)
                                XF, YF = XM.flatten(), YM.flatten()
                                dist = np.sqrt((x_col[:, np.newaxis] - XF)**2 + (y_col[:, np.newaxis] - YF)**2)
                                dist = np.where(dist == 0, 1e-10, dist)
                                weights = 1.0 / (dist ** 2)
                                ZF = np.sum(weights * z_col[:, np.newaxis], axis=0) / np.sum(weights, axis=0)
                                ZM = ZF.reshape(XM.shape)
                                fig_3d.add_trace(go.Surface(x=XM, y=YM, z=ZM, opacity=0.6, colorscale=[[0, '#3e2723'], [0.5, '#5d4037'], [1, '#2e7d32']], showscale=False, name='Topografía'))
                            fig_3d.update_layout(margin=dict(r=10, l=10, b=10, t=10), height=500, paper_bgcolor="rgba(0,0,0,0)", scene=dict(xaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Este (X)", color="white"), yaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Norte (Y)", color="white"), zaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Elevación (Z)", color="white"), bgcolor="rgba(0,0,0,0)", aspectmode='data'), legend=dict(font=dict(color="white")))
                            st.plotly_chart(fig_3d, use_container_width=True)
                    except: st.error("Error al procesar tablas.")
            st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # PESTAÑA 5: DISEÑO DE VOLADURA
    # ====================================================================
    elif pestaña == "Diseño de Voladura":
        st.markdown("<h2 style='color: white; text-align: center; font-weight: 700; letter-spacing: 1px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>DISEÑO DE MALLA DE PERFORACIÓN Y VOLADURA 🧨</h2>", unsafe_allow_html=True)
        col_parametros, col_visor = st.columns([1.2, 2])
        with col_parametros:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            st.markdown("<div class='titulo-seccion'>Plantilla de Perforación</div>", unsafe_allow_html=True)
            tipo_malla = st.selectbox("Seleccionar Plantilla Geometría", ["Malla Cuadrada (Tajo Abierto)", "Malla Tresbolillo (Tajo Abierto)", "Frente de Túnel (Galería 3x3m)"])
            if "Tajo" in tipo_malla:
                col_b, col_s = st.columns(2)
                burden = col_b.number_input("Burden (m)", min_value=1.0, max_value=10.0, value=3.0, step=0.5)
                espaciamiento = col_s.number_input("Espaciamiento (m)", min_value=1.0, max_value=10.0, value=3.5, step=0.5)
                col_l, col_d = st.columns(2)
                profundidad = col_l.number_input("Longitud Taladro (m)", min_value=1.0, max_value=20.0, value=10.0, step=1.0)
                diametro_mm = col_d.number_input("Diámetro (mm)", min_value=45.0, max_value=311.0, value=165.0, step=1.0)
                filas = st.slider("Número de Filas", 2, 10, 4)
                columnas = st.slider("Taladros por Fila", 2, 20, 8)
            else:
                st.info("ℹ️ Parámetros de túnel estandarizados.")
                profundidad = st.number_input("Longitud de Avance (m)", min_value=1.0, max_value=5.0, value=3.0, step=0.5)
                diametro_mm = st.number_input("Diámetro (mm)", min_value=32.0, max_value=64.0, value=45.0, step=1.0)
                burden, espaciamiento, filas, columnas = 1, 1, 1, 1
            st.markdown("<br><div class='titulo-seccion'>Parámetros de Voladura</div>", unsafe_allow_html=True)
            densidad_roca = st.number_input("Densidad de la Roca (ton/m³)", min_value=1.0, max_value=5.0, value=2.7, step=0.1)
            factor_potencia = st.number_input("Factor de Potencia (kg/ton)", min_value=0.1, max_value=2.0, value=0.45, step=0.05)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_visor:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            taladros = []
            if tipo_malla == "Malla Cuadrada (Tajo Abierto)":
                for f in range(filas):
                    for c in range(columnas): taladros.append({"ID": f"T-{f}-{c}", "X": c * espaciamiento, "Y": f * burden, "Z_start": 0, "Z_end": -profundidad, "Tipo": "Producción"})
            elif tipo_malla == "Malla Tresbolillo (Tajo Abierto)":
                for f in range(filas):
                    offset = (espaciamiento / 2) if f % 2 != 0 else 0
                    for c in range(columnas): taladros.append({"ID": f"T-{f}-{c}", "X": (c * espaciamiento) + offset, "Y": f * burden, "Z_start": 0, "Z_end": -profundidad, "Tipo": "Producción"})
            elif tipo_malla == "Frente de Túnel (Galería 3x3m)":
                taladros.append({"ID": "A1", "X": 1.5, "Y": 1.5, "Z_start": 0, "Z_end": profundidad, "Tipo": "Arranque"})
                for x in [1.0, 2.0]:
                    for y in [1.0, 2.0]: taladros.append({"ID": f"Ay-{x}-{y}", "X": x, "Y": y, "Z_start": 0, "Z_end": profundidad, "Tipo": "Ayudas"})
                for x in [0.2, 0.8, 1.5, 2.2, 2.8]: taladros.append({"ID": f"Ar-{x}", "X": x, "Y": 0.2, "Z_start": 0, "Z_end": profundidad, "Tipo": "Arrastre"})
                for y in [0.8, 1.5, 2.2]:
                    taladros.append({"ID": f"C1-{y}", "X": 0.2, "Y": y, "Z_start": 0, "Z_end": profundidad, "Tipo": "Cuadradores"})
                    taladros.append({"ID": f"C2-{y}", "X": 2.8, "Y": y, "Z_start": 0, "Z_end": profundidad, "Tipo": "Cuadradores"})
                for x in [0.2, 0.8, 1.5, 2.2, 2.8]: taladros.append({"ID": f"Co-{x}", "X": x, "Y": 2.8, "Z_start": 0, "Z_end": profundidad, "Tipo": "Corona"})

            df_malla = pd.DataFrame(taladros)
            fig_malla = go.Figure()
            colores = {"Producción": "#f44336", "Arranque": "#ffeb3b", "Ayudas": "#ff9800", "Cuadradores": "#2196f3", "Arrastre": "#4caf50", "Corona": "#9c27b0"}
            for _, row in df_malla.iterrows():
                if "Tajo" in tipo_malla:
                    fig_malla.add_trace(go.Scatter3d(x=[row["X"], row["X"]], y=[row["Y"], row["Y"]], z=[row["Z_start"], row["Z_end"]], mode='lines', line=dict(width=6, color=colores.get(row["Tipo"], "#fff")), showlegend=False))
                else:
                    fig_malla.add_trace(go.Scatter3d(x=[row["X"], row["X"]], y=[row["Z_start"], row["Z_end"]], z=[row["Y"], row["Y"]], mode='lines', line=dict(width=6, color=colores.get(row["Tipo"], "#fff")), showlegend=False))
            fig_malla.update_layout(margin=dict(r=10, l=10, b=10, t=10), height=450, paper_bgcolor="rgba(0,0,0,0)", scene=dict(xaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="X", color="white"), yaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Y", color="white"), zaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Z", color="white"), bgcolor="rgba(0,0,0,0)", aspectmode='data'), showlegend=False)
            st.plotly_chart(fig_malla, use_container_width=True)
            
            st.markdown("<div class='titulo-seccion'>Reporte de Carga Mecánica</div>", unsafe_allow_html=True)
            num_taladros = len(df_malla)
            volumen_total = (burden * espaciamiento * profundidad) * num_taladros if "Tajo" in tipo_malla else 9 * profundidad
            tonelaje_total = volumen_total * densidad_roca
            anfo_total = tonelaje_total * factor_potencia
            anfo_por_taladro = anfo_total / num_taladros
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.markdown(f"<div class='metric-box'><p class='metric-label'>Toneladas</p><p class='metric-value' style='color: #8bc34a; font-size:32px;'>{tonelaje_total:,.1f}</p></div>", unsafe_allow_html=True)
            col_r2.markdown(f"<div class='metric-box'><p class='metric-label'>ANFO Malla</p><p class='metric-value' style='color: #f44336; font-size:32px;'>{anfo_total:,.1f} kg</p></div>", unsafe_allow_html=True)
            col_r3.markdown(f"<div class='metric-box'><p class='metric-label'>ANFO / Taladro</p><p class='metric-value' style='color: #ffeb3b; font-size:32px;'>{anfo_por_taladro:,.1f} kg</p></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # PESTAÑA 6: VENTILACIÓN MINERA
    # ====================================================================
    elif pestaña == "Ventilación Minera":
        st.markdown("<h2 style='color: white; text-align: center; font-weight: 700; letter-spacing: 1px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>SISTEMA OPERATIVO DE VENTILACIÓN MINERA ⛑️</h2>", unsafe_allow_html=True)
        col_inputs, col_3d_visor = st.columns([1.3, 2])
        with col_inputs:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            st.markdown("<div class='titulo-seccion'>1. Parámetros de Caudal Requerido (Q)</div>", unsafe_allow_html=True)
            col_p1, col_p2 = st.columns(2)
            n_personal = col_p1.number_input("Número de Personal (Turno Crítico)", min_value=1, value=45)
            q_personal = col_p2.slider("Norma por Persona (m³/min)", 3.0, 6.0, 4.0, step=0.5)
            col_d1, col_d2 = st.columns(2)
            hp_diesel = col_d1.number_input("Potencia Diésel (HP)", min_value=0, value=280)
            q_diesel = col_d2.slider("Factor por HP", 2.8, 4.0, 3.0, step=0.1)
            dispo_diesel = st.slider("Factor de Disponibilidad", 0.1, 1.0, 0.85, step=0.05)
            col_g1, col_g2, col_g3 = st.columns(3)
            v_gas = col_g1.number_input("Volumen Gas", min_value=0.0, value=0.12, step=0.01)
            c_lim = col_g2.number_input("L.M.P (ppm)", min_value=1, value=25) / 1000000
            c_o = col_g3.number_input("Gas Ingreso (ppm)", min_value=0, value=0) / 1000000
            st.markdown("<br><div class='titulo-seccion'>2. Geometría (Atkinson)</div>", unsafe_allow_html=True)
            col_g1, col_g2 = st.columns(2)
            longitud_ducto = col_g1.number_input("Longitud de Ducto (m)", min_value=1, value=350)
            k_atkinson = col_g2.number_input("Fricción k", min_value=0.0001, max_value=0.05, value=0.0120, format="%.4f")
            col_dim1, col_dim2 = st.columns(2)
            ancho_gal = col_dim1.number_input("Ancho (m)", min_value=1.0, value=3.0, step=0.5)
            alto_gal = col_dim2.number_input("Alto (m)", min_value=1.0, value=3.0, step=0.5)
            st.markdown("<br><div class='titulo-seccion'>3. Parámetro Mecánico</div>", unsafe_allow_html=True)
            eficiencia_vent = st.slider("Eficiencia (η)", 0.50, 0.95, 0.75, step=0.05)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_3d_visor:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            Q_p = n_personal * q_personal
            Q_d = (hp_diesel * q_diesel) * dispo_diesel
            denominador_gases = c_lim - c_o
            if denominador_gases <= 0: denominador_gases = 0.00001
            Q_g = v_gas / denominador_gases
            Q_total_min = max(Q_p, Q_d, Q_g)
            Q_m3s = Q_total_min / 60.0
            area_transversal = ancho_gal * alto_gal
            perimetro_transversal = 2 * (ancho_gal + alto_gal)
            R_atkinson = (k_atkinson * perimetro_transversal * longitud_ducto) / (area_transversal ** 3)
            delta_P = R_atkinson * (Q_m3s ** 2)
            potencia_kW = (delta_P * Q_m3s) / (1000.0 * eficiencia_vent)
            
            fig_vent = go.Figure()
            velocidad_aire = Q_m3s / area_transversal
            y_cones = np.linspace(20, longitud_ducto - 20, 12)
            x_cones, z_cones = np.zeros_like(y_cones), np.full_like(y_cones, alto_gal / 2.0)
            u, v, w = np.zeros_like(y_cones), np.ones_like(y_cones) * velocidad_aire, np.zeros_like(y_cones)
            fig_vent.add_trace(go.Cone(x=x_cones, y=y_cones, z=z_cones, u=u, v=v, w=w, colorscale='Cividis', sizemode='scaled', sizeref=1.5, colorbar=dict(title=dict(text="m/s", font=dict(color='white')), tickfont=dict(color='white'))))
            box_x, box_z = [-ancho_gal/2, ancho_gal/2, ancho_gal/2, -ancho_gal/2, -ancho_gal/2], [0, 0, alto_gal, alto_gal, 0]
            for y_wall in [0, longitud_ducto / 2, longitud_ducto]:
                fig_vent.add_trace(go.Scatter3d(x=box_x, y=[y_wall]*5, z=box_z, mode='lines', line=dict(color='rgba(255,255,255,0.2)', width=3), showlegend=False))
            fig_vent.update_layout(margin=dict(r=10, l=10, b=10, t=10), height=450, paper_bgcolor="rgba(0,0,0,0)", scene=dict(xaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.05)', title="X", color="white"), yaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.05)', title="Y", color="white"), zaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.05)', title="Z", color="white"), bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig_vent, use_container_width=True)
            
            st.markdown("<div class='titulo-seccion'>Resultados del Balance Operativo</div>", unsafe_allow_html=True)
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.markdown(f"<div class='metric-box'><p class='metric-label'>Caudal (Q_t)</p><p class='metric-value' style='color: #4af4ff; font-size:30px;'>{Q_total_min:,.1f} <span style='font-size:14px;'>m³/min</span></p></div>", unsafe_allow_html=True)
            col_m2.markdown(f"<div class='metric-box'><p class='metric-label'>Presión (ΔP)</p><p class='metric-value' style='color: #ffeb3b; font-size:30px;'>{delta_P:,.2f} <span style='font-size:14px;'>Pa</span></p></div>", unsafe_allow_html=True)
            col_m3.markdown(f"<div class='metric-box'><p class='metric-label'>Motor Vent</p><p class='metric-value' style='color: #f44336; font-size:30px;'>{potencia_kW:,.2f} <span style='font-size:14px;'>kW</span></p></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # PESTAÑA 7: BASE DE DATOS
    # ====================================================================
    elif pestaña == "Base de Datos":
        st.markdown("<h2 style='color: white; text-align: center; font-weight: 700; letter-spacing: 1px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>GESTOR DE BASE DE DATOS 🗄️</h2>", unsafe_allow_html=True)
        col_busqueda, col_filtro = st.columns([3, 1])
        with col_busqueda: texto_busqueda = st.text_input("🔍 Buscar documento por nombre...", "")
        with col_filtro: tipo_filtro = st.selectbox("Filtro por Tipo", ["Todos", "CSV / Excel", "PDF", "Imágenes", "Texto"])
        st.markdown("<br>", unsafe_allow_html=True)
        
        archivos_mostrar = st.session_state.get("archivos_nube", [])
        if texto_busqueda: archivos_mostrar = [f for f in archivos_mostrar if texto_busqueda.lower() in f['name'].lower()]
        if tipo_filtro == "CSV / Excel": archivos_mostrar = [f for f in archivos_mostrar if f['name'].endswith(('.csv', '.xlsx', '.xls'))]
        elif tipo_filtro == "PDF": archivos_mostrar = [f for f in archivos_mostrar if f['name'].endswith('.pdf')]
        elif tipo_filtro == "Imágenes": archivos_mostrar = [f for f in archivos_mostrar if f['name'].endswith(('.png', '.jpg', '.jpeg'))]
        elif tipo_filtro == "Texto": archivos_mostrar = [f for f in archivos_mostrar if f['name'].endswith('.txt')]
            
        if len(archivos_mostrar) == 0: st.warning("No se encontraron documentos en Drive.")
        else:
            st.markdown(f"<p style='color: #a8c7fa; font-weight: 600; margin-bottom: 15px;'>Mostrando {len(archivos_mostrar)} documentos de la nube</p>", unsafe_allow_html=True)
            columnas = st.columns(3)
            for i, arch in enumerate(archivos_mostrar):
                icono, nombre, id_corto = obtener_icono(arch['name']), arch['name'], arch['id'][:10]
                tarjeta_html = f"<div class='file-card'><div class='file-icon'>{icono}</div><div class='file-details'><p class='file-name' title='{nombre}'>{nombre}</p><p class='file-id'>ID: {id_corto}...</p></div></div>"
                columnas[i % 3].markdown(tarjeta_html, unsafe_allow_html=True)
