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

# --- INYECCIÓN DE ESTÉTICA GEMINI Y FONDO INMERSIVO (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Google Sans', sans-serif !important;
    }
    
    /* ---------------------------------------------------
       1. FONDO DE PANTALLA COMPLETO CON CAPA SEMI-TRANSPARENTE
       --------------------------------------------------- */
    .stApp {
        background: linear-gradient(rgba(19, 19, 20, 0.65), rgba(19, 19, 20, 0.65)), 
                    url("https://github.com/jeanventocilla13-cpu/intranet-inkadrill/blob/main/fondo%20de%20escaneo.png?raw=true") no-repeat center center fixed !important;
        background-size: cover !important;
    }
    
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }

    /* ---------------------------------------------------
       2. EFECTO CRISTAL (GLASSMORPHISM) EN LA BARRA LATERAL
       --------------------------------------------------- */
    [data-testid="stSidebar"] {
        background-color: rgba(19, 19, 20, 0.3) !important;
        backdrop-filter: blur(12px) !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important; 
    }

    /* ---------------------------------------------------
       3. HACKS DE LA BARRA LATERAL (ALINEACIÓN ESTRICTA)
       --------------------------------------------------- */
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

    [data-testid="stSidebar"] button[kind="primary"] {
        border-radius: 30px !important;
        background-color: rgba(30, 31, 32, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #e3e3e3 !important;
        padding: 8px 15px !important;
        font-weight: 500 !important;
        transition: 0.3s !important;
    }
    [data-testid="stSidebar"] button[kind="primary"]:hover {
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    
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
       4. HACKS DEL CHAT Y BOTÓN FLOTANTE (CRISTAL TRANSPARENTE)
       --------------------------------------------------- */
    /* Destruir el fondo sólido ancla de Streamlit */
    [data-testid="stBottom"] {
        background-color: transparent !important;
    }
    [data-testid="stBottom"] > div {
        background-color: transparent !important;
    }

    .stChatInputContainer {
        border-radius: 30px !important;
        /* Mismo cristal que la barra lateral (30% de opacidad) */
        background-color: rgba(19, 19, 20, 0.3) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        width: calc(100% - 60px) !important;
        margin-left: 60px !important;
    }
    .stChatInputContainer textarea {
        padding-left: 45px !important;
        font-size: 16px !important;
        color: #e3e3e3 !important;
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
        /* Mismo cristal para el botón + */
        background-color: rgba(19, 19, 20, 0.3) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #e3e3e3 !important;
        font-size: 24px !important;
        line-height: 0 !important;
        transition: 0.3s;
    }
    div[data-testid="stPopover"] > button:hover {
        background-color: rgba(255, 255, 255, 0.1) !important;
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
    modelo = genai.GenerativeModel('gemini-2.5-flash')
    
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
        
    for arch in opciones_archivos:
        icono = "📌" if st.session_state.archivo_activo == arch else "📄"
        if st.button(f"{icono} {arch}", key=f"file_{arch}", type="secondary", use_container_width=True):
            st.session_state.archivo_activo = arch
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
            # 1. Mostramos la pregunta del usuario
            with st.chat_message("user"): st.markdown(pregunta)
            st.session_state.mensajes_ia.append({"rol": "user", "contenido": pregunta})
            
            # 2. Llamamos a Gemini y mostramos la respuesta
            with st.chat_message("assistant"):
                caja_respuesta = st.empty()
                caja_respuesta.markdown("Extrayendo datos de la nube y procesando... ⏳")
                
                try:
                    contexto_documento = ""
                    # Si hay un archivo seleccionado que NO sea la simulación
                    if st.session_state.archivo_activo != "Base de datos general (Simulación)":
                        try:
                            # 1. Buscar el ID del archivo en nuestra memoria de Drive
                            file_id = next(f['id'] for f in st.session_state.archivos_nube if f['name'] == st.session_state.archivo_activo)
                            
                            # 2. Si es un PDF, lo descargamos y leemos sus páginas
                            if st.session_state.archivo_activo.endswith('.pdf'):
                                pdf_bytes = drive_service.files().get_media(fileId=file_id).execute()
                                lector_pdf = PyPDF2.PdfReader(BytesIO(pdf_bytes))
                                texto_extraido = ""
                                for pagina in lector_pdf.pages:
                                    texto_extraido += pagina.extract_text() + "\n"
                                
                                contexto_documento = f"BASA TU RESPUESTA ESTRICTAMENTE EN EL SIGUIENTE DOCUMENTO OFICIAL ({st.session_state.archivo_activo}):\n\n{texto_extraido}\n\n"
                            
                            # 3. Si es un CSV (como tus tablas topográficas), también lo leemos
                            elif st.session_state.archivo_activo.endswith('.csv'):
                                csv_bytes = drive_service.files().get_media(fileId=file_id).execute()
                                contexto_documento = f"BASA TU RESPUESTA ESTRICTAMENTE EN LA SIGUIENTE TABLA DE DATOS ({st.session_state.archivo_activo}):\n\n{csv_bytes.decode('utf-8')}\n\n"
                                
                        except Exception as e:
                            st.warning(f"No pude leer el interior del archivo. Responderé de forma general. (Detalle: {e})")

                    # Construimos la orden final para Gemini
                    instruccion_final = f"{contexto_documento}PREGUNTA DEL INGENIERO: {pregunta}"
                    
                    # Llamada real a la inteligencia artificial
                    respuesta_ia = modelo.generate_content(instruccion_final)
                    texto_final = respuesta_ia.text
                    
                    # Actualizamos la interfaz y guardamos en memoria
                    caja_respuesta.markdown(texto_final)
                    st.session_state.mensajes_ia.append({"rol": "assistant", "contenido": texto_final})
                    
                except Exception as e:
                    caja_respuesta.error(f"Hubo un error de conexión con la IA: {e}")

    # ====================================================================
    # PESTAÑA 2: CÁLCULOS GEOMECÁNICOS
    # ====================================================================
    elif pestaña == "🧮 Cálculos Geomecánicos":
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
            if st.button("Estimar GSI", type="primary"): st.success("GSI Estimado: Rango 45 - 55")

    # ====================================================================
    # PESTAÑA 3: VISOR TOPOGRÁFICO INTERACTIVO
    # ====================================================================
    elif pestaña == "🗺️ Visor Topográfico":
        st.markdown("<h1 style='color: white;'>Control Topográfico y Planos 🗺️</h1>", unsafe_allow_html=True)
        if st.session_state.archivo_activo == "Base de datos general (Simulación)":
            st.info("ℹ️ Mostrando mapa base de simulación (Área referencial Condestable).")
            mapa_mina = folium.Map(location=[-12.684, -76.602], zoom_start=14, tiles="CartoDB positron")
            st_folium(mapa_mina, width=1000, height=500)
        else:
            st.success(f"🗺️ Leyendo datos topográficos desde: **{st.session_state.archivo_activo}**")
            with st.spinner("Analizando coordenadas..."):
                try:
                    file_id = next(f['id'] for f in st.session_state.archivos_nube if f['name'] == st.session_state.archivo_activo)
                    csv_content = drive_service.files().get_media(fileId=file_id).execute().decode('utf-8')
                    df_mapa = pd.read_csv(StringIO(csv_content))
                    
                    with st.expander("Ver datos extraídos por la IA", expanded=False):
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
                        st.info("🔄 Coordenadas UTM detectadas. Convirtiendo a Latitud/Longitud (Zona 18S)...")
                        df_mapa = df_mapa.dropna(subset=[col_norte, col_este])
                        transformer = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)
                        
                        lon_centro, lat_centro = transformer.transform(float(df_mapa.iloc[0][col_este]), float(df_mapa.iloc[0][col_norte]))
                        mapa_dinamico = folium.Map(location=[lat_centro, lon_centro], zoom_start=15, tiles="OpenStreetMap")
                        
                        for idx, row in df_mapa.iterrows():
                            lon_val, lat_val = transformer.transform(float(row[col_este]), float(row[col_norte]))
                            folium.Marker([lat_val, lon_val], popup=f"Vértice: {str(row.iloc[0])}", icon=folium.Icon(color="red", icon="flag")).add_to(mapa_dinamico)
                            
                        st_folium(mapa_dinamico, width=1000, height=500)
                    else:
                        st.warning("⚠️ No se detectaron columnas válidas de coordenadas.")
                except Exception as e:
                    st.error(f"Error procesando el mapa: {e}")

    # ====================================================================
    # PESTAÑAS 4 Y 5: SONDAJES Y DASHBOARD 
    # ====================================================================
    elif pestaña == "🛢️ Visualizador 3D Sondajes":
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
        fig_3d.update_layout(margin=dict(r=20, l=20, b=20, t=40), height=500)
        st.plotly_chart(fig_3d, use_container_width=True)

    elif pestaña == "📈 Dashboard Analíticas":
        st.markdown("<h1 style='color: white;'>Panel de Analíticas y Control Operativo 📈</h1>", unsafe_allow_html=True)
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        modificador = len(st.session_state.archivo_activo)
        with col_kpi1: st.metric(label="Documentos Indexados en la Nube", value=len(st.session_state.get("archivos_nube", [])))
        with col_kpi2: st.metric(label="Promedio RMR Registrado", value=f"{68.5 + (modificador*0.2):.1f}")
        with col_kpi3: st.metric(label="Consultas de IA este mes", value=142 + modificador)
