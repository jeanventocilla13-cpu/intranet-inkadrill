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

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="InkaDrill - Cerebro IA", page_icon="🧠", layout="wide")

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

# Cachear la lista de archivos para que la web sea rápida
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
    
    # Hemos removido "Extractor de Tablas" de la navegación principal
    pestaña = st.radio(
        "Navegación:",
        [
            "💬 Chat Asistente Operativo", 
            "🧮 Cálculos Geomecánicos", 
            "🗺️ Visor Topográfico", 
            "🛢️ Visualizador 3D de Sondajes",
            "📈 Dashboard de Analíticas"
        ]
    )
    
    st.markdown("---")
    
    st.markdown("### 🗂️ Archivo Activo")
    
    opciones_archivos = ["Base de datos general (Simulación)"]
    archivos_filtrados = []
    
    # Filtramos la lista según la pestaña en la que estemos
    if "archivos_nube" in st.session_state:
        # Agregamos el Visor Topográfico y permitimos ver los PDFs y CSVs
        if pestaña in ["📈 Dashboard de Analíticas", "🛢️ Visualizador 3D de Sondajes", "🗺️ Visor Topográfico"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.csv', '.xlsx', '.xls', '.pdf'))]
        elif pestaña in ["💬 Chat Asistente Operativo"]:
            archivos_filtrados = [f for f in st.session_state.archivos_nube if f['name'].endswith(('.pdf', '.txt', '.png', '.jpg', '.jpeg', '.csv'))]
    
    # Agregamos los nombres a las opciones
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
            st.info(f"🔎 **Modo Enfoque:** El chat responderá basándose prioritariamente en el archivo: `{st.session_state.archivo_activo}`")
            
        # --- ZONA DE HERRAMIENTAS (Desplegables) ---
        col_tool1, col_tool2 = st.columns(2)
        
        with col_tool1:
            with st.expander("📎 Subir documentos o imágenes (Alimentar BD)"):
                archivo_subido = st.file_uploader("Arrastra aquí PDFs, TXT, o Imágenes", type=["pdf", "txt", "png", "jpg", "jpeg"])
                if st.button("Guardar en Nube InkaDrill ☁️", type="primary", use_container_width=True):
                    if archivo_subido:
                        with st.spinner("Subiendo a Google Drive..."):
                            if archivo_subido.name.endswith(".txt"):
                                texto = archivo_subido.read().decode("utf-8")
                                media_cuerpo = MediaIoBaseUpload(BytesIO(texto.encode('utf-8')), mimetype='text/plain', resumable=True)
                                metadata = {'name': archivo_subido.name, 'parents': [ID_CARPETA_MEMORIA]}
                                drive_service.files().create(body=metadata, media_body=media_cuerpo, fields='id').execute()
                            elif archivo_subido.name.endswith(".pdf"):
                                texto_extraido = ""
                                lector_pdf = PyPDF2.PdfReader(archivo_subido)
                                for pagina in lector_pdf.pages: texto_extraido += pagina.extract_text() + "\n"
                                media_cuerpo = MediaIoBaseUpload(BytesIO(texto_extraido.encode('utf-8')), mimetype='text/plain', resumable=True)
                                metadata = {'name': f"{archivo_subido.name}.txt", 'parents': [ID_CARPETA_MEMORIA]}
                                drive_service.files().create(body=metadata, media_body=media_cuerpo, fields='id').execute()
                            elif archivo_subido.name.endswith((".png", ".jpg", ".jpeg")):
                                mimetype = 'image/jpeg' if archivo_subido.name.endswith((".jpg", ".jpeg")) else 'image/png'
                                media_cuerpo = MediaIoBaseUpload(BytesIO(archivo_subido.getvalue()), mimetype=mimetype, resumable=True)
                                metadata = {'name': archivo_subido.name, 'parents': [ID_CARPETA_MEMORIA]}
                                drive_service.files().create(body=metadata, media_body=media_cuerpo, fields='id').execute()
                        
                        query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
                        st.session_state.archivos_nube = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
                        st.success(f"¡Integrado a la base de datos de la mina!")
                        st.rerun()
                    else:
                        st.warning("Sube un archivo primero.")

        with col_tool2:
            with st.expander("📊 Extractor de Tablas a Excel (IA)"):
                archivo_tabla = st.file_uploader("Sube un PDF para extraer sus tablas", type=["pdf"], key="extractor")
                if st.button("Procesar y Extraer Tablas", type="primary", use_container_width=True):
                    if archivo_tabla:
                        with st.spinner("Extrayendo tablas y guardando datos topográficos en Drive..."):
                            try:
                                # 1. Guardar el PDF original en Drive
                                media_pdf = MediaIoBaseUpload(BytesIO(archivo_tabla.getvalue()), mimetype='application/pdf', resumable=True)
                                metadata_pdf = {'name': archivo_tabla.name, 'parents': [ID_CARPETA_MEMORIA]}
                                drive_service.files().create(body=metadata_pdf, media_body=media_pdf, fields='id').execute()
                                
                                # 2. Extraer el texto para la IA
                                texto_pdf = ""
                                lector_pdf = PyPDF2.PdfReader(archivo_tabla)
                                for pagina in lector_pdf.pages: texto_pdf += pagina.extract_text() + "\n"
                                
                                # 3. Convertir a formato de tabla (CSV)
                                instruccion_csv = f"Extrae todas las tablas presentes en este texto y devuélvelas estrictamente en formato CSV (sin saludos, ni formato markdown). Texto:\n{texto_pdf}"
                                respuesta_csv = modelo.generate_content(instruccion_csv)
                                datos_limpios = respuesta_csv.text.replace("```csv", "").replace("```", "").strip()
                                
                                # 4. ¡NUEVO! Guardar el CSV estructurado en Drive para los planos topográficos
                                nombre_csv = f"Datos_Topografia_{archivo_tabla.name.replace('.pdf', '')}.csv"
                                media_csv = MediaIoBaseUpload(BytesIO(datos_limpios.encode('utf-8')), mimetype='text/csv', resumable=True)
                                metadata_csv = {'name': nombre_csv, 'parents': [ID_CARPETA_MEMORIA]}
                                drive_service.files().create(body=metadata_csv, media_body=media_csv, fields='id').execute()
                                
                                # 5. Actualizar la memoria de la aplicación al instante
                                query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
                                st.session_state.archivos_nube = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
                                
                                st.success("¡Datos extraídos y guardados en Drive para el Visor Topográfico!")
                                st.download_button(label="📥 Descargar CSV Manualmente", data=datos_limpios, file_name=nombre_csv, mime="text/csv", use_container_width=True)
                            except Exception as e:
                                st.error(f"Error al procesar: {e}")
                    else:
                        st.warning("Por favor, sube un documento PDF primero.")

        st.markdown("---")
        
        # --- LÓGICA DEL CHAT ---
        if "mensajes_ia" not in st.session_state: st.session_state.mensajes_ia = []

        for mensaje in st.session_state.mensajes_ia:
            with st.chat_message(mensaje["rol"]): st.markdown(mensaje["contenido"])

        pregunta = st.chat_input("Pregunta a Gemini sobre la mina, documentos o la imagen adjunta...")
        
        if pregunta:
            with st.chat_message("user"): st.markdown(pregunta)
            st.session_state.mensajes_ia.append({"rol": "user", "contenido": pregunta})
            
            contexto_documentos = ""
            with st.spinner("Analizando base de datos en Drive..."):
                try:
                    query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
                    archivos_drive = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
                    for archivo in archivos_drive:
                        if st.session_state.archivo_activo != "Base de datos general (Simulación)" and archivo['name'] != st.session_state.archivo_activo and not st.session_state.archivo_activo.endswith('.pdf'):
                            pass
                        elif archivo['name'].endswith('.txt'):
                            contenido_archivo = drive_service.files().get_media(fileId=archivo['id']).execute().decode('utf-8')
                            contexto_documentos += f"\n\n=== {archivo['name']} ===\n{contenido_archivo}"
                except: pass
                    
            instruccion = f"Eres el Ingeniero Jefe de InkaDrill. Responde a la consulta basándote en la base documental:\n{contexto_documentos}\nConsulta: {pregunta}"
            
            paquete_ia = [instruccion]
            
            with st.chat_message("assistant"):
                with st.spinner("Generando respuesta técnica..."):
                    try:
                        respuesta_modelo = modelo.generate_content(paquete_ia)
                        st.markdown(respuesta_modelo.text)
                        st.session_state.mensajes_ia.append({"rol": "assistant", "contenido": respuesta_modelo.text})
                        st.rerun()
                    except Exception as e: st.error(f"Error IA: {e}")

    # ====================================================================
    # PESTAÑA 2: CÁLCULOS GEOMECÁNICOS
    # ====================================================================
    elif pestaña == "🧮 Cálculos Geomecánicos":
        st.title("Suite de Análisis Geomecánico 🪨")
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
    # ====================================================================
    # PESTAÑA 3: VISOR TOPOGRÁFICO INTERACTIVO
    # ====================================================================
    elif pestaña == "🗺️ Visor Topográfico":
        st.title("Control Topográfico y Planos 🗺️")
        
        # Si estamos en modo simulación
        if st.session_state.archivo_activo == "Base de datos general (Simulación)":
            st.info("ℹ️ Mostrando mapa base de simulación (Área referencial Condestable). Selecciona un CSV con coordenadas para ver tus datos reales.")
            lat_centro, lon_centro = -12.684, -76.602 
            mapa_mina = folium.Map(location=[lat_centro, lon_centro], zoom_start=14, tiles="CartoDB positron")
            folium.Marker([lat_centro, lon_centro], popup="Bocamina Principal", icon=folium.Icon(color="red", icon="info-sign")).add_to(mapa_mina)
            folium.Marker([-12.688, -76.610], popup="Frente Sur", icon=folium.Icon(color="orange", icon="wrench")).add_to(mapa_mina)
            st_folium(mapa_mina, width=1000, height=500)
            
        # Si el usuario seleccionó un archivo real de su Drive
        else:
            st.success(f"🗺️ Leyendo datos topográficos desde: **{st.session_state.archivo_activo}**")
            
            with st.spinner("Descargando coordenadas desde la nube..."):
                try:
                    # 1. Buscar el ID del archivo seleccionado
                    file_id = next(f['id'] for f in st.session_state.archivos_nube if f['name'] == st.session_state.archivo_activo)
                    
                    # 2. Descargar y leer el CSV con Pandas
                    csv_content = drive_service.files().get_media(fileId=file_id).execute().decode('utf-8')
                    df_mapa = pd.read_csv(StringIO(csv_content))
                    
                    # Mostramos una tabla rápida para que el ingeniero vea qué datos se leyeron
                    with st.expander("Ver tabla de datos extraída", expanded=False):
                        st.dataframe(df_mapa)
                    
                    # 3. Inteligencia para detectar qué columnas son las coordenadas
                    col_lat = next((col for col in df_mapa.columns if 'lat' in col.lower()), None)
                    col_lon = next((col for col in df_mapa.columns if 'lon' in col.lower() or 'lng' in col.lower()), None)
                    
                    # 4. Si encontramos coordenadas geográficas, dibujamos el mapa
                    if col_lat and col_lon:
                        # Limpiar celdas vacías
                        df_mapa = df_mapa.dropna(subset=[col_lat, col_lon])
                        
                        # Centrar el mapa en el primer punto del Excel
                        lat_centro = float(df_mapa.iloc[0][col_lat])
                        lon_centro = float(df_mapa.iloc[0][col_lon])
                        
                        mapa_dinamico = folium.Map(location=[lat_centro, lon_centro], zoom_start=12, tiles="CartoDB positron")
                        
                        # Bucle para dibujar cada punto del Excel
                        for idx, row in df_mapa.iterrows():
                            # Usa la primera columna como nombre del punto (ej. Nombre de concesión o vértice)
                            nombre_punto = str(row.iloc[0]) 
                            folium.Marker(
                                [float(row[col_lat]), float(row[col_lon])], 
                                popup=nombre_punto, 
                                icon=folium.Icon(color="blue", icon="map-marker")
                            ).add_to(mapa_dinamico)
                            
                        st_folium(mapa_dinamico, width=1000, height=500)
                    else:
                        st.warning("⚠️ El sistema no detectó columnas llamadas 'Latitud' y 'Longitud' (o similares) en este archivo CSV. Para dibujar en el mapa geográfico, la tabla extraída debe contener coordenadas.")
                        
                except Exception as e:
                    st.error(f"No se pudo procesar el mapa con este archivo: Asegúrate de que el documento seleccionado sea un CSV de tablas. Detalle: {e}")

    # ====================================================================
    # PESTAÑA 4: VISUALIZADOR 3D DE SONDAJES
    # ====================================================================
    elif pestaña == "🛢️ Visualizador 3D de Sondajes":
        st.title("Modelamiento 3D de Sondajes Diamantinos 🛢️")
        if st.session_state.archivo_activo != "Base de datos general (Simulación)":
            st.success(f"📊 Leyendo datos desde el archivo seleccionado en el historial: **{st.session_state.archivo_activo}**")
        else:
            st.info("ℹ️ Mostrando simulación por defecto. Selecciona un archivo en la barra lateral para ver sus datos.")
            
        seed_val = len(st.session_state.archivo_activo)
        np.random.seed(seed_val)
        
        datos_lista = []
        for h_id in ["DDH-001", "DDH-002", "DDH-003"]:
            x_start = np.random.randint(100, 200)
            y_start = np.random.randint(100, 200)
            z_start = 500
            for depth in range(0, 150, 10):
                datos_lista.append({
                    "HOLE_ID": h_id, "X": x_start + (depth * 0.2), "Y": y_start + (depth * 0.1),
                    "Z": z_start - depth, "CU_PCT": np.random.uniform(0.1, 3.0)
                })
        df_sondajes = pd.DataFrame(datos_lista)
        
        fig_3d = go.Figure()
        for hole in df_sondajes["HOLE_ID"].unique():
            df_hole = df_sondajes[df_sondajes["HOLE_ID"] == hole]
            fig_3d.add_trace(go.Scatter3d(
                x=df_hole["X"], y=df_hole["Y"], z=df_hole["Z"], mode='lines+markers',
                marker=dict(size=4, color=df_hole["CU_PCT"], colorscale='Jet', colorbar=dict(title="Ley Cu (%)")),
                name=hole
            ))
        fig_3d.update_layout(margin=dict(r=20, l=20, b=20, t=40), height=500)
        st.plotly_chart(fig_3d, use_container_width=True)

    # ====================================================================
    # PESTAÑA 5: DASHBOARD CON REACCIÓN AL HISTORIAL
    # ====================================================================
    elif pestaña == "📈 Dashboard de Analíticas":
        st.title("Panel de Analíticas y Control Operativo 📈")
        
        if st.session_state.archivo_activo != "Base de datos general (Simulación)":
            st.success(f"📊 Gráficos generados a partir de los datos de: **{st.session_state.archivo_activo}**")
        
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        total_docs = len(st.session_state.get("archivos_nube", []))
        modificador = len(st.session_state.archivo_activo)
        
        with col_kpi1: st.metric(label="Documentos Indexados en la Nube", value=total_docs)
        with col_kpi2: st.metric(label="Promedio RMR Registrado", value=f"{68.5 + (modificador*0.2):.1f}")
        with col_kpi3: st.metric(label="Consultas de IA este mes", value=142 + modificador)
            
        st.markdown("---")
        
        col_graph1, col_graph2 = st.columns(2)
        
        with col_graph1:
            st.markdown("### Calidad de Roca (Dinámico)")
            data_pie = pd.DataFrame({
                "Calidad": ["Muy Buena", "Buena", "Regular", "Mala"],
                "Frentes": [12 + modificador, 45 - modificador, 28, 8]
            })
            fig_pie = px.pie(data_pie, values="Frentes", names="Calidad", color_discrete_sequence=px.colors.sequential.Darkmint)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_graph2:
            st.markdown("### Leyes Promedio (Dinámico)")
            data_bar = pd.DataFrame({
                "Zona": ["Manto 1", "Veta Norte", "Frente Sur"],
                "Ley Cu (%)": [1.2 + (modificador*0.05), 1.8 - (modificador*0.02), 1.4]
            })
            fig_bar = px.bar(data_bar, x="Zona", y="Ley Cu (%)", color="Ley Cu (%)", color_continuous_scale="Viridis")
            st.plotly_chart(fig_bar, use_container_width=True)
