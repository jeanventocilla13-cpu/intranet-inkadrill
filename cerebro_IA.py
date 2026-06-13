import streamlit as st
import google.generativeai as genai
import os
import PyPDF2
import json
from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="InkaDrill - Cerebro IA", page_icon="🧠", layout="wide")

# Tu ID de carpeta en Google Drive
ID_CARPETA_MEMORIA = "1L-6rI-3lu4m0PoXk8Y1brudQC9PrkGCn"

# --- 2. CONEXIÓN A LAS IA Y GOOGLE DRIVE ---
try:
    # 2.1 Conectar Gemini
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    modelo = genai.GenerativeModel('gemini-1.5-flash')
    
    # 2.2 Conectar Google Drive (Usando los secretos de Streamlit)
    SCOPES = ['https://www.googleapis.com/auth/drive']
    # Convertimos el texto del secreto en un diccionario que Google pueda leer
    token_dict = json.loads(st.secrets["GOOGLE_TOKEN"])
    creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
    
    drive_service = build('drive', 'v3', credentials=creds)
    conexion_exitosa = True
except Exception as e:
    conexion_exitosa = False
    st.error(f"Error de conexión con los servidores: {e}")

# --- 3. BARRA LATERAL (MENÚ IZQUIERDO ESTILO ESTÁNDAR) ---
with st.sidebar:
    st.markdown("<h2 style='color: #A6802C; font-weight: 900; text-align: center;'>INKADRILL<br>CEREBRO IA</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Menú de navegación lateral
    pestaña = st.radio(
        "Navegación:",
        ["💬 Chat Asistente Operativo", "📂 Alimentar Base de Datos"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("<p style='font-size: 11px; color: #888; text-align: center;'>InkaDrill 2026 ©<br>Gestión de Conocimiento Minero</p>", unsafe_allow_html=True)

# Solo mostramos el contenido principal si hay conexión exitosa con las APIs
if conexion_exitosa:
    # ====================================================================
    # PESTAÑA 1: CHATBOT (Lee los archivos .txt desde Google Drive)
    # ====================================================================
    if pestaña == "💬 Chat Asistente Operativo":
        st.title("Asistente Operativo InkaDrill ⛏️")
        st.markdown("Realiza consultas técnicas. La IA buscará las respuestas en los documentos almacenados en tu Google Drive corporativo.")
        
        if "mensajes_ia" not in st.session_state:
            st.session_state.mensajes_ia = []

        for mensaje in st.session_state.mensajes_ia:
            with st.chat_message(mensaje["rol"]):
                st.markdown(mensaje["contenido"])

        pregunta = st.chat_input("Escribe tu consulta geomecánica, de sostenimiento o topográfica...")
        
        if pregunta:
            with st.chat_message("user"):
                st.markdown(pregunta)
            st.session_state.mensajes_ia.append({"rol": "user", "contenido": pregunta})
            
            contexto_documentos = ""
            
            with st.spinner("Conectando a la base de datos documental en Google Drive..."):
                try:
                    query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
                    archivos_drive = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
                    
                    for archivo in archivos_drive:
                        file_id = archivo['id']
                        file_name = archivo['name']
                        contenido_archivo = drive_service.files().get_media(fileId=file_id).execute().decode('utf-8')
                        contexto_documentos += f"\n\n=== DOCUMENTO: {file_name} ===\n{contenido_archivo}"
                except Exception as e:
                    st.error(f"Error al leer los documentos: {e}")
                    
            instruccion = f"""
            Eres un Ingeniero de Minas experto que labora en InkaDrill. 
            Responde a la consulta del usuario basándote ESTRICTAMENTE en la siguiente base de conocimientos:
            {contexto_documentos}
            Si la información no se encuentra registrada en los documentos provistos, indica amablemente: 
            "La información no se encuentra registrada en la base de datos documental actual de InkaDrill."
            Consulta: {pregunta}
            """
            
            with st.chat_message("assistant"):
                with st.spinner("Procesando respuesta técnica..."):
                    try:
                        respuesta_modelo = modelo.generate_content(instruccion)
                        st.markdown(respuesta_modelo.text)
                        st.session_state.mensajes_ia.append({"rol": "assistant", "contenido": respuesta_modelo.text})
                    except Exception as e:
                        st.error(f"Error al generar la respuesta con IA: {e}")

    # ====================================================================
    # PESTAÑA 2: SUBIR DOCUMENTOS (Sube PDFs/TXT a Drive)
    # ====================================================================
    elif pestaña == "📂 Alimentar Base de Datos":
        st.title("Alimentar Base de Datos Documental 🧠")
        st.markdown("Sube manuales o reportes. El sistema extraerá el texto y lo guardará en tu carpeta de Google Drive.")
        
        archivo_subido = st.file_uploader("Selecciona un archivo PDF o TXT", type=["pdf", "txt"])
        
        if st.button("Subir y Guardar en Google Drive", use_container_width=True, type="primary"):
            if archivo_subido is not None:
                texto_extraido = ""
                with st.spinner("Extrayendo texto del documento..."):
                    if archivo_subido.name.endswith(".txt"):
                        texto_extraido = archivo_subido.read().decode("utf-8")
                    elif archivo_subido.name.endswith(".pdf"):
                        lector_pdf = PyPDF2.PdfReader(archivo_subido)
                        for pagina in lector_pdf.pages:
                            texto_extraido += pagina.extract_text() + "\n"
                    
                    metadata_archivo = {
                        'name': f"{archivo_subido.name}.txt",
                        'parents': [ID_CARPETA_MEMORIA]
                    }
                    media_cuerpo = MediaIoBaseUpload(
                        BytesIO(texto_extraido.encode('utf-8')), 
                        mimetype='text/plain', 
                        chunksize=1024*1024, 
                        resumable=True
                    )
                    drive_service.files().create(body=metadata_archivo, media_body=media_cuerpo, fields='id').execute()
                        
                st.success(f"¡El archivo '{archivo_subido.name}' fue convertido a texto y guardado en Google Drive!")
            else:
                st.warning("Por favor, carga un archivo primero.")
                
        st.markdown("---")
        st.markdown("### 📂 Documentos actualmente en la nube:")
        with st.spinner("Cargando lista de documentos..."):
            try:
                query_lista = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
                archivos_actuales = drive_service.files().list(q=query_lista, fields="files(name)").execute().get('files', [])
                if len(archivos_actuales) > 0:
                    for arch in archivos_actuales:
                        st.markdown(f"📄 `{arch['name']}`")
                else:
                    st.info("La carpeta en Google Drive está vacía.")
            except Exception as e:
                st.error("No se pudo conectar a Google Drive para listar los archivos.")
