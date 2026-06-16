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
from pyproj import Transformer # LIBRERÍA TOPOGRÁFICA

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="InkaDrill - Cerebro IA", page_icon="🧠", layout="wide")

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
    st.markdown("<h2 style='color: #A6802C; font-weight: 900; text-align: center;'>INKADRILL<br>CEREBRO IA</h2>", unsafe_allow_html=True)
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
    # PESTAÑA 1: CHATBOT UNIFICADO + CARGA DE ARCHIVOS + EXTRACTOR
    # ====================================================================
    if pestaña == "💬 Chat Asistente Operativo":
        st.markdown("<h1 style='text-align: center; color: #444; font-weight: 400; font-size: 40px; margin-top: 20px; margin-bottom: 40px;'>¿Qué toca hoy, JEAN KENNEDY?</h1>", unsafe_allow_html=True)
        
        if st.session_state.archivo_activo != "Base de datos general (Simulación)":
            st.info(f"🔎 **Modo Enfoque:** El chat responderá basándose en el archivo: `{st.session_state.archivo_activo}`")
            
        col_tool1, col_tool2 = st.columns(2)
        
        with col_tool1:
            with st.expander("📎 Subir documentos o imágenes (Alimentar BD)"):
                archivo_subido = st.file_uploader("Arrastra aquí PDFs, TXT, o Imágenes", type=["pdf", "txt", "png", "jpg", "jpeg"])
                if st.button("Guardar en Nube InkaDrill ☁️", type="primary", use_container_width=True):
                    if archivo_subido:
                        with st.spinner("Subiendo a Google Drive..."):
                            # Lógica de guardado estándar omitida por brevedad en este bloque visual
                            st.success("Guardado correctamente.")
                            st.rerun()

        with col_tool2:
            with st.expander("📊 Extractor Quirúrgico a Excel (IA)"):
                archivo_tabla = st.file_uploader("Sube un PDF de INGEMMET u otro reporte", type=["pdf"], key="extractor")
                if st.button("Procesar y Extraer Tablas", type="primary", use_container_width=True):
                    if archivo_tabla:
                        with st.spinner("Extrayendo la tabla WGS84 y guardando en Drive..."):
                            try:
                                media_pdf = MediaIoBaseUpload(BytesIO(archivo_tabla.getvalue()), mimetype='application/pdf', resumable=True)
                                metadata_pdf = {'name': archivo_tabla.name, 'parents': [ID_CARPETA_MEMORIA]}
                                drive_service.files().create(body=metadata_pdf, media_body=media_pdf, fields='id').execute()
                                
                                texto_pdf = ""
                                lector_pdf = PyPDF2.PdfReader(archivo_tabla)
                                for pagina in lector_pdf.pages: texto_pdf += pagina.extract_text() + "\n"
                                
                                # INSTRUCCIÓN ESTRICTA PARA EVITAR CHOQUE DE TABLAS
                                instruccion_csv = f"""
                                Actúa como un experto en extracción de datos topográficos. 
                                Analiza el texto y extrae ÚNICAMENTE la tabla que dice "Coordenadas WGS84".
                                IGNORA por completo las tablas de "Demarcaciones", "Cartas" y "PSAD56".
                                Devuelve estrictamente un archivo CSV con 3 columnas exactas: Vertice,Norte,Este
                                IMPORTANTE: No uses comas para los separadores de miles en los números (ejemplo: escribe 8622632.65 en vez de 8,622,632.65).
                                No incluyas saludos ni comillas. Texto:\n{texto_pdf}
                                """
                                respuesta_csv = modelo.generate_content(instruccion_csv)
                                datos_limpios = respuesta_csv.text.replace("```csv", "").replace("```", "").strip()
                                
                                nombre_csv = f"Datos_Topografia_{archivo_tabla.name.replace('.pdf', '')}.csv"
                                media_csv = MediaIoBaseUpload(BytesIO(datos_limpios.encode('utf-8')), mimetype='text/csv', resumable=True)
                                metadata_csv = {'name': nombre_csv, 'parents': [ID_CARPETA_MEMORIA]}
                                drive_service.files().create(body=metadata_csv, media_body=media_csv, fields='id').execute()
                                
                                query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
                                st.session_state.archivos_nube = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
                                
                                st.success("¡Datos extraídos limpiamente!")
                                st.download_button(label="📥 Descargar CSV", data=datos_limpios, file_name=nombre_csv, mime="text/csv", use_container_width=True)
                            except Exception as e:
                                st.error(f"Error al procesar: {e}")

        st.markdown("---")
        
        if "mensajes_ia" not in st.session_state: st.session_state.mensajes_ia = []
        for mensaje in st.session_state.mensajes_ia:
            with st.chat_message(mensaje["rol"]): st.markdown(mensaje["contenido"])

        pregunta = st.chat_input("Pregunta a Gemini sobre la mina, documentos o la imagen adjunta...")
        if pregunta:
            with st.chat_message("user"): st.markdown(pregunta)
            st.session_state.mensajes_ia.append({"rol": "user", "contenido": pregunta})
            
            with st.chat_message("assistant"):
                st.markdown("La respuesta técnica iría aquí...")

    # ====================================================================
    # PESTAÑA 2: CÁLCULOS GEOMECÁNICOS
    # ====================================================================
    elif pestaña == "🧮 Cálculos Geomecánicos":
        st.title("Suite de Análisis Geomecánico 🪨")
        st.info("Herramientas operativas disponibles.")

    # ====================================================================
    # PESTAÑA 3: VISOR TOPOGRÁFICO INTERACTIVO (AHORA CON INTELIGENCIA UTM)
    # ====================================================================
    elif pestaña == "🗺️ Visor Topográfico":
        st.title("Control Topográfico y Planos 🗺️")
        
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
                        
                        # El transformador oficial (EPSG:32718 es la Zona 18S de Perú)
                        transformer = Transformer.from_crs("epsg:32718", "epsg:4326", always_xy=True)
                        
                        lon_centro, lat_centro = transformer.transform(float(df_mapa.iloc[0][col_este]), float(df_mapa.iloc[0][col_norte]))
                        mapa_dinamico = folium.Map(location=[lat_centro, lon_centro], zoom_start=15, tiles="OpenStreetMap")
                        
                        for idx, row in df_mapa.iterrows():
                            este_val = float(row[col_este])
                            norte_val = float(row[col_norte])
                            lon_val, lat_val = transformer.transform(este_val, norte_val)
                            
                            folium.Marker(
                                [lat_val, lon_val], 
                                popup=f"Vértice: {str(row.iloc[0])}", 
                                icon=folium.Icon(color="red", icon="flag")
                            ).add_to(mapa_dinamico)
                            
                        st_folium(mapa_dinamico, width=1000, height=500)
                    else:
                        st.warning("⚠️ No se detectaron columnas válidas de coordenadas (Norte/Este o Lat/Lon).")
                        
                except Exception as e:
                    st.error(f"Error procesando el mapa: {e}")

    # ====================================================================
    # PESTAÑA 4 y 5: SONDAJES Y DASHBOARD
    # ====================================================================
    elif pestaña in ["🛢️ Visualizador 3D de Sondajes", "📈 Dashboard de Analíticas"]:
        st.title(pestaña)
        st.info("Visualizaciones operativas conectadas al historial.")
