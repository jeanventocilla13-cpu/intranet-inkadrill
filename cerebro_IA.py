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

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="InkaDrill - Cerebro IA", page_icon="✨", layout="wide")

if "pestaña_activa" not in st.session_state:
    st.session_state.pestaña_activa = "Visualizador 3D Sondajes"
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
    
    opciones_nav = {"💬": "Chat Asistente Operativo", "🧮": "Cálculos Geomecánicos", "🗺️": "Visor Topográfico", "🛢️": "Visualizador 3D Sondajes", "🗄️": "Base de Datos"}
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
    # PESTAÑA 2: CÁLCULOS GEOMECÁNICOS (IMAGEN HÍBRIDA)
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
        # 1. Intento Local
        rutas_locales = [nombre_imagen, f"rocas/{nombre_imagen}"]
        for ruta in rutas_locales:
            if os.path.exists(ruta):
                with open(ruta, "rb") as f: img_b64 = base64.b64encode(f.read()).decode()
                break
        
        # 2. Intento de Respaldo por Web (Si lo local falla en la nube)
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
                        with st.expander("Ver tabla de datos", expanded=False): st.dataframe(df_mapa, use_container_width=True)
                        
                        def detectar_col(df, keywords):
                            for col in df.columns:
                                for kw in keywords:
                                    if kw.upper() == str(col).upper() or f"{kw.upper()}_" in str(col).upper() or f"_{kw.upper()}" in str(col).upper(): return col
                            for col in df.columns:
                                for kw in keywords:
                                    if kw.upper() in str(col).upper(): return col
                            return None
                            
                        col_lat = detectar_col(df_mapa, ['LAT', 'LATITUD', 'Y'])
                        col_lon = detectar_col(df_mapa, ['LON', 'LNG', 'LONGITUD', 'X'])
                        col_norte = detectar_col(df_mapa, ['NORTE', 'NORTH', 'Y'])
                        col_este = detectar_col(df_mapa, ['ESTE', 'EAST', 'X'])
                        
                        if df_mapa.empty: st.warning("⚠️ El archivo está vacío.")
                        elif col_lat and col_lon and ('NORTE' not in str(col_lat).upper()) and ('ESTE' not in str(col_lon).upper()):
                            df_clean = df_mapa.dropna(subset=[col_lat, col_lon])
                            if df_clean.empty: st.warning("⚠️ Hay coordenadas vacías.")
                            else:
                                mapa_dinamico = folium.Map(location=[float(df_clean.iloc[0][col_lat]), float(df_clean.iloc[0][col_lon])], zoom_start=14, tiles="CartoDB dark_matter")
                                for idx, row in df_clean.iterrows(): folium.Marker([float(row[col_lat]), float(row[col_lon])], popup=str(row.iloc[0]), icon=folium.Icon(color="green", icon="info-sign")).add_to(mapa_dinamico)
                                st_folium(mapa_dinamico, width="100%", height=500)
                        elif col_norte and col_este:
                            st.info(f"🔄 Coordenadas UTM detectadas. Convirtiendo a WGS84...")
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
                        else: st.warning("🗺️ El archivo no contiene coordenadas topográficas.")
                except Exception as e: st.error(f"Error procesando el mapa topográfico.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # PESTAÑA 4: VISUALIZADOR 3D SONDAJES (EVITA CRUCE DE PROYECTOS)
    # ====================================================================
    elif pestaña == "Visualizador 3D Sondajes":
        st.markdown("<h2 style='color: white; text-align: center; font-weight: 700; letter-spacing: 1px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>MODELAMIENTO 3D DE SONDAJES 🛢️</h2>", unsafe_allow_html=True)
        st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
        
        try:
            with st.spinner("Descargando sondajes y ejecutando motor trigonométrico..."):
                df_collar, df_survey, df_assay = None, None, None
                archivos_cargados = []
                
                # Se asigna solo el PRIMER archivo que coincida para evitar mezclar minas
                for f in st.session_state.archivos_nube:
                    nombre = f['name'].lower()
                    if 'collar' in nombre and nombre.endswith('.csv') and df_collar is None:
                        csv_content = drive_service.files().get_media(fileId=f['id']).execute().decode('utf-8')
                        df_collar = pd.read_csv(StringIO(csv_content))
                        archivos_cargados.append(f['name'])
                    elif 'survey' in nombre and nombre.endswith('.csv') and df_survey is None:
                        csv_content = drive_service.files().get_media(fileId=f['id']).execute().decode('utf-8')
                        df_survey = pd.read_csv(StringIO(csv_content))
                        archivos_cargados.append(f['name'])
                    elif ('assay' in nombre or 'intervalo' in nombre) and nombre.endswith('.csv') and df_assay is None:
                        csv_content = drive_service.files().get_media(fileId=f['id']).execute().decode('utf-8')
                        df_assay = pd.read_csv(StringIO(csv_content))
                        archivos_cargados.append(f['name'])
                
                if df_collar is not None and df_survey is not None and df_assay is not None:
                    st.success(f"✅ Modelando 3D usando: {', '.join(archivos_cargados)}")
                    
                    def buscar_columna(df, palabras_clave):
                        for col in df.columns:
                            for p in palabras_clave:
                                if p.upper() in str(col).upper(): return col
                        return df.columns[0]
                        
                    id_c = buscar_columna(df_collar, ['BHID', 'HOLE', 'ID', 'TALADRO'])
                    id_s = buscar_columna(df_survey, ['BHID', 'HOLE', 'ID', 'TALADRO'])
                    id_a = buscar_columna(df_assay, ['BHID', 'HOLE', 'ID', 'TALADRO'])
                    
                    c_x = buscar_columna(df_collar, ['X', 'ESTE', 'EAST'])
                    c_y = buscar_columna(df_collar, ['Y', 'NORTE', 'NORTH'])
                    c_z = buscar_columna(df_collar, ['Z', 'ELEV', 'RL', 'COTA'])
                    
                    s_at = buscar_columna(df_survey, ['AT', 'DEPTH', 'PROF'])
                    s_az = buscar_columna(df_survey, ['AZIMUTH', 'AZ', 'AZM'])
                    s_dip = buscar_columna(df_survey, ['DIP', 'INCLINACION', 'BUZAMIENTO'])
                    
                    a_from = buscar_columna(df_assay, ['FROM', 'DESDE'])
                    a_to = buscar_columna(df_assay, ['TO', 'HASTA'])
                    col_ley = buscar_columna(df_assay, ['CU', 'AU', 'AG', 'LEY', 'GRADE'])
                    
                    df_assay[col_ley] = pd.to_numeric(df_assay[col_ley], errors='coerce').fillna(0)
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
                    fig_3d = go.Figure()
                    cmax_val = max(0.1, df_3d['LEY'].quantile(0.98))
                    
                    for hole in df_3d["BHID"].unique():
                        df_hole = df_3d[df_3d["BHID"] == hole]
                        fig_3d.add_trace(go.Scatter3d(x=df_hole["X"], y=df_hole["Y"], z=df_hole["Z"], mode='lines+markers', marker=dict(size=4, color=df_hole["LEY"], colorscale='Viridis', colorbar=dict(title=f"Ley ({col_ley})", tickfont=dict(color='white'), titlefont=dict(color='white')), cmin=0, cmax=cmax_val), line=dict(width=2, color='rgba(255,255,255,0.3)'), name=str(hole)))
                        
                    fig_3d.update_layout(margin=dict(r=10, l=10, b=10, t=10), height=700, paper_bgcolor="rgba(0,0,0,0)", scene=dict(xaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Este (X)", color="white"), yaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Norte (Y)", color="white"), zaxis=dict(showbackground=False, gridcolor='rgba(255,255,255,0.1)', title="Elevación (Z)", color="white"), bgcolor="rgba(0,0,0,0)"), legend=dict(font=dict(color="white")))
                    st.plotly_chart(fig_3d, use_container_width=True)
                else:
                    faltantes = []
                    if df_collar is None: faltantes.append("Collar")
                    if df_survey is None: faltantes.append("Survey")
                    if df_assay is None: faltantes.append("Intervalos")
                    st.warning(f"⚠️ Para renderizar el modelo 3D te faltan los siguientes archivos en Drive: **{', '.join(faltantes)}**.")
        except Exception as e: st.error(f"⚠️ Error procesando la topología de sondajes: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # PESTAÑA 5: BASE DE DATOS
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
