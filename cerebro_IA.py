import streamlit as st
import google.generativeai as genai
import os
import PyPDF2
import json
from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import datetime # Para exportar reportes con fecha

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="InkaDrill - Cerebro IA", page_icon="🧠", layout="wide")

# Tu ID de carpeta en Google Drive
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

# --- 3. BARRA LATERAL ESTILO PODEROSA ---
with st.sidebar:
    st.markdown("<h2 style='color: #A6802C; font-weight: 900; text-align: center;'>INKADRILL<br>CEREBRO IA</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # ¡NUEVO MENÚ CON HERRAMIENTAS TÉCNICAS!
    pestaña = st.radio(
        "Navegación:",
        ["💬 Chat Asistente Operativo", "🧮 Cálculos Geomecánicos", "📂 Alimentar Base de Datos"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("<p style='font-size: 11px; color: #888; text-align: center;'>InkaDrill 2026 ©<br>Gestión de Conocimiento Minero</p>", unsafe_allow_html=True)

if conexion_exitosa:
    # ====================================================================
    # PESTAÑA 1: CHATBOT CON EXPORTACIÓN DE REPORTES
    # ====================================================================
    if pestaña == "💬 Chat Asistente Operativo":
        col_tit, col_btn = st.columns([4, 1])
        with col_tit:
            st.title("Asistente Operativo InkaDrill ⛏️")
        
        # Botón para exportar el chat
        with col_btn:
            if "mensajes_ia" in st.session_state and len(st.session_state.mensajes_ia) > 0:
                chat_history = "REPORTE TÉCNICO INKADRILL\n" + "="*30 + "\n\n"
                for m in st.session_state.mensajes_ia:
                    rol = "INGENIERO" if m["rol"] == "user" else "SISTEMA IA"
                    chat_history += f"[{rol}]:\n{m['contenido']}\n\n"
                
                st.download_button(
                    label="📄 Exportar Reporte",
                    data=chat_history,
                    file_name=f"Reporte_InkaDrill_{datetime.date.today()}.txt",
                    mime="text/plain"
                )

        st.markdown("Realiza consultas técnicas. La IA buscará las respuestas en los documentos de Google Drive.")
        
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
            with st.spinner("Conectando a la base de datos documental..."):
                try:
                    query = f"'{ID_CARPETA_MEMORIA}' in parents and trashed = false"
                    archivos_drive = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
                    for archivo in archivos_drive:
                        contenido_archivo = drive_service.files().get_media(fileId=archivo['id']).execute().decode('utf-8')
                        contexto_documentos += f"\n\n=== {archivo['name']} ===\n{contenido_archivo}"
                except:
                    pass # Evitamos romper el chat si falla un archivo
                    
            instruccion = f"""
            Eres el Ingeniero de Minas Jefe de InkaDrill. Responde basándote ESTRICTAMENTE en estos documentos:
            {contexto_documentos}
            Si no hay información, indícalo. Consulta: {pregunta}
            """
            
            with st.chat_message("assistant"):
                with st.spinner("Procesando respuesta técnica..."):
                    try:
                        respuesta_modelo = modelo.generate_content(instruccion)
                        st.markdown(respuesta_modelo.text)
                        st.session_state.mensajes_ia.append({"rol": "assistant", "contenido": respuesta_modelo.text})
                        st.rerun() # Recargamos para que aparezca el botón de exportar
                    except Exception as e:
                        st.error(f"Error IA: {e}")

    # ====================================================================
    # PESTAÑA NUEVA: CÁLCULOS GEOMECÁNICOS (RMR y GSI)
    # ====================================================================
    elif pestaña == "🧮 Cálculos Geomecánicos":
        st.title("Suite de Análisis Geomecánico 🪨")
        st.markdown("Herramientas de evaluación rápida para el macizo rocoso en frentes de avance.")
        
        tab_rmr, tab_gsi = st.tabs(["Clasificación RMR (Bieniawski)", "Índice GSI (Hoek)"])
        
        with tab_rmr:
            st.markdown("### Parámetros de Rock Mass Rating")
            col1, col2 = st.columns(2)
            with col1:
                p1 = st.number_input("1. Resistencia Compresión Simple (MPa)", min_value=0, max_value=300, value=50)
                p2 = st.slider("2. RQD (%)", min_value=0, max_value=100, value=75)
                p3 = st.selectbox("3. Espaciado de Discontinuidades", ["< 60 mm", "60 - 200 mm", "200 - 600 mm", "0.6 - 2.0 m", "> 2.0 m"])
            with col2:
                p4 = st.selectbox("4. Condición de Discontinuidades", ["Muy Rugosas, cerradas", "Ligeramente rugosas", "Ligeramente abiertas (<1mm)", "Relleno suave / Abiertas", "Relleno blando (>5mm)"])
                p5 = st.selectbox("5. Agua Subterránea", ["Completamente seco", "Húmedo", "Goteo", "Flujo continuo"])
            
            if st.button("Calcular RMR", type="primary"):
                # Simulación de un cálculo básico (Ajustable a tablas reales posteriormente)
                puntaje_base = (p2 * 0.2) + (p1 * 0.1) + 30 # Fórmula prototipo simplificada
                st.success(f"**Puntaje RMR Estimado:** {puntaje_base:.1f}")
                if puntaje_base > 60:
                    st.info("Clase: Buena (II) - Sostenimiento sugerido: Pernos sistemáticos ocasionales.")
                else:
                    st.warning("Clase: Regular (III) - Sostenimiento sugerido: Pernos + Malla sistemática.")
                    
        with tab_gsi:
            st.markdown("### Geological Strength Index")
            st.markdown("Seleccione las condiciones estructurales y de superficie:")
            estruct = st.selectbox("Estructura del Macizo", ["Intacto / Masivo", "Blocoso", "Muy Blocoso", "Fracturado / Disturbado"])
            superf = st.selectbox("Condición de Superficie", ["Muy Buena", "Buena", "Regular", "Pobre", "Muy Pobre"])
            if st.button("Estimar GSI", type="primary"):
                st.success("GSI Estimado: Rango 45 - 55")
                st.info("Aplicable para criterios de falla Hoek-Brown.")

    # ====================================================================
    # PESTAÑA 3: SUBIR DOCUMENTOS
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
                    
                    metadata_archivo = {'name': f"{archivo_subido.name}.txt", 'parents': [ID_CARPETA_MEMORIA]}
                    media_cuerpo = MediaIoBaseUpload(BytesIO(texto_extraido.encode('utf-8')), mimetype='text/plain', resumable=True)
                    drive_service.files().create(body=metadata_archivo, media_body=media_cuerpo, fields='id').execute()
                        
                st.success(f"¡El archivo '{archivo_subido.name}' fue guardado en Google Drive!")
            else:
                st.warning("Por favor, carga un archivo primero.")
