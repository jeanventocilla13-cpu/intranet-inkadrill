import streamlit as st
import os
import PyPDF2
from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload

# --- 1. CONFIGURACIÓN DE LA PÁGINA Y GOOGLE DRIVE ---
st.set_page_config(page_title="InkaDrill - Cerebro IA", page_icon="🧠", layout="wide")

# ►► PEGA AQUÍ EL ID DE TU CARPETA DE GOOGLE DRIVE ◄◄
ID_CARPETA_MEMORIA = "1L-6rI-3lu4m0PoXk8Y1brudQC9PrkGCn"

# Asumimos que drive_service ya está disponible por tu conexión principal.
# Si estás en un archivo separado, recuerda importar o inicializar tu service de Google Drive aquí.

# --- 2. BARRA LATERAL (MENÚ IZQUIERDO ESTILO ESTándar) ---
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

# ====================================================================
# PESTAÑA 1: CHATBOT (Lee los archivos .txt desde Google Drive)
# ====================================================================
if pestaña == "💬 Chat Asistente Operativo":
    st.title("Asistente Operativo InkaDrill ⛏️")
    st.markdown("Realiza consultas técnicas. La IA buscará las respuestas en los documentos almacenados en tu Google Drive corporativo.")
    
    # Historial de chat en sesión
    if "mensajes_ia" not in st.session_state:
        st.session_state.mensajes_ia = []

    # Mostrar mensajes anteriores
    for mensaje in st.session_state.mensajes_ia:
        with st.chat_message(mensaje["rol"]):
            st.markdown(mensaje["contenido"])

    # Caja de texto para preguntar
    pregunta = st.chat_input("Escribe tu consulta geomecánica, de sostenimiento o topográfica...")
    
    if pregunta:
        # 1. Mostrar pregunta en pantalla
        with st.chat_message("user"):
            st.markdown(pregunta)
        st.session_state.mensajes_ia.append({"rol": "user", "contenido": pregunta})
        
        # 2. Conectar a Google Drive y leer todos los archivos de la carpeta
        contexto_documentos = ""
        
        with st.spinner("Conectando a la base de datos documental en Google Drive..."):
            try:
                query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
                archivos_drive = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
                
                for archivo in archivos_drive:
                    file_id = archivo['id']
                    file_name = archivo['name']
                    # Descargamos el contenido del archivo de texto
                    contenido_archivo = drive_service.files().get_media(fileId=file_id).execute().decode('utf-8')
                    
                    contexto_documentos += f"\n\n=== DOCUMENTO: {file_name} ===\n"
                    contexto_documentos += contenido_archivo
            except Exception as e:
                st.error(f"Error al leer los documentos desde Drive: {e}")
                
        # 3. Preparar la instrucción (Prompt) para Gemini
        instruccion = f"""
        Eres un Ingeniero de Minas experto que labora en InkaDrill. 
        Responde a la consulta del usuario basándote ESTRICTAMENTE en la siguiente base de conocimientos:
        
        {contexto_documentos}
        
        Si la información necesaria para responder no se encuentra en los documentos provistos, indica amablemente: 
        "La información no se encuentra registrada en la base de datos documental actual de InkaDrill."
        
        Consulta: {pregunta}
        """
        
        # 4. Generar respuesta
        with st.chat_message("assistant"):
            with st.spinner("Procesando respuesta técnica..."):
                try:
                    respuesta_modelo = modelo.generate_content(instruccion)
                    st.markdown(respuesta_modelo.text)
                    st.session_state.mensajes_ia.append({"rol": "assistant", "contenido": respuesta_modelo.text})
                except Exception as e:
                    st.error(f"Error al generar la respuesta con IA: {e}")

