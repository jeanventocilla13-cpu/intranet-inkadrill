import streamlit as st
import google.generativeai as genai
import os
import PyPDF2
import json
from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import datetime
from PIL import Image  # NUEVA LIBRERÍA PARA LEER IMÁGENES

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="InkaDrill - Cerebro IA", page_icon="🧠", layout="wide")

# Tu ID de carpeta en Google Drive
ID_CARPETA_MEMORIA = "1L-6rI-3lu4m0PoXk8Y1brudQC9PrkGCn"

# --- 2. CONEXIÓN A LAS IA Y GOOGLE DRIVE ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    modelo = genai.GenerativeModel('gemini-1.5-flash') # Modelo multimodal (Lee texto e imágenes)
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    token_dict = json.loads(st.secrets["GOOGLE_TOKEN"])
    creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
    
    drive_service = build('drive', 'v3', credentials=creds)
    conexion_exitosa = True
except Exception as e:
    conexion_exitosa = False
    st.error(f"Error de conexión con los servidores: {e}")

# --- 3. BARRA LATERAL ESTILO PODEROSA ---
with st.sidebar:
    st.markdown("<h2 style='color: #A6802C; font-weight: 900; text-align: center;'>INKADRILL<br>CEREBRO IA</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Menú simplificado (Sin la pestaña extra de subir documentos)
    pestaña = st.radio(
        "Navegación:",
        ["💬 Chat Asistente Operativo", "🧮 Cálculos Geomecánicos"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("<p style='font-size: 11px; color: #888; text-align: center;'>InkaDrill 2026 ©<br>Gestión de Conocimiento Minero</p>", unsafe_allow_html=True)

if conexion_exitosa:
    # ====================================================================
    # PESTAÑA 1: CHATBOT UNIFICADO Y SUBIDA DE DOCUMENTOS/IMÁGENES
    # ====================================================================
    if pestaña == "💬 Chat Asistente Operativo":
        
        # El saludo personalizado estilo Google Gemini
        st.markdown("<h1 style='text-align: center; color: #444; font-weight: 400; font-size: 40px; margin-top: 20px; margin-bottom: 40px;'>¿Qué toca hoy, JEAN KENNEDY?</h1>", unsafe_allow_html=True)
        
        # --- ZONA DE ADJUNTOS INTEGRADA ---
        with st.expander("📎 Subir documentos o imágenes (Alimentar BD)"):
            archivo_subido = st.file_uploader("Arrastra aquí tus archivos PDF, TXT, PNG o JPG", type=["pdf", "txt", "png", "jpg", "jpeg"])
            
            if st.button("Guardar en Nube InkaDrill ☁️", type="primary"):
                if archivo_subido is not None:
                    with st.spinner("Subiendo a Google Drive..."):
                        if archivo_subido.name.endswith(".txt"):
                            texto = archivo_subido.read().decode("utf-8")
                            media_cuerpo = MediaIoBaseUpload(BytesIO(texto.encode('utf-8')), mimetype='text/plain', resumable=True)
                            metadata = {'name': archivo_subido.name, 'parents': [ID_CARPETA_MEMORIA]}
                            drive_service.files().create(body=metadata, media_body=media_cuerpo, fields='id').execute()
                            
                        elif archivo_subido.name.endswith(".pdf"):
                            texto_extraido = ""
                            lector_pdf = PyPDF2.PdfReader(archivo_subido)
                            for pagina in lector_pdf.pages:
                                texto_extraido += pagina.extract_text() + "\n"
                            media_cuerpo = MediaIoBaseUpload(BytesIO(texto_extraido.encode('utf-8')), mimetype='text/plain', resumable=True)
                            metadata = {'name': f"{archivo_subido.name}.txt", 'parents': [ID_CARPETA_MEMORIA]}
                            drive_service.files().create(body=metadata, media_body=media_cuerpo, fields='id').execute()
                            
                        elif archivo_subido.name.endswith((".png", ".jpg", ".jpeg")):
                            mimetype = 'image/jpeg' if archivo_subido.name.endswith((".jpg", ".jpeg")) else 'image/png'
                            media_cuerpo = MediaIoBaseUpload(BytesIO(archivo_subido.getvalue()), mimetype=mimetype, resumable=True)
                            metadata = {'name': archivo_subido.name, 'parents': [ID_CARPETA_MEMORIA]}
                            drive_service.files().create(body=metadata, media_body=media_cuerpo, fields='id').execute()
                            
                    st.success(f"¡El archivo '{archivo_subido.name}' se integró a la base de datos de la mina!")
                else:
                    st.warning("Selecciona un archivo primero.")
        
        # --- LÓGICA DEL CHAT ---
        if "mensajes_ia" not in st.session_state:
            st.session_state.mensajes_ia = []

        # Mostrar botones de exportación si hay historial
        if len(st.session_state.mensajes_ia) > 0:
            chat_history = "REPORTE TÉCNICO INKADRILL\n" + "="*30 + "\n\n"
            for m in st.session_state.mensajes_ia:
                rol = "JEAN KENNEDY" if m["rol"] == "user" else "SISTEMA IA"
                chat_history += f"[{rol}]:\n{m['contenido']}\n\n"
            st.download_button("📄 Descargar Reporte de la Conversación", data=chat_history, file_name=f"Reporte_{datetime.date.today()}.txt", mime="text/plain")

        # Dibujar mensajes
        for mensaje in st.session_state.mensajes_ia:
            with st.chat_message(mensaje["rol"]):
                st.markdown(mensaje["contenido"])

        # Barra de búsqueda inferior
        pregunta = st.chat_input("Pregunta a Gemini sobre la mina, documentos o la imagen adjunta...")
        
        if pregunta:
            with st.chat_message("user"):
                st.markdown(pregunta)
            st.session_state.mensajes_ia.append({"rol": "user", "contenido": pregunta})
            
            contexto_documentos = ""
            with st.spinner("Analizando base de datos en Drive..."):
                try:
                    # Traemos solo los archivos de texto/PDF convertidos para el contexto del chat
                    query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
                    archivos_drive = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
                    for archivo in archivos_drive:
                        if archivo['name'].endswith('.txt'): # Solo leemos el texto para no romper la IA con binarios de imágenes
                            contenido_archivo = drive_service.files().get_media(fileId=archivo['id']).execute().decode('utf-8')
                            contexto_documentos += f"\n\n=== {archivo['name']} ===\n{contenido_archivo}"
                except:
                    pass
                    
            instruccion = f"""
            Eres el Ingeniero Jefe de InkaDrill. Responde a la consulta basándote en la base documental:
            {contexto_documentos}
            Consulta: {pregunta}
            """
            
            # Preparar los elementos para la IA (Texto + Imagen si hay una cargada en ese momento)
            paquete_ia = [instruccion]
            if archivo_subido and archivo_subido.name.endswith((".png", ".jpg", ".jpeg")):
                imagen_adjunta = Image.open(archivo_subido)
                paquete_ia.append(imagen_adjunta)
            
            with st.chat_message("assistant"):
                with st.spinner("Generando respuesta técnica..."):
                    try:
                        respuesta_modelo = modelo.generate_content(paquete_ia)
                        st.markdown(respuesta_modelo.text)
                        st.session_state.mensajes_ia.append({"rol": "assistant", "contenido": respuesta_modelo.text})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error IA: {e}")

    # ====================================================================
    # PESTAÑA 2: CÁLCULOS GEOMECÁNICOS
    # ====================================================================
    elif pestaña == "🧮 Cálculos Geomecánicos":
        st.title("Suite de Análisis Geomecánico 🪨")
        st.markdown("Herramientas de evaluación rápida para el macizo rocoso en frentes de avance.")
        
        tab_rmr, tab_gsi = st.tabs(["Clasificación RMR", "Índice GSI"])
        
        with tab_rmr:
            st.markdown("### Parámetros de Rock Mass Rating")
            col1, col2 = st.columns(2)
            with col1:
                p1 = st.number_input("1. Resistencia Compresión Simple (MPa)", value=50)
                p2 = st.slider("2. RQD (%)", min_value=0, max_value=100, value=75)
            with col2:
                p4 = st.selectbox("3. Condición de Discontinuidades", ["Cerradas", "Rugosas", "Abiertas"])
            
            if st.button("Calcular RMR", type="primary"):
                puntaje_base = (p2 * 0.2) + (p1 * 0.1) + 30
                st.success(f"**Puntaje RMR Estimado:** {puntaje_base:.1f}")
                    
        with tab_gsi:
            st.markdown("### Geological Strength Index")
            estruct = st.selectbox("Estructura", ["Masivo", "Blocoso", "Fracturado"])
            if st.button("Estimar GSI", type="primary"):
                st.success("GSI Estimado: Rango 45 - 55")
