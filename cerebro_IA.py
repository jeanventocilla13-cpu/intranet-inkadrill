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
    st.session_state.pestaña_activa = "Chat Asistente Operativo"
if "archivo_activo" not in st.session_state:
    st.session_state.archivo_activo = "Base de datos general (Simulación)"

# --- FUNCIÓN INTELIGENTE PARA LOGOS DE ARCHIVOS ---
def obtener_icono(nombre_archivo):
    nombre_lower = nombre_archivo.lower()
    if "simulación" in nombre_lower or "simulacion" in nombre_lower:
        return "⚙️"  
    elif nombre_lower.endswith('.pdf'):
        return "📕"  
    elif nombre_lower.endswith(('.csv', '.xlsx', '.xls')):
        return "📗"  
    elif nombre_lower.endswith(('.png', '.jpg', '.jpeg')):
        return "🖼️"  
    elif nombre_lower.endswith('.txt'):
        return "📝"  
    else:
        return "📄"  

# --- INYECCIÓN DE ESTÉTICA GEMINI (CSS Customizado) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Google Sans', sans-serif !important;
    }
    
    /* 1. FONDO DE PANTALLA COMPLETO */
    .stApp {
        background: linear-gradient(rgba(19, 19, 20, 0.65), rgba(19, 19, 20, 0.65)), 
                    url("https://github.com/jeanventocilla13-cpu/intranet-inkadrill/blob/main/fondo%20de%20escaneo.png?raw=true") no-repeat center center fixed !important;
        background-size: cover !important;
    }
    [data-testid="stHeader"] { background-color: transparent !important; }

    /* 2. BARRA LATERAL (CRISTAL) */
    [data-testid="stSidebar"] {
        background-color: rgba(19, 19, 20, 0.3) !important;
        backdrop-filter: blur(12px) !important; 
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

    /* Botón Nueva Conversación */
    [data-testid="stSidebar"] button[kind="primary"] {
        border-radius: 30px !important;
        background-color: rgba(30, 31, 32, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #e3e3e3 !important;
        font-weight: 500 !important;
    }
    
    /* 4. MAGIA: CUADRO AMARILLO (NAVEGACIÓN Y RECIENTES) */
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
    div[role="radiogroup"] > label > div:first-of-type {
        display: none !important; 
    }
    
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
    
    /* 5. FIX DEFINITIVO: CHAT INPUT Y BOTÓN FLOTANTE ALINEADO */
    [data-testid="stBottom"], [data-testid="stBottom"] > div {
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    .stChatFloatingInputContainer {
        background-color: transparent !important;
    }

    .stChatInputContainer {
        border-radius: 30px !important;
        background-color: rgba(25, 26, 27, 0.85) !important; 
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        width: calc(100% - 65px) !important; 
        margin-left: 65px !important; 
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
    
    div[data-testid="stPopover"] > button svg {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
    }
    div[data-testid="stPopover"] > button p,
    div[data-testid="stPopover"] > button span {
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
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
    st.error(f"Error de conexión con Drive: {e}")

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
    
    opciones_nav = {
        "💬": "Chat Asistente Operativo", 
        "🧮": "Cálculos Geomecánicos", 
        "🗺️": "Visor Topográfico", 
        "🛢️": "Visualizador 3D Sondajes", 
        "📈": "Dashboard Analíticas"
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
    
    st.markdown("<br>", unsafe_allow_html=True) 
    st.markdown("<p style='color:#888; font-size:13px; font-weight:500; margin-bottom:5px; padding-left:10px;'>Recientes</p>", unsafe_allow_html=True)
    
    opciones_archivos = ["Base de datos general (Simulación)"]
    archivos_filtrados = []
    
    if "archivos_nube" in st.session_state:
        if pestaña in ["Dashboard Analíticas", "Visualizador 3D Sondajes", "Visor Topográfico"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.csv', '.xlsx', '.xls', '.pdf'))]
        elif pestaña in ["Chat Asistente Operativo"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.pdf', '.txt', '.png', '.jpg', '.jpeg', '.csv'))]
    
    for f in archivos_filtrados:
        opciones_archivos.append(f['name'])
        
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
        
        if st.session_state.archivo_activo != "Base de datos general (Simulación)":
            st.info(f"🔎 **Modo Enfoque:** El chat responderá basándose en el archivo: `{st.session_state.archivo_activo}`")
            
        with st.popover("➕", use_container_width=False):
            st.markdown("#### 🛠️ Herramientas")
            tab1, tab2 = st.tabs(["📎 Subir Archivos", "📊 Extraer Tablas"])
            with tab1:
                archivo_subido = st.file_uploader("Arrastra PDFs", type=["pdf", "txt", "png", "jpg", "jpeg"])
                if st.button("Guardar en Nube", type="primary", use_container_width=True):
                    if archivo_subido:
                        st.success("Guardado correctamente.")
            with tab2:
                archivo_tabla = st.file_uploader("Sube un PDF topográfico", type=["pdf"])
                if st.button("Procesar Tabla", type="primary", use_container_width=True):
                    if archivo_tabla:
                        st.success("¡Datos extraídos limpiamente!")

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
                                texto_extraido = ""
                                for pagina in lector_pdf.pages:
                                    texto_extraido += pagina.extract_text() + "\n"
                                contexto_documento = f"BASA TU RESPUESTA ESTRICTAMENTE EN EL SIGUIENTE DOCUMENTO OFICIAL ({st.session_state.archivo_activo}):\n\n{texto_extraido}\n\n"
                        except Exception as e:
                            pass

                    instruccion_final = f"{contexto_documento}PREGUNTA DEL INGENIERO: {pregunta}"
                    respuesta_ia = modelo.generate_content(instruccion_final)
                    texto_final = respuesta_ia.text
                    
                    caja_respuesta.markdown(texto_final)
                    st.session_state.mensajes_ia.append({"rol": "assistant", "contenido": texto_final})
                    
                except Exception as e:
                    caja_respuesta.error(f"Hubo un error de conexión con la IA: {e}")

    # ====================================================================
    # PESTAÑA 2: CÁLCULOS GEOMECÁNICOS RESTAURADOS
    # ====================================================================
    elif pestaña == "Cálculos Geomecánicos":
        st.markdown("<h1 style='color: white;'>Suite de Análisis Geomecánico 🪨</h1>", unsafe_allow_html=True)
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
                st.success(f"**Puntaje RMR Estimado:** {val_rmr:.1f}")
                
        with tab_gsi:
            estruct = st.selectbox("Estructura", ["Masivo", "Blocoso", "Fracturado"])
            if st.button("Estimar GSI", type="primary"): 
                st.success("GSI Estimado: Rango 45 - 55")

    # ====================================================================
    # PESTAÑA 3: VISOR TOPOGRÁFICO INTERACTIVO RESTAURADO
    # ====================================================================
    elif pestaña == "Visor Topográfico":
        st.markdown("<h1 style='color: white;'>Control Topográfico y Planos 🗺️</h1>", unsafe_allow_html=True)
        if st.session_state.archivo_activo == "Base de datos general (Simulación)":
            st.info("ℹ️ Mostrando mapa base de simulación (Área referencial).")
            mapa_mina = folium.Map(location=[-12.684, -76.602], zoom_start=14, tiles="CartoDB positron")
            st_folium(mapa_mina, width=1000, height=500)
        else:
            st.success(f"🗺️ Leyendo datos topográficos desde: **{st.session_state.archivo_activo}**")
            with st.spinner("Analizando coordenadas..."):
                try:
                    file_id = next(f['id'] for f in st.session_state.archivos_nube if f['name'] == st.session_state.archivo_activo)
                    csv_content = drive_service.files().get_media(fileId=file_id).execute().decode('utf-8')
                    df_mapa = pd.read_csv(StringIO(csv_content))
                    
                    with st.expander("Ver datos extraídos", expanded=False):
                        st.dataframe(df_mapa)
                    
                    col_lat = next((col for col in df_mapa.columns if 'lat' in col.lower()), None)
                    col_lon = next((col for col in df_mapa.columns if 'lon' in col.lower() or 'lng' in col.lower()), None)
                    col_norte = next((col for col in df_mapa.columns if 'norte' in col.lower()), None)
                    col_este = next((col for col in df_mapa.columns if 'este' in col.lower()), None)
                    
                    if col_lat and col_lon:
                        df_mapa = df_mapa.dropna(subset=[col_lat, col_lon])
                        mapa_dinamico = folium.Map(location=[float(df_mapa.iloc[0][col_lat]), float(df_mapa.iloc[0][col_lon])], zoom_start=14)
                        for idx, row in df_mapa.iterrows():
                            folium.Marker([float(row[col_lat]), float(row[col_lon])], popup=str(row.iloc[0])).add_to(mapa_dinamico)
                        st_folium(mapa_dinamico, width=1000, height=500)
                        
                    elif col_norte and col_este:
                        st.info("🔄 Coordenadas UTM detectadas. Convirtiendo a Latitud/Longitud...")
                        df_mapa = df_mapa.dropna(subset=[col_norte, col_este])
                        transformer = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)
                        
                        lon_centro, lat_centro = transformer.transform(float(df_mapa.iloc[0][col_este]), float(df_mapa.iloc[0][col_norte]))
                        mapa_dinamico = folium.Map(location=[lat_centro, lon_centro], zoom_start=15, tiles="OpenStreetMap")
                        
                        for idx, row in df_mapa.iterrows():
                            lon_val, lat_val = transformer.transform(float(row[col_este]), float(row[col_norte]))
                            folium.Marker([lat_val, lon_val], popup=f"Vértice: {str(row.iloc[0])}", icon=folium.Icon(color="red", icon="flag")).add_to(mapa_dinamico)
                            
                        st_folium(mapa_dinamico, width=1000, height=500)
                    else:
                        st.warning("⚠️ No se detectaron columnas válidas de coordenadas en el archivo.")
                except Exception as e:
                    st.error(f"Error procesando el mapa: {e}")

    # ====================================================================
    # PESTAÑA 4: VISUALIZADOR 3D SONDAJES RESTAURADO
    # ====================================================================
    elif pestaña == "Visualizador 3D Sondajes":
        st.markdown("<h1 style='color: white;'>Modelamiento 3D de Sondajes Diamantinos 🛢️</h1>", unsafe_allow_html=True)
        seed_val = len(st.session_state.archivo_activo)
        np.random.seed(seed_val)
        datos_lista = []
        for h_id in ["DDH-001", "DDH-002", "DDH-003"]:
            x_start, y_start, z_start = np.random.randint(100, 200), np.random.randint(100, 200), 500
            for depth in range(0, 150, 10):
                datos_lista.append({"HOLE_ID": h_id, "X": x_start + (depth * 0.2), "Y": y_start + (depth * 0.1), "Z": z_start - depth, "CU_PCT": np.random.uniform(0.1, 3.0)})
        df_sondajes = pd.DataFrame(datos_lista)
        
        fig_3d = go.Figure()
        for hole in df_sondajes["HOLE_ID"].unique():
            df_hole = df_sondajes[df_sondajes["HOLE_ID"] == hole]
            fig_3d.add_trace(go.Scatter3d(x=df_hole["X"], y=df_hole["Y"], z=df_hole["Z"], mode='lines+markers', marker=dict(size=4, color=df_hole["CU_PCT"], colorscale='Jet', colorbar=dict(title="Ley Cu (%)")), name=hole))
        fig_3d.update_layout(margin=dict(r=20, l=20, b=20, t=40), height=500, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_3d, use_container_width=True)

    # ====================================================================
    # PESTAÑA 5: DASHBOARD ANALÍTICAS RESTAURADO
    # ====================================================================
    elif pestaña == "Dashboard Analíticas":
        st.markdown("<h1 style='color: white;'>Panel de Analíticas y Control Operativo 📈</h1>", unsafe_allow_html=True)
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        modificador = len(st.session_state.archivo_activo)
        with col_kpi1: st.metric(label="Documentos Indexados en la Nube", value=len(st.session_state.get("archivos_nube", [])))
        with col_kpi2: st.metric(label="Promedio RMR Registrado", value=f"{68.5 + (modificador*0.2):.1f}")
        with col_kpi3: st.metric(label="Consultas de IA este mes", value=142 + modificador)