# ====================================================================
# PESTAÑA 2: SUBIR DOCUMENTOS (Sube PDFs/TXT y los guarda en Drive)
# ====================================================================
elif pestaña == "📂 Alimentar Base de Datos":
    st.title("Alimentar Base de Datos Documental 🧠")
    st.markdown("Sube manuales, reportes geomecánicos o protocolos. El sistema extraerá el texto y lo guardará de forma permanente en tu carpeta de Google Drive.")
    
    archivo_subido = st.file_uploader("Selecciona un archivo PDF o TXT", type=["pdf", "txt"])
    
    if st.button("Subir y Guardar en Google Drive", use_container_width=True, type="primary"):
        if archivo_subido is not None:
            texto_extraido = ""
            
            with st.spinner("Procesando y extrayendo texto del documento..."):
                # Procesar archivo .txt
                if archivo_subido.name.endswith(".txt"):
                    texto_extraido = archivo_subido.read().decode("utf-8")
                
                # Procesar archivo .pdf
                elif archivo_subido.name.endswith(".pdf"):
                    lector_pdf = PyPDF2.PdfReader(archivo_subido)
                    for pagina in lector_pdf.pages:
                        texto_extraido += pagina.extract_text() + "\n"
                
                # Subir el texto directamente a la carpeta de Google Drive como archivo .txt
                metadata_archivo = {
                    'name': f"{archivo_subido.name}.txt",
                    'parents': [ID_CARPETA_MEMORIA]
                }
                
                # Convertimos el texto extraído a flujo de bytes para enviarlo a la API
                media_cuerpo = MediaIoBaseUpload(
                    BytesIO(texto_extraido.encode('utf-8')), 
                    mimetype='text/plain', 
                    chunksize=1024*1024, 
                    resumable=True
                )
                
                # Ejecutamos la subida en Drive
                drive_service.files().create(
                    body=metadata_archivo, 
                    media_body=media_cuerpo, 
                    fields='id'
                ).execute()
                    
            st.success(f"¡El archivo '{archivo_subido.name}' fue procesado, convertido a texto y guardado exitosamente en tu Google Drive!")
        else:
            st.warning("Por favor, carga un archivo antes de presionar el botón.")
            
    st.markdown("---")
    st.markdown("### 📂 Documentos mineros actualmente en la nube:")
    
    with st.spinner("Cargando lista de documentos..."):
        try:
            query_lista = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
            archivos_actuales = drive_service.files().list(q=query_lista, fields="files(name)").execute().get('files', [])
            
            if len(archivos_actuales) > 0:
                for arch in archivos_actuales:
                    st.markdown(f"📄 `{arch['name']}`")
            else:
                st.info("La carpeta en Google Drive se encuentra vacía.")
        except Exception as e:
            st.error("No se pudo conectar a Google Drive para listar los archivos. Verifica tus credenciales.")import streamlit as st
import os
import PyPDF2
from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload

# --- 1. CONFIGURACIÓN DE LA PÁGINA Y GOOGLE DRIVE ---
st.set_page_config(page_title="InkaDrill - Cerebro IA", page_icon="🧠", layout="wide")

# ►► PEGA AQUÍ EL ID DE TU CARPETA DE GOOGLE DRIVE ◄◄
ID_CARPETA_MEMORIA = "1L-6rI-3lu4m0PoXk8Y1brudQC9PrkGCn"

# Asumimos que drive_service ya está disponible por tu conexión principal.
# Si estás en un archivo separado, recuerda importar o inicializar tu service de Google Drive aquí.

# --- 2. BARRA LATERAL (MENÚ IZQUIERDO ESTILO ESTándar) ---
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

