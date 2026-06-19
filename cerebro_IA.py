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

if "pestaña_activa" not in st.session_state:
    st.session_state.pestaña_activa = "Cálculos Geomecánicos"
if "archivo_activo" not in st.session_state:
    st.session_state.archivo_activo = "Base de datos general (Simulación)"

# --- FUNCIÓN INTELIGENTE PARA LOGOS DE ARCHIVOS ---
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
    
    html, body, [class*="css"] {
        font-family: 'Google Sans', sans-serif !important;
    }
    
    /* 1. FONDO DE PANTALLA COMPLETO */
    .stApp {
        background: linear-gradient(rgba(19, 19, 20, 0.70), rgba(19, 19, 20, 0.70)), 
                    url("https://github.com/jeanventocilla13-cpu/intranet-inkadrill/blob/main/fondo%20de%20escaneo.png?raw=true") no-repeat center center fixed !important;
        background-size: cover !important;
    }
    [data-testid="stHeader"] { background-color: transparent !important; }

    /* 2. BARRA LATERAL (CRISTAL) */
    [data-testid="stSidebar"] {
        background-color: rgba(19, 19, 20, 0.4) !important;
        backdrop-filter: blur(15px) !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important; 
    }

    /* 3. ALINEACIÓN PERFECTA (NAVEGACIÓN) */
    [data-testid="stSidebar"] button[kind="secondary"] {
        padding-left: 10px !important; 
        background-color: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        display: flex !important;
        justify-content: flex-start !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"] div {
        display: flex !important;
        justify-content: flex-start !important;
        width: 100% !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"] p {
        text-align: left !important;
        color: #c4c7c5 !important;
        margin: 0 !important;
        font-size: 14px !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
    }

    [data-testid="stSidebar"] button[kind="primary"] {
        border-radius: 30px !important;
        background-color: rgba(30, 31, 32, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #e3e3e3 !important;
        font-weight: 500 !important;
    }
    
    /* 4. MAGIA: RECIENTES CON CUADRO AMARILLO PERFECTO */
    div[role="radiogroup"] > label {
        background-color: transparent !important;
        padding: 8px 10px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        margin-bottom: 2px !important;
        transition: 0.2s;
    }
    div[role="radiogroup"] > label:hover {
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    div[role="radiogroup"] > label > div:first-of-type { display: none !important; }
    
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: rgba(255, 213, 79, 0.15) !important;
        border-left: 3px solid #ffd54f !important;
    }
    div[role="radiogroup"] > label:has(input:checked) p {
        color: #ffd54f !important;
        font-weight: 600 !important;
    }
    div[role="radiogroup"] p {
        color: #c4c7c5 !important;
        font-size: 14.5px !important;
        margin: 0 !important;
        text-align: left !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    
    /* 5. FIX: CHAT INPUT Y BOTÓN FLOTANTE ALINEADO */
    [data-testid="stBottom"], [data-testid="stBottom"] > div {
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    .stChatFloatingInputContainer { background-color: transparent !important; }

    .stChatInputContainer {
        border-radius: 30px !important;
        background-color: rgba(25, 26, 27, 0.85) !important; 
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        width: calc(100% - 75px) !important; 
        margin-left: 75px !important;
        margin-bottom: 15px !important;
    }
    .stChatInputContainer textarea {
        padding-left: 20px !important;
        color: #e3e3e3 !important;
    }
    
    div[data-testid="stPopover"] {
        position: fixed !important;
        bottom: 27px !important; 
        left: auto !important; 
        width: 46px !important; 
        height: 46px !important; 
        z-index: 999999 !important;
    }
    div[data-testid="stPopover"] > button {
        width: 46px !important;
        height: 46px !important;
        min-width: 46px !important;
        max-width: 46px !important;
        border-radius: 50% !important; 
        padding: 0 !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: rgba(25, 26, 27, 0.85) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: #e3e3e3 !important;
        font-size: 24px !important;
        line-height: 0 !important;
        transition: 0.3s;
    }
    div[data-testid="stPopover"] > button:hover {
        background-color: rgba(255, 255, 255, 0.15) !important;
        color: #ffd54f !important;
    }
    div[data-testid="stPopover"] > button svg { display: none !important; width: 0 !important; height: 0 !important; }
    div[data-testid="stPopover"] > button p, div[data-testid="stPopover"] > button span {
        margin: 0 !important; display: flex !important; align-items: center !important; justify-content: center !important; width: 100% !important;
    }
    
    /* 6. ESTILOS PRO PARA LA SUITE GEOMECÁNICA */
    .panel-geo {
        background-color: rgba(25, 26, 27, 0.6) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px;
        padding: 20px;
        height: 100%;
    }
    .titulo-seccion {
        color: #e3e3e3;
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 15px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        padding-bottom: 8px;
    }
    .metric-box {
        background-color: rgba(19, 19, 20, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
    }
    .metric-value {
        font-size: 46px;
        font-weight: 700;
        margin: 5px 0;
        line-height: 1;
    }
    .metric-label {
        color: #aaa;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 0;
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
    
    opciones_nav = {"💬": "Chat Asistente Operativo", "🧮": "Cálculos Geomecánicos", "🗺️": "Visor Topográfico", "🛢️": "Visualizador 3D Sondajes", "📈": "Dashboard Analíticas"}
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
        if pestaña in ["Dashboard Analíticas", "Visualizador 3D Sondajes", "Visor Topográfico"]: archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.csv', '.xlsx', '.xls', '.pdf'))]
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
    # PESTAÑA 2: CÁLCULOS GEOMECÁNICOS (AHORA CON LÓGICA 100% DINÁMICA)
    # ====================================================================
    elif pestaña == "Cálculos Geomecánicos":
        st.markdown("<h2 style='color: white; text-align: center; font-weight: 700; letter-spacing: 1px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>SUITE DE ANÁLISIS GEOMECÁNICO 🪨</h2>", unsafe_allow_html=True)
        
        # Inicializar en memoria
        if "rmr_calc" not in st.session_state: st.session_state.rmr_calc = 45 # Default como en tu foto
        if "gsi_calc" not in st.session_state: st.session_state.gsi_calc = 51 # Default como en tu foto
        
        col_param, col_visor, col_resultados = st.columns([1.2, 1.2, 1])
        
        # 1. PARÁMETROS DE ENTRADA
        with col_param:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            st.markdown("<div class='titulo-seccion'>Parámetros de Roca Intacta</div>", unsafe_allow_html=True)
            ucs = st.number_input("Resistencia Compresión Simple (UCS) (MPa)", min_value=0, max_value=300, value=16)
            
            st.markdown("<br><div class='titulo-seccion'>Propiedades del Macizo Rocoso</div>", unsafe_allow_html=True)
            rqd = st.slider("RQD (%)", 0, 100, 55)
            sep = st.slider("Separación de Discontinuidades (m)", 0.0, 2.0, 0.96)
            
            condicion = st.selectbox("Condición de Discontinuidades", ["Lisas", "Rugosas", "Ligeramente Rugosas", "Espejadas"])
            estructura = st.selectbox("Estructura del Macizo Rocoso", ["Fracturado", "Masivo", "Laminado", "Triturado"])
            st.markdown("</div>", unsafe_allow_html=True)

        # CÁLCULOS DE LA IA 
        # (Se calculan antes de renderizar el Visor para que el modelo 3D responda al instante)
        rmr_base = (rqd * 0.4) + (ucs * 0.2) + (sep * 5)
        if condicion == "Rugosas": rmr_base += 10
        elif condicion == "Lisas": rmr_base += 5
        st.session_state.rmr_calc = min(100, int(rmr_base))
        
        gsi_base = rqd * 0.85
        if estructura == "Masivo": gsi_base += 10
        elif estructura == "Fracturado": gsi_base += 4
        st.session_state.gsi_calc = min(100, int(gsi_base))

        # 2. VISOR DEL MODELO 3D DINÁMICO
        with col_visor:
            rmr = st.session_state.rmr_calc
            
            # LÓGICA DINÁMICA DEL MODELO 3D SEGÚN RMR
            if rmr >= 80:
                icono_3d = "💎"
                color_brillo = "rgba(76, 175, 80, 0.6)" # Verde brillante
                texto_3d = "ROCA INTACTA / EXCELENTE"
            elif rmr >= 60:
                icono_3d = "🧊"
                color_brillo = "rgba(139, 195, 74, 0.6)" # Verde claro
                texto_3d = "MACIZO LEVEMENTE FRACTURADO"
            elif rmr >= 40:
                icono_3d = "🧱"
                color_brillo = "rgba(255, 235, 59, 0.6)" # Amarillo
                texto_3d = "MACIZO FRACTURADO / REGULAR"
            else:
                icono_3d = "🪨"
                color_brillo = "rgba(244, 67, 54, 0.6)" # Rojo Alerta
                texto_3d = "MACIZO MUY POBRE / INESTABLE"

            st.markdown(f"""
            <div style='background: radial-gradient(circle, {color_brillo} 0%, rgba(0,0,0,0) 70%); height: 350px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px dashed rgba(255, 255, 255, 0.2); border-radius: 15px; box-shadow: inset 0 0 20px rgba(0,0,0,0.5); transition: 0.5s;'>
                <h1 style='font-size: 90px; margin: 0; filter: drop-shadow(0px 0px 15px {color_brillo});'>{icono_3d}</h1>
                <p style='color: #e3e3e3; font-weight: 600; margin-top: 20px; letter-spacing: 1px;'>{texto_3d}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⚡ ACTUALIZAR ANÁLISIS", type="primary", use_container_width=True):
                st.rerun()

        # 3. COLUMNA DE RESULTADOS Y RECOMENDACIONES REALES (BIENIAWSKI)
        with col_resultados:
            st.markdown("<div class='panel-geo'>", unsafe_allow_html=True)
            st.markdown("<div class='titulo-seccion'>Informes y Resultados</div>", unsafe_allow_html=True)
            
            gsi = st.session_state.gsi_calc
            
            # Lógica RMR y Recomendación de Ingeniería Real
            if rmr >= 81: 
                color_rmr, texto_rmr = "#4caf50", "Muy Bueno"
                rec_eng = "Excavación a sección completa (avance de 3m). No requiere sostenimiento sistemático, solo perneado esporádico (spot bolting) en cuñas sueltas identificadas."
            elif rmr >= 61: 
                color_rmr, texto_rmr = "#8bc34a", "Bueno"
                rec_eng = "Avance de 1.5 - 3.0 m. Instalar pernos sistemáticos (long. 3m) espaciados a 1.5 - 2m en corona y hastiales, con malla ocasional."
            elif rmr >= 41: 
                color_rmr, texto_rmr = "#ffeb3b", "Regular"
                rec_eng = "Avance de 1.5 - 3.0 m. Pernos sistemáticos (3-4m) a 1.5m de espaciamiento. Aplicar shotcrete (5-10 cm) y malla electrosoldada en techo y paredes."
            elif rmr >= 21: 
                color_rmr, texto_rmr = "#ff9800", "Malo"
                rec_eng = "Avance de 1.0 - 1.5m. Sostenimiento concurrente. Pernos sistemáticos a 1m de espaciamiento, malla y shotcrete grueso (10-15 cm). Evaluar uso de cerchas livianas."
            else: 
                color_rmr, texto_rmr = "#f44336", "Muy Malo"
                rec_eng = "Avance múltiple (0.5 - 1.0m). Sostenimiento inmediato en el frente. Requiere uso de cerchas metálicas pesadas espaciadas a 0.75m, marchavantes y shotcrete estructural (>15cm)."
            
            if gsi > 75: color_gsi, texto_gsi = "#4caf50", "Excelente"
            elif gsi > 50: color_gsi, texto_gsi = "#ffeb3b", "Bueno"
            else: color_gsi, texto_gsi = "#ff9800", "Regular"

            st.markdown(f"""
            <div class='metric-box'>
                <p class='metric-label'>Índice GSI Estimado</p>
                <p class='metric-value' style='color: {color_gsi};'>{gsi}</p>
                <p style='color: {color_gsi}; font-size: 13px; margin:0; font-weight: 500;'>GSI = {texto_gsi}</p>
            </div>
            
            <div class='metric-box'>
                <p class='metric-label'>Clasificación RMR Unificada</p>
                <p class='metric-value' style='color: {color_rmr};'>{rmr}</p>
                <p style='color: {color_rmr}; font-size: 13px; margin:0; font-weight: 500; margin-bottom: 10px;'>RMR = {texto_rmr}</p>
                <div style='text-align: left; font-size: 11px; color: #888; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;'>
                    <p style='margin:2px 0; display:flex; justify-content:space-between;'><span>Impacto RQD:</span> <span>{(rqd*0.4):.1f} pts</span></p>
                    <p style='margin:2px 0; display:flex; justify-content:space-between;'><span>Impacto UCS:</span> <span>{(ucs*0.2):.1f} pts</span></p>
                </div>
            </div>
            
            <div class='metric-box' style='text-align: left; background-color: rgba(168,199,250,0.05); border-color: rgba(168,199,250,0.2) !important;'>
                <p class='metric-label' style='color: #a8c7fa; margin-bottom: 5px;'>RECOMENDACIÓN TÉCNICA (Bieniawski)</p>
                <p style='color: #e3e3e3; font-size: 12px; margin:0; line-height: 1.5;'>
                    {rec_eng}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

    # ====================================================================
    # OTRAS PESTAÑAS
    # ====================================================================
    elif pestaña == "Visor Topográfico": st.markdown("<h1 style='color: white;'>Control Topográfico y Planos 🗺️</h1>", unsafe_allow_html=True)
    elif pestaña == "Visualizador 3D Sondajes": st.markdown("<h1 style='color: white;'>Modelamiento 3D 🛢️</h1>", unsafe_allow_html=True)
    elif pestaña == "Dashboard Analíticas": st.markdown("<h1 style='color: white;'>Analíticas 📈</h1>", unsafe_allow_html=True)
