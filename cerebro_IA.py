import streamlit as st
import google.generativeai as genai
import os
import PyPDF2
import json
import pandas as pd
import folium
from streamlit_folium import st_folium
from io import BytesIO, StringIO
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import datetime
from PIL import Image

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

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='color: #A6802C; font-weight: 900; text-align: center;'>INKADRILL<br>CEREBRO IA</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    pestaña = st.radio(
        "Navegación:",
        [
            "💬 Chat Asistente Operativo", 
            "🧮 Cálculos Geomecánicos", 
            "🗺️ Visor Topográfico", 
            "📊 Extractor de Tablas"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("<p style='font-size: 11px; color: #888; text-align: center;'>InkaDrill 2026 ©<br>Gestión de Conocimiento Minero</p>", unsafe_allow_html=True)

if conexion_exitosa:
    # ====================================================================
    # PESTAÑA 1: CHATBOT UNIFICADO
    # ====================================================================
    if pestaña == "💬 Chat Asistente Operativo":
        st.markdown("<h1 style='text-align: center; color: #444; font-weight: 400; font-size: 40px; margin-top: 20px; margin-bottom: 40px;'>¿Qué toca hoy, JEAN KENNEDY?</h1>", unsafe_allow_html=True)
        
        with st.expander("📎 Subir documentos o imágenes (Alimentar BD)"):
            archivo_subido = st.file_uploader("Arrastra aquí tus archivos PDF, TXT, PNG o JPG", type=["pdf", "txt", "png", "jpg", "jpeg"])
            if st.button("Guardar en Nube InkaDrill ☁️", type="primary"):
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
                    st.success(f"¡El archivo '{archivo_subido.name}' se integró a la base de datos de la mina!")

        if "mensajes_ia" not in st.session_state: st.session_state.mensajes_ia = []

        if len(st.session_state.mensajes_ia) > 0:
            chat_history = "REPORTE TÉCNICO INKADRILL\n" + "="*30 + "\n\n"
            for m in st.session_state.mensajes_ia:
                rol = "JEAN KENNEDY" if m["rol"] == "user" else "SISTEMA IA"
                chat_history += f"[{rol}]:\n{m['contenido']}\n\n"
            st.download_button("📄 Descargar Reporte de la Conversación", data=chat_history, file_name=f"Reporte_{datetime.date.today()}.txt", mime="text/plain")

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
                        if archivo['name'].endswith('.txt'):
                            contenido_archivo = drive_service.files().get_media(fileId=archivo['id']).execute().decode('utf-8')
                            contexto_documentos += f"\n\n=== {archivo['name']} ===\n{contenido_archivo}"
                except: pass
                    
            instruccion = f"Eres el Ingeniero Jefe de InkaDrill. Responde a la consulta basándote en la base documental:\n{contexto_documentos}\nConsulta: {pregunta}"
            
            paquete_ia = [instruccion]
            if archivo_subido and archivo_subido.name.endswith((".png", ".jpg", ".jpeg")):
                paquete_ia.append(Image.open(archivo_subido))
            
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
            st.markdown("### Parámetros de Rock Mass Rating")
            col1, col2 = st.columns(2)
            with col1:
                p1 = st.number_input("Resistencia Compresión Simple (MPa)", value=50)
                p2 = st.slider("RQD (%)", 0, 100, 75)
            with col2:
                p4 = st.selectbox("Condición de Discontinuidades", ["Cerradas", "Rugosas", "Abiertas"])
            if st.button("Calcular RMR", type="primary"):
                st.success(f"**Puntaje RMR Estimado:** {(p2 * 0.2) + (p1 * 0.1) + 30:.1f}")
        with tab_gsi:
            st.markdown("### Geological Strength Index")
            estruct = st.selectbox("Estructura", ["Masivo", "Blocoso", "Fracturado"])
            if st.button("Estimar GSI", type="primary"): st.success("GSI Estimado: Rango 45 - 55")

    # ====================================================================
    # PESTAÑA 3: VISOR TOPOGRÁFICO INTERACTIVO
    # ====================================================================
    elif pestaña == "🗺️ Visor Topográfico":
        st.title("Control Topográfico y Planos 🗺️")
        st.markdown("Visualización interactiva de puntos de interés operativos en superficie.")
        
        # Coordenadas referenciales centradas en el área de Compañía Minera Condestable
        lat_centro, lon_centro = -12.684, -76.602 
        
        mapa_mina = folium.Map(location=[lat_centro, lon_centro], zoom_start=14, tiles="CartoDB positron")
        
        # Marcadores de ejemplo
        folium.Marker([lat_centro, lon_centro], popup="Bocamina Nivel Principal", icon=folium.Icon(color="red", icon="info-sign")).add_to(mapa_mina)
        folium.Marker([-12.688, -76.610], popup="Frente de Avance Sur", icon=folium.Icon(color="orange", icon="wrench")).add_to(mapa_mina)
        folium.Marker([-12.679, -76.595], popup="Zona de Desmonte", icon=folium.Icon(color="gray", icon="trash")).add_to(mapa_mina)
        
        # Renderizar el mapa en Streamlit
        st_folium(mapa_mina, width=1000, height=500)
        
        st.info("💡 En la siguiente fase, conectaremos este mapa a un archivo Excel para que los puntos se dibujen automáticamente según la topografía.")

    # ====================================================================
    # PESTAÑA 4: EXTRACTOR DE TABLAS (IA)
    # ====================================================================
    elif pestaña == "📊 Extractor de Tablas":
        st.title("Extractor de Datos Estructurados 📊")
        st.markdown("Sube un logueo geomecánico o reporte en PDF. Gemini procesará el documento y extraerá las tablas en un formato CSV listo para Excel.")
        
        archivo_tabla = st.file_uploader("Subir PDF con tablas de datos", type=["pdf"], key="extractor")
        
        if st.button("Extraer Tablas a Excel", type="primary"):
            if archivo_tabla:
                with st.spinner("La IA está leyendo y estructurando las tablas del documento..."):
                    try:
                        # Extraemos el texto crudo del PDF
                        texto_pdf = ""
                        lector_pdf = PyPDF2.PdfReader(archivo_tabla)
                        for pagina in lector_pdf.pages:
                            texto_pdf += pagina.extract_text() + "\n"
                        
                        # Le pedimos a Gemini que actúe como un convertidor a CSV
                        instruccion_csv = f"""
                        Eres un experto en análisis de datos. Tu tarea es extraer CUALQUIER tabla presente en el siguiente texto y formatearla estrictamente como un archivo CSV (Valores separados por comas). 
                        No incluyas saludos ni explicaciones, SOLO devuelve el texto en formato CSV listo para ser guardado.
                        
                        TEXTO DEL DOCUMENTO:
                        {texto_pdf}
                        """
                        
                        respuesta_csv = modelo.generate_content(instruccion_csv)
                        datos_limpios = respuesta_csv.text.replace("```csv", "").replace("```", "").strip()
                        
                        st.success("¡Extracción completada con éxito!")
                        
                        # Botón para descargar el CSV
                        st.download_button(
                            label="📥 Descargar Archivo Excel (CSV)",
                            data=datos_limpios,
                            file_name=f"Datos_Extraidos_{datetime.date.today()}.csv",
                            mime="text/csv"
                        )
                        
                        # Vista previa de los datos extraídos
                        st.markdown("### Vista Previa de los Datos:")
                        try:
                            df_preview = pd.read_csv(StringIO(datos_limpios))
                            st.dataframe(df_preview, use_container_width=True)
                        except:
                            st.code(datos_limpios, language="csv")
                            
                    except Exception as e:
                        st.error(f"Hubo un error al procesar el archivo: {e}")
            else:
                st.warning("Por favor, sube un documento PDF primero.")