# ====================================================================
# PESTAÑA 1: CHATBOT (Lee los archivos .txt desde Google Drive)
# ====================================================================
if pestaña == "💬 Chat Asistente Operativo":
    st.title("Asistente Operativo InkaDrill ⛏️")
    st.markdown("Realiza consultas técnicas. La IA buscará las respuestas en los documentos almacenados en tu Google Drive corporativo.")
    
    # Historial de chat en sesión
    if "mensajes_ia" not in st.session_state:
        st.session_state.mensajes_ia = []

    # Mostrar mensajes anteriores
    for mensaje in st.session_state.mensajes_ia:
        with st.chat_message(mensaje["rol"]):
            st.markdown(mensaje["contenido"])

    # Caja de texto para preguntar
    pregunta = st.chat_input("Escribe tu consulta geomecánica, de sostenimiento o topográfica...")
    
    if pregunta:
        # 1. Mostrar pregunta en pantalla
        with st.chat_message("user"):
            st.markdown(pregunta)
        st.session_state.mensajes_ia.append({"rol": "user", "contenido": pregunta})
        
        # 2. Conectar a Google Drive y leer todos los archivos de la carpeta
        contexto_documentos = ""
        
        with st.spinner("Conectando a la base de datos documental en Google Drive..."):
            try:
                query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
                archivos_drive = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
                
                for archivo in archivos_drive:
                    file_id = archivo['id']
                    file_name = archivo['name']
                    # Descargamos el contenido del archivo de texto
                    contenido_archivo = drive_service.files().get_media(fileId=file_id).execute().decode('utf-8')
                    
                    contexto_documentos += f"\n\n=== DOCUMENTO: {file_name} ===\n"
                    contexto_documentos += contenido_archivo
            except Exception as e:
                st.error(f"Error al leer los documentos desde Drive: {e}")
                
        # 3. Preparar la instrucción (Prompt) para Gemini
        instruccion = f"""
        Eres un Ingeniero de Minas experto que labora en InkaDrill. 
        Responde a la consulta del usuario basándote ESTRICTAMENTE en la siguiente base de conocimientos:
        
        {contexto_documentos}
        
        Si la información necesaria para responder no se encuentra en los documentos provistos, indica amablemente: 
        "La información no se encuentra registrada en la base de datos documental actual de InkaDrill."
        
        Consulta: {pregunta}
        """
        
        # 4. Generar respuesta
        with st.chat_message("assistant"):
            with st.spinner("Procesando respuesta técnica..."):
                try:
                    respuesta_modelo = modelo.generate_content(instruccion)
                    st.markdown(respuesta_modelo.text)
                    st.session_state.mensajes_ia.append({"rol": "assistant", "contenido": respuesta_modelo.text})
                except Exception as e:
                    st.error(f"Error al generar la respuesta con IA: {e}")

# ====================================================================
# PESTAÑA 2: SUBIR DOCUMENTOS (Sube PDFs/TXT y los guarda en Drive)
# ====================================================================
elif pestaña == "📂 Alimentar Base de Datos":
    st.title("Alimentar Base de Datos Documental 🧠")
    st.markdown("Sube manuales, reportes geomecánicos o protocolos. El sistema extraerá el texto y lo guardará de forma permanente en tu carpeta de Google Drive.")
    
    archivo_subido = st.file_uploader("Selecciona un archivo PDF o TXT", type=["pdf", "txt"])
    
    if st.button("Subir y Guardar en Google Drive", use_container_width=True, type="primary"):
        if archivo_subido is not None:
            texto_extraido = ""
            
            with st.spinner("Procesando y extrayendo texto del documento..."):
                # Procesar archivo .txt
                if archivo_subido.name.endswith(".txt"):
                    texto_extraido = archivo_subido.read().decode("utf-8")
                
                # Procesar archivo .pdf
                elif archivo_subido.name.endswith(".pdf"):
                    lector_pdf = PyPDF2.PdfReader(archivo_subido)
                    for pagina in lector_pdf.pages:
                        texto_extraido += pagina.extract_text() + "\n"
                
                # Subir el texto directamente a la carpeta de Google Drive como archivo .txt
                metadata_archivo = {
                    'name': f"{archivo_subido.name}.txt",
                    'parents': [ID_CARPETA_MEMORIA]
                }
                
                # Convertimos el texto extraído a flujo de bytes para enviarlo a la API
                media_cuerpo = MediaIoBaseUpload(
                    BytesIO(texto_extraido.encode('utf-8')), 
                    mimetype='text/plain', 
                    chunksize=1024*1024, 
                    resumable=True
                )
                
                # Ejecutamos la subida en Drive
                drive_service.files().create(
                    body=metadata_archivo, 
                    media_body=media_cuerpo, 
                    fields='id'
                ).execute()
                    
            st.success(f"¡El archivo '{archivo_subido.name}' fue procesado, convertido a texto y guardado exitosamente en tu Google Drive!")
        else:
            st.warning("Por favor, carga un archivo antes de presionar el botón.")
            
    st.markdown("---")
    st.markdown("### 📂 Documentos mineros actualmente en la nube:")
    
    with st.spinner("Cargando lista de documentos..."):
        try:
            query_lista = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
            archivos_actuales = drive_service.files().list(q=query_lista, fields="files(name)").execute().get('files', [])
            
            if len(archivos_actuales) > 0:
                for arch in archivos_actuales:
                    st.markdown(f"📄 `{arch['name']}`")
            else:
                st.info("La carpeta en Google Drive se encuentra vacía.")
        except Exception as e:
            st.error("No se pudo conectar a Google Drive para listar los archivos. Verifica tus credenciales.")
