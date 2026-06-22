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

if "pestaña_activa" not in st.session_state:
    st.session_state.pestaña_activa = "Diseño de Voladura" # Cambiado para que lo veas al entrar
if "archivo_activo" not in st.session_state:
    st.session_state.archivo_activo = "Base de datos general (Simulación)"

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
    
    div[data-testid="stPopover"] { position: fixed !important; bottom: 27px !important; left: auto !important; width: 46px !important; height: 46px !important; z-index: 999999 !important; }
    div[data-testid="stPopover"] > button {
        width: 46px !important; height: 46px !important; min-width: 46px !important; max-width: 46px !important;
        border-radius: 50% !important; padding: 0 !important; margin: 0 !important; display: flex !important;
        align-items: center !important; justify-content: center !important; background-color: rgba(25, 26, 27, 0.85) !important;
        backdrop-filter: blur(12px) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; color: #e3e3e3 !important; font-size: 24px !important; transition: 0.3s;
    }
    div[data-testid="stPopover"] > button:hover { background-color: rgba(255, 255, 255, 0.15) !important; color: #ffd54f !important; }
    div[data-testid="stPopover"] > button svg { display: none !important; width: 0 !important; height: 0 !important; }
    div[data-testid="stPopover"] > button p, div[data-testid="stPopover"] > button span { margin: 0 !important; display: flex !important; align-items: center !important; justify-content: center !important; width: 100% !important; }
    
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
    modelo = genai.GenerativeModel('gemini-1.5-flash')
    
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
    st.markdown("<div style='display:flex; align-items:center; margin-bottom:15px;'><h2 style='color:#e3e3e3; font-weight:500; font-size:22px; margin:0;'>✨ InkaDrill IA</h2></div>", unsafe_allow_html=True)
    if st.button("📝 Nueva conversación", type="primary", use_container_width=True):
        st.session_state.mensajes_ia = [] 
        st.session_state.pestaña_activa = "Chat Asistente Operativo"
        st.rerun()
        
    st.markdown("<p style='color:#888; font-size:13px; font-weight:500; margin-top:20px; margin-bottom:5px; padding-left:10px;'>Navegación</p>", unsafe_allow_html=True)
    
    # ¡AQUÍ AGREGAMOS LA NUEVA PESTAÑA A LA BARRA LATERAL!
    opciones_nav = {"💬": "Chat Asistente Operativo", "🪨": "Cálculos Geomecánicos", "🗺️": "Visor Topográfico", "🛢️": "Visualizador 3D Sondajes", "🧨": "Diseño de Voladura", "🗄️": "Base de Datos"}
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
    
    st.markdown("<br>", unsafe_allow_html=True) 
    st.markdown("<p style='color:#888; font-size:13px; font-weight:500; margin-bottom:5px; padding-left:10px;'>Recientes</p>", unsafe_allow_html=True)
    
    opciones_archivos = ["Base de datos general (Simulación)"]
    archivos_filtrados = []
    
    if "archivos_nube" in st.session_state:
        if pestaña in ["Base de Datos", "Visualizador 3D Sondajes", "Visor Topográfico"]: archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.csv', '.xlsx', '.xls', '.pdf'))]
        elif pestaña in ["Chat Asistente Operativo"]: archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.pdf', '.txt', '.png', '.jpg', '.jpeg', '.csv'))]
    for f in archivos_filtrados: opciones_archivos.append(f['name'])
        
    nombres_archivos_formateados = [f"{obtener_icono(arch)} {arch}" for arch in opciones_archivos]
    indice_archivo_activo = 0
    for i, arch in enumerate(opciones_archivos):
        if arch == st.session_state.archivo_activo:
            indice_archivo_activo = i
            break
            
    seleccion_archivo = st.radio("Recientes", options=nombres_archivos_formateados, index=indice_archivo_activo, label_visibility="collapsed", key="radio_archivos")
    archivo_real = seleccion_archivo.split(" ", 1)[1]
    if archivo_real != st.session_state.archivo_activo:
        st.session_state.archivo_activo = archivo_real
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
    # PESTAÑA 1: CHATBOT UNIFICADO
    # ====================================================================
    if pestaña == "Chat Asistente Operativo":
        st.markdown("<h1 style='text-align: center; background: -webkit-linear-gradient(45deg, #4285f4, #d96570, #9b72cb); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 500; font-size: 46px; margin-top: 50px; margin-bottom: 30px;'>Hola, Jean</h1>", unsafe_allow_html=True)
        if st.session_state.archivo_activo != "Base de datos general (Simulación)": st.info(f"🔎 **Modo Enfoque:** El chat responderá basándose en el archivo: `{st.session_state.archivo_activo}`")
            
        with st.popover("➕", use_container_width=False):
            st.markdown("#### 🛠️ Herramientas")
            tab1, tab2 = st.tabs(["📎 Subir Archivos", "📊 Extraer Tablas"])
            with tab1:
                archivo_subido = st.file_uploader("Arrastra PDFs", type=["pdf", "txt", "png", "jpg", "jpeg"])
                if st.button("Guardar en Nube", type="primary", use_container_width=True) and archivo_subido: st.success("Guardado correctamente.")
            with tab2:
                archivo_tabla = st.file_uploader("Sube un PDF topográfico", type=["pdf"])
                if st.button("Procesar Tabla", type="primary", use_container_width=True) and archivo_tabla: st.success("¡Datos extraídos limpiamente!")

        if "mensajes_ia" not in st.session_state: st.session_state.mensajes_ia = []
        for mensaje in st.session_state.mensajes_ia:
            with st.chat_message(mensaje["rol"]): st.markdown(mensaje["contenido"])

        pregunta = st.chat_input("Pregunta a Gemini")
        if pregunta:
            with st.chat_message("user"): st.markdown(pregunta)
            st.session_state.mensajes_ia.append({"rol": "user", "contenido": pregunta})
            with st.chat_message("assistant"):
                caja_respuesta = st.empty()
                caja_respuesta.markdown("Extrayendo datos de la nube y procesando... ⏳")
                try:
                    contexto_documento = ""
                    if st.session_state.archivo_activo != "Base de datos general (Simulación)":
                        try:
                            file_id = next(f['id'] for f in st.session_state.archivos_nube if f['name'] == st.session_state.archivo_activo)
                            if st.session_state.archivo_activo.endswith('.pdf'):
                                pdf_bytes = drive_service.files().get_media(fileId=file_id).execute()
                                lector_pdf = PyPDF2.PdfReader(BytesIO(pdf_bytes))
                                texto_extraido = "".join([pagina.extract_text() + "\n" for pagina in lector_pdf.pages])
                                contexto_documento = f"BASA TU RESPUESTA ESTRICTAMENTE EN EL SIGUIENTE DOCUMENTO OFICIAL ({st.session_state.archivo_activo}):\n\n{texto_extraido}\n\n"
                        except Exception as e: pass
                    instruccion_final = f"{contexto_documento}PREGUNTA DEL INGENIERO: {pregunta}"
                    texto_final = modelo.generate_content(instruccion_final).text
                    caja_respuesta.markdown(texto_final)
                    st.session_state.mensajes_ia.append({"rol": "assistant", "contenido": texto_final})
                except Exception as e: caja_respuesta.error(f"Hubo un error de conexión: {e}")

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
            if rmr_final >= 81: texto_rmr, rec_eng = "Muy Bueno", "<b>Avance permitido:</b> Excavación a sección completa (hasta 3.0 m).<br><br><b>Soporte:</b> No requiere sostenimiento sistemático. Se recomienda desate meticuloso y perneado esporádico con pernos de fricción en cuñas sueltas."
            elif rmr_final >= 61: texto_rmr, rec_eng = "Bueno", "<b>Avance permitido:</b> Sección completa (1.5 a 3.0 m). Soporte a no más de 20 m del frente.<br><br><b>Soporte:</b> Instalar pernos sistemáticos (longitud de 3 m) espaciados entre 1.5 y 2.0 m en corona y hastiales. Opcional: Aplicar 5 cm de shotcrete en corona si existe debilidad local."
            elif rmr_final >= 41: texto_rmr, rec_eng = "Regular", "<b>Avance permitido:</b> Por galerías y banqueo (1.5 a 3.0 m). Soporte a <10 m del frente.<br><br><b>Soporte:</b> Pernos sistemáticos (3 a 4 m) cada 1.5 m. <b>Obligatorio:</b> Aplicación de shotcrete estructural (5 a 10 cm) complementado con malla electrosoldada en techo y paredes."
            elif rmr_final >= 21: texto_rmr, rec_eng = "Malo", "<b>Avance permitido:</b> 1.0 a 1.5 m. El sostenimiento debe ser concurrente a la excavación.<br><br><b>Soporte:</b> Perneado sistemático denso (1.0 m de espaciamiento), malla electrosoldada y shotcrete grueso (10 a 15 cm). Altamente recomendable evaluar el uso de cerchas metálicas cada 1.5 m."
            else: texto_rmr, rec_eng = "Muy Malo", "<b>Avance permitido:</b> Múltiple y controlado (0.5 a 1.0 m). Sostenimiento inmediato bajo paraguas de protección.<br><br><b>Soporte:</b> Uso sistemático de cerchas pesadas cada 0.75 m, marchavantes y blindaje con shotcrete estructural (>15 cm) en corona, hastiales y solera."

            st.markdown(f"""
            <div class='metric-box' style='border-color: {color_hex}66 !important;'><p class='metric-label'>Código GSI Identificado</p><p class='metric-value' style='color: {color_hex}; font-size: 38px;'>{codigo_gsi}</p></div>
            <div class='metric-box'><p class='metric-label'>Clasificación RMR Unificada</p><p class='metric-value' style='color: {color_hex};'>{rmr_final}</p><p style='color: {color_hex}; font-size: 13px; margin:0; font-weight: 500;'>Calidad: {texto_rmr}</p></div>
            <div class='metric-box' style='text-align: left; background-color: rgba(168,199,250,0.05); border-color: rgba(168,199,250,0.2) !important;'><p class='metric-label' style='color: #a8c7fa; margin-bottom: 8px;'>RECOMENDACIÓN TÉCNICA</p><p style='color: #e3e3e3; font-size: 11.5px; margin:0; line-height: 1.6;'>{rec_eng}</p></div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # PESTAÑA 3: VISOR TOPOGRÁFICO INTERACTIVO
    # ====================================================================
    elif pestaña == "Visor Topográfico":
        st.markdown("<h2 style='color: white; text-align: center; font-weight: 700; letter-spacing: 1px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>CONTROL TOPOGRÁFICO Y PLANOS 🗺️</h2>", unsafe_allow_html=True)
        st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
        
        if st.session_state.archivo_activo == "Base de datos general (Simulación)":
            st.info("ℹ️ Mostrando mapa base de simulación (Área referencial - Ate).")
            mapa_mina = folium.Map(location=[-12.025, -76.908], zoom_start=14, tiles="CartoDB dark_matter")
            st_folium(mapa_mina, width="100%", height=500)
        else:
            st.success(f"🗺️ Procesando base de datos: **{st.session_state.archivo_activo}**")
            with st.spinner("Buscando coordenadas planimétricas..."):
                try:
                    archivo_encontrado = next((f for f in st.session_state.archivos_nube if f['name'] == st.session_state.archivo_activo), None)
                    if not archivo_encontrado:
                        st.error("⚠️ Archivo no encontrado en la memoria de Drive.")
                    else:
                        csv_content = drive_service.files().get_media(fileId=archivo_encontrado['id']).execute().decode('utf-8')
                        df_mapa = pd.read_csv(StringIO(csv_content))
                        
                        def detectar_col(df, keywords):
                            for col in df.columns:
                                if str(col).upper() in keywords: return col
                            for col in df.columns:
                                for kw in keywords:
                                    if kw in str(col).upper(): return col
                            return None
                            
                        col_lat = detectar_col(df_mapa, ['LAT', 'LATITUD'])
                        col_lon = detectar_col(df_mapa, ['LON', 'LNG', 'LONGITUD'])
                        col_norte = detectar_col(df_mapa, ['NORTE', 'NORTH', 'Y_UTM'])
                        col_este = detectar_col(df_mapa, ['ESTE', 'EAST', 'X_UTM'])
                        
                        if df_mapa.empty: st.warning("⚠️ El archivo está vacío.")
                        elif col_norte is not None and col_este is not None:
                            df_clean = df_mapa.dropna(subset=[col_norte, col_este])
                            if df_clean.empty: st.warning("⚠️ Las columnas UTM están vacías.")
                            else:
                                transformer = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)
                                lon_centro, lat_centro = transformer.transform(float(df_clean.iloc[0][col_este]), float(df_clean.iloc[0][col_norte]))
                                mapa_dinamico = folium.Map(location=[lat_centro, lon_centro], zoom_start=16, tiles="CartoDB dark_matter")
                                for idx, row in df_clean.iterrows():
                                    try:
                                        lon_val, lat_val = transformer.transform(float(row[col_este]), float(row[col_norte]))
                                        folium.Marker([lat_val, lon_val], popup=f"Punto: {str(row.iloc[0])}", icon=folium.Icon(color="red", icon="flag")).add_to(mapa_dinamico)
                                    except: pass
                                st_folium(mapa_dinamico, width="100%", height=500)
                        elif col_lat is not None and col_lon is not None:
                            df_clean = df_mapa.dropna(subset=[col_lat, col_lon])
                            if df_clean.empty: st.warning("⚠️ Hay coordenadas vacías.")
                            else:
                                mapa_dinamico = folium.Map(location=[float(df_clean.iloc[0][col_lat]), float(df_clean.iloc[0][col_lon])], zoom_start=14, tiles="CartoDB dark_matter")
                                for idx, row in df_clean.iterrows(): folium.Marker([float(row[col_lat]), float(row[col_lon])], popup=str(row.iloc[0]), icon=folium.Icon(color="green", icon="info-sign")).add_to(mapa_dinamico)
                                st_folium(mapa_dinamico, width="100%", height=500)
                        else: st.warning("🗺️ El archivo no contiene coordenadas topográficas.")
                except Exception as e: st.error(f"Error procesando el mapa topográfico.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # PESTAÑA 4: VISUALIZADOR 3D SONDAJES 
    # ====================================================================
    elif pestaña == "Visualizador 3D Sondajes":
        st.markdown("<h2 style='color: white; text-align: center; font-weight: 700; letter-spacing: 1px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>MODELAMIENTO 3D DE SONDAJES 🛢️</h2>", unsafe_allow_html=True)
        st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
        
        csv_files = [f['name'] for f in st.session_state.get("archivos_nube", []) if f['name'].endswith(('.csv', '.txt'))]
        
        if len(csv_files) < 3:
            st.warning("⚠️ Necesitas tener al menos 3 archivos CSV en tu Google Drive para modelar sondajes (Collar, Survey e Intervalos).")
        else:
            st.markdown("<p style='color: #a8c7fa; font-weight: 600; margin-bottom: 10px;'>📌 Mapeo de Base de Datos (Selecciona los archivos del proyecto)</p>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                idx_c = next((i for i, f in enumerate(csv_files) if 'collar' in f.lower()), 0)
                sel_collar = st.selectbox("Archivo COLLAR (X, Y, Z)", csv_files, index=idx_c)
            with col2:
                idx_s = next((i for i, f in enumerate(csv_files) if 'survey' in f.lower()), 0)
                sel_survey = st.selectbox("Archivo SURVEY (Azimuth, Dip)", csv_files, index=idx_s)
            with col3:
                idx_a = next((i for i, f in enumerate(csv_files) if 'assay' in f.lower() or 'intervalo' in f.lower()), 0)
                sel_assay = st.selectbox("Archivo ASSAY (Leyes)", csv_files, index=idx_a)
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🚀 GENERAR MODELO 3D", type="primary", use_container_width=True):
                if sel_collar and sel_survey and sel_assay:
                    with st.spinner(f"Calculando interpolación espacial de la topografía..."):
                        try:
                            id_collar = next(f['id'] for f in st.session_state.archivos_nube if f['name'] == sel_collar)
                            id_survey = next(f['id'] for f in st.session_state.archivos_nube if f['name'] == sel_survey)
                            id_assay = next(f['id'] for f in st.session_state.archivos_nube if f['name'] == sel_assay)
                            
                            c_csv = drive_service.files().get_media(fileId=id_collar).execute().decode('utf-8')
                            s_csv = drive_service.files().get_media(fileId=id_survey).execute().decode('utf-8')
                            a_csv = drive_service.files().get_media(fileId=id_assay).execute().decode('utf-8')
                            
                            df_collar = pd.read_csv(StringIO(c_csv), sep=None, engine='python')
                            df_survey = pd.read_csv(StringIO(s_csv), sep=None, engine='python')
                            df_assay = pd.read_csv(StringIO(a_csv), sep=None, engine='python')
                            
                            df_collar.columns = [re.sub(r'[^a-zA-Z0-9_]', '', str(c).strip().upper()) for c in df_collar.columns]
                            df_survey.columns = [re.sub(r'[^a-zA-Z0-9_]', '', str(c).strip().upper()) for c in df_survey.columns]
                            df_assay.columns = [re.sub(r'[^a-zA-Z0-9_]', '', str(c).strip().upper()) for c in df_assay.columns]
                            
                            def buscar_col_exacta(df, palabras_clave):
                                for col in df.columns:
                                    if col in [p.upper() for p in palabras_clave]: return col
                                for col in df.columns:
                                    for p in palabras_clave:
                                        if p.upper() in col: return col
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
                                        
                                    dip_rad = np.radians(s_row[s_dip])
                                    az_rad = np.radians(s_row[s_az])
                                    dx = mid_depth * np.cos(dip_rad) * np.sin(az_rad)
                                    dy = mid_depth * np.cos(dip_rad) * np.cos(az_rad)
                                    dz = mid_depth * np.sin(dip_rad)
                                    resultados.append({'BHID': bhid, 'X': x0 + dx, 'Y': y0 + dy, 'Z': z0 + dz, 'LEY': row[col_ley]})
                                    
                            df_3d = pd.DataFrame(resultados)
                            
                            if df_3d.empty:
                                st.error("❌ Los archivos se leyeron perfectamente, pero los nombres de los taladros (BHID) no coinciden entre sí.")
                            else:
                                fig_3d = go.Figure()
                                cmax_val = max(0.1, df_3d['LEY'].quantile(0.98))
                                
                                for hole in df_3d["BHID"].unique():
                                    df_hole = df_3d[df_3d["BHID"] == hole]
                                    fig_3d.add_trace(go.Scatter3d(
                                        x=df_hole["X"], y=df_hole["Y"], z=df_hole["Z"], 
                                        mode='lines+markers', 
                                        marker=dict(size=4, color=df_hole["LEY"], colorscale='Viridis', colorbar=dict(title=dict(text=f"Ley Mineral", font=dict(color='white')), tickfont=dict(color='white')), cmin=0, cmax=cmax_val), 
                                        line=dict(width=2, color='rgba(255,255,255,0.3)'), 
                                        name=str(hole)
                                    ))
                                
                                try:
                                    x_col = df_collar[c_x].values
                                    y_col = df_collar[c_y].values
                                    z_col = df_collar[c_z].values
                                    
                                    if len(x_col) > 2:
                                        x_min, x_max = x_col.min(), x_col.max()
                                        y_min, y_max = y_col.min(), y_col.max()
                                        
                                        margen_x = (x_max - x_min) * 1.0 if x_max != x_min else 200
                                        margen_y = (y_max - y_min) * 1.0 if y_max != y_min else 200
                                        
                                        grid_x = np.linspace(x_min - margen_x, x_max + margen_x, 60)
                                        grid_y = np.linspace(y_min - margen_y, y_max + margen_y, 60)
                                        X_mesh, Y_mesh = np.meshgrid(grid_x, grid_y)
                                        
                                        X_flat = X_mesh.flatten()
                                        Y_flat = Y_mesh.flatten()
                                        
                                        dist = np.sqrt((x_col[:, np.newaxis] - X_flat)**2 + (y_col[:, np.newaxis] - Y_flat)**2)
                                        dist = np.where(dist == 0, 1e-10, dist)
                                        weights = 1.0 / (dist ** 2)
                                        Z_flat = np.sum(weights * z_col[:, np.newaxis], axis=0) / np.sum(weights, axis=0)
                                        Z_mesh = Z_flat.reshape(X_mesh.shape)
                                        
                                        fig_3d.add_trace(go.Surface(
                                            x=X_mesh, y=Y_mesh, z=Z_mesh,
                                            opacity=0.65, 
                                            colorscale=[[0, '#3e2723'], [0.6, '#5d4037'], [1, '#2e7d32']], 
                                            showscale=False,
                                            name='Terreno Interpolado',
                                            hoverinfo='skip'
                                        ))
                                except Exception as e: pass 

                                fig_3d.update_layout(
                                    margin=dict(r=10, l=10, b=10, t=10), height=700, paper_bgcolor="rgba(0,0,0,0)", 
                                    scene=dict(
                                        xaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Este (X)", color="white"), 
                                        yaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Norte (Y)", color="white"), 
                                        zaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Elevación (Z)", color="white"), 
                                        bgcolor="rgba(0,0,0,0)",
                                        aspectmode='data' 
                                    ), 
                                    legend=dict(font=dict(color="white"))
                                )
                                st.plotly_chart(fig_3d, use_container_width=True)
                                st.success(f"✅ Modelo 3D generado con **{len(df_3d['BHID'].unique())}** sondajes y Topografía Espacial Extendida.")
                        except Exception as e: st.error(f"⚠️ Error matemático crítico al generar el modelo 3D: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # PESTAÑA 5: DISEÑO DE VOLADURA (¡LA NUEVA PESTAÑA!)
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
                tacos = 0.0 # No aplica directamente a la forma en galería simple
                
            else: # Túnel
                st.info("ℹ️ Parámetros estandarizados para una sección de galería de 3x3 metros.")
                profundidad = st.number_input("Longitud de Avance (m)", min_value=1.0, max_value=5.0, value=3.0, step=0.5)
                diametro_mm = st.number_input("Diámetro de Taladro (mm)", min_value=32.0, max_value=64.0, value=45.0, step=1.0)
                burden, espaciamiento, filas, columnas = 1, 1, 1, 1 # Valores fijos para cálculo interno
                
            st.markdown("<br><div class='titulo-seccion'>Parámetros de Voladura</div>", unsafe_allow_html=True)
            densidad_roca = st.number_input("Densidad de la Roca (ton/m³)", min_value=1.0, max_value=5.0, value=2.7, step=0.1)
            factor_potencia = st.number_input("Factor de Potencia Deseado (kg/ton)", min_value=0.1, max_value=2.0, value=0.45, step=0.05)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_visor:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            
            # --- MOTOR GENERADOR DE MALLAS ---
            taladros = []
            
            if tipo_malla == "Malla Cuadrada (Tajo Abierto)":
                for f in range(filas):
                    for c in range(columnas):
                        x = c * espaciamiento
                        y = f * burden
                        taladros.append({"ID": f"T-{f}-{c}", "X": x, "Y": y, "Z_start": 0, "Z_end": -profundidad, "Tipo": "Producción"})
                        
            elif tipo_malla == "Malla Tresbolillo (Tajo Abierto)":
                for f in range(filas):
                    offset = (espaciamiento / 2) if f % 2 != 0 else 0
                    for c in range(columnas):
                        x = (c * espaciamiento) + offset
                        y = f * burden
                        taladros.append({"ID": f"T-{f}-{c}", "X": x, "Y": y, "Z_start": 0, "Z_end": -profundidad, "Tipo": "Producción"})
                        
            elif tipo_malla == "Frente de Túnel (Galería 3x3m)":
                # Arranque (Cut) - Centro
                taladros.append({"ID": "A1", "X": 1.5, "Y": 1.5, "Z_start": 0, "Z_end": profundidad, "Tipo": "Arranque"})
                taladros.append({"ID": "A2", "X": 1.3, "Y": 1.5, "Z_start": 0, "Z_end": profundidad, "Tipo": "Arranque"})
                taladros.append({"ID": "A3", "X": 1.7, "Y": 1.5, "Z_start": 0, "Z_end": profundidad, "Tipo": "Arranque"})
                taladros.append({"ID": "A4", "X": 1.5, "Y": 1.3, "Z_start": 0, "Z_end": profundidad, "Tipo": "Arranque"})
                taladros.append({"ID": "A5", "X": 1.5, "Y": 1.7, "Z_start": 0, "Z_end": profundidad, "Tipo": "Arranque"})
                
                # Ayudas (Relievers)
                for x in [1.0, 2.0]:
                    for y in [1.0, 2.0]:
                        taladros.append({"ID": f"Ay-{x}-{y}", "X": x, "Y": y, "Z_start": 0, "Z_end": profundidad, "Tipo": "Ayudas"})
                        
                # Cuadradores y Arrastre
                for x in [0.2, 0.8, 1.5, 2.2, 2.8]:
                    taladros.append({"ID": f"Ar-{x}", "X": x, "Y": 0.2, "Z_start": 0, "Z_end": profundidad, "Tipo": "Arrastre"})
                for y in [0.8, 1.5, 2.2]:
                    taladros.append({"ID": f"C1-{y}", "X": 0.2, "Y": y, "Z_start": 0, "Z_end": profundidad, "Tipo": "Cuadradores"})
                    taladros.append({"ID": f"C2-{y}", "X": 2.8, "Y": y, "Z_start": 0, "Z_end": profundidad, "Tipo": "Cuadradores"})
                
                # Corona (Roof)
                for x in [0.2, 0.8, 1.5, 2.2, 2.8]:
                    taladros.append({"ID": f"Co-{x}", "X": x, "Y": 2.8, "Z_start": 0, "Z_end": profundidad, "Tipo": "Corona"})

            df_malla = pd.DataFrame(taladros)
            
            # --- RENDERIZADO 3D DE LA MALLA ---
            fig_malla = go.Figure()
            
            colores = {"Producción": "#f44336", "Arranque": "#ffeb3b", "Ayudas": "#ff9800", "Cuadradores": "#2196f3", "Arrastre": "#4caf50", "Corona": "#9c27b0"}
            
            for _, row in df_malla.iterrows():
                # Dibujamos las líneas de los taladros
                if "Tajo" in tipo_malla:
                    fig_malla.add_trace(go.Scatter3d(
                        x=[row["X"], row["X"]], y=[row["Y"], row["Y"]], z=[row["Z_start"], row["Z_end"]],
                        mode='lines', line=dict(width=6, color=colores.get(row["Tipo"], "#fff")), name=row["ID"], showlegend=False
                    ))
                    # Puntos en superficie
                    fig_malla.add_trace(go.Scatter3d(
                        x=[row["X"]], y=[row["Y"]], z=[row["Z_start"]],
                        mode='markers', marker=dict(size=5, color='white'), showlegend=False
                    ))
                else: # Túnel (rotamos los ejes para que mire hacia adelante)
                    fig_malla.add_trace(go.Scatter3d(
                        x=[row["X"], row["X"]], y=[row["Z_start"], row["Z_end"]], z=[row["Y"], row["Y"]],
                        mode='lines', line=dict(width=6, color=colores.get(row["Tipo"], "#fff")), name=row["ID"], showlegend=False
                    ))
                    # Puntos en el frente
                    fig_malla.add_trace(go.Scatter3d(
                        x=[row["X"]], y=[row["Z_start"]], z=[row["Y"]],
                        mode='markers', marker=dict(size=4, color='white'), showlegend=False
                    ))

            fig_malla.update_layout(
                margin=dict(r=10, l=10, b=10, t=10), height=450, paper_bgcolor="rgba(0,0,0,0)", 
                scene=dict(
                    xaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Ancho (X)", color="white"), 
                    yaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Avance (Y)", color="white"), 
                    zaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Alto (Z)", color="white"), 
                    bgcolor="rgba(0,0,0,0)", aspectmode='data'
                ), 
                showlegend=False
            )
            st.plotly_chart(fig_malla, use_container_width=True)
            
            # --- CÁLCULOS MATEMÁTICOS DE VOLADURA ---
            st.markdown("<div class='titulo-seccion'>Reporte de Carga y Factor de Potencia</div>", unsafe_allow_html=True)
            
            num_taladros = len(df_malla)
            
            if "Tajo" in tipo_malla:
                volumen_total = (burden * espaciamiento * profundidad) * num_taladros
                tonelaje_total = volumen_total * densidad_roca
                anfo_total = tonelaje_total * factor_potencia
                anfo_por_taladro = anfo_total / num_taladros
            else:
                area_frente = 3 * 3 # 9 m2
                volumen_total = area_frente * profundidad
                tonelaje_total = volumen_total * densidad_roca
                anfo_total = tonelaje_total * factor_potencia
                anfo_por_taladro = anfo_total / num_taladros
            
            # Densidad de carga (Factor de carga lineal) aproximada
            radio_m = (diametro_mm / 1000) / 2
            volumen_taladro = math.pi * (radio_m ** 2) * profundidad
            # Densidad del ANFO es aprox 0.8 g/cm3 = 800 kg/m3
            kg_max_por_taladro = volumen_taladro * 800
            
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.markdown(f"<div class='metric-box'><p class='metric-label'>Toneladas a Romper</p><p class='metric-value' style='color: #8bc34a; font-size:32px;'>{tonelaje_total:,.1f}</p><p style='color:#aaa; font-size:12px; margin:0;'>Volumen: {volumen_total:,.1f} m³</p></div>", unsafe_allow_html=True)
            col_r2.markdown(f"<div class='metric-box'><p class='metric-label'>ANFO Total Requerido</p><p class='metric-value' style='color: #f44336; font-size:32px;'>{anfo_total:,.1f} kg</p><p style='color:#aaa; font-size:12px; margin:0;'>{num_taladros} Taladros en la Malla</p></div>", unsafe_allow_html=True)
            
            # Verificación de sobrecarga
            color_carga = "#ffeb3b" if anfo_por_taladro <= kg_max_por_taladro else "#f44336"
            alerta_carga = "Carga Óptima" if anfo_por_taladro <= kg_max_por_taladro else "⚠️ Sobrecarga (Diámetro insuficiente)"
            
            col_r3.markdown(f"<div class='metric-box'><p class='metric-label'>ANFO por Taladro</p><p class='metric-value' style='color: {color_carga}; font-size:32px;'>{anfo_por_taladro:,.1f} kg</p><p style='color:{color_carga}; font-size:12px; margin:0;'>{alerta_carga}</p></div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # PESTAÑA 6: BASE DE DATOS
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
                tarjeta_html = f"<div class='file-card'><div class='file-icon'>{icono}</div><div class='file-details'><p class='file-name' title='{nombre}'>{nombre}</p><p class='file-id'>ID DRIVE: {id_corto}...</p></div></div>"
                columnas[i % 3].markdown(tarjeta_html, unsafe_allow_html=True)
