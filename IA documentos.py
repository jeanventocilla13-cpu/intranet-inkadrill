import streamlit as st
import google.generativeai as genai
import os
import PyPDF2

# --- 1. CONFIGURACIÓN DE PÁGINA Y CARPETA DE MEMORIA ---
st.set_page_config(page_title="InkaDrill IA", page_icon="🧠", layout="wide")

# Creamos una carpeta virtual para guardar los documentos que subas
CARPETA_MEMORIA = "memoria_ia"
if not os.path.exists(CARPETA_MEMORIA):
    os.makedirs(CARPETA_MEMORIA)

# --- 2. CONFIGURACIÓN DE GEMINI ---
# Asegúrate de tener tu API KEY en los Secrets de Streamlit
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    modelo = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.warning("⚠️ No se encontró la API Key de Gemini en los Secrets.")

# --- 3. BARRA LATERAL (MENÚ IZQUIERDO) ---
with st.sidebar:
    st.markdown("<h2 style='color: #d4a017; font-weight: 900; text-align: center;'>INKADRILL<br>CEREBRO IA</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Menú de navegación estilo botones
    pestaña = st.radio(
        "Navegación:",
        ["💬 Chat Asistente", "📂 Subir Documentos"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("<p style='font-size: 11px; color: #888; text-align: center;'>InkaDrill 2026 ©<br>Sistema de Memoria Operativa</p>", unsafe_allow_html=True)

# ====================================================================
# PESTAÑA 1: CHATBOT (Lee la memoria)
# ====================================================================
if pestaña == "💬 Chat Asistente":
    st.title("Asistente Operativo InkaDrill ⛏️")
    st.markdown("Pregunta cualquier cosa. La IA buscará las respuestas en los documentos que has subido.")
    
    # Historial de chat
    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []

    # Mostrar mensajes anteriores
    for mensaje in st.session_state.mensajes:
        with st.chat_message(mensaje["rol"]):
            st.markdown(mensaje["contenido"])

    # Caja de texto para preguntar
    pregunta = st.chat_input("Escribe tu consulta sobre los documentos...")
    
    if pregunta:
        # 1. Mostrar pregunta del usuario
        with st.chat_message("user"):
            st.markdown(pregunta)
        st.session_state.mensajes.append({"rol": "user", "contenido": pregunta})
        
        # 2. Leer TODA la memoria (todos los txt en la carpeta)
        contexto_global = ""
        archivos_guardados = os.listdir(CARPETA_MEMORIA)
        
        for archivo in archivos_guardados:
            with open(os.path.join(CARPETA_MEMORIA, archivo), "r", encoding="utf-8") as f:
                contexto_global += f"\n--- ARCHIVO: {archivo} ---\n"
                contexto_global += f.read() + "\n"
                
        # 3. Preparar la instrucción para la IA
        instruccion = f"""
        Eres el Ingeniero Jefe de InkaDrill. Tu base de conocimientos son estos documentos operativos:
        {contexto_global}
        
        Si la información no está en los documentos, di que no tienes datos suficientes en la base de datos actual.
        PREGUNTA DEL USUARIO: {pregunta}
        """
        
        # 4. Generar respuesta
        with st.chat_message("assistant"):
            with st.spinner("Revisando la base de datos documental..."):
                try:
                    respuesta = modelo.generate_content(instruccion)
                    st.markdown(respuesta.text)
                    st.session_state.mensajes.append({"rol": "assistant", "contenido": respuesta.text})
                except Exception as e:
                    st.error(f"Hubo un error con la IA: {e}")

# ====================================================================
# PESTAÑA 2: SUBIR DOCUMENTOS (Alimentar la memoria)
# ====================================================================
elif pestaña == "📂 Subir Documentos":
    st.title("Alimentar el Cerebro Digital 🧠")
    st.markdown("Sube manuales, reportes geomecánicos o protocolos. La IA los leerá y los guardará en su memoria para futuras consultas.")
    
    archivo_subido = st.file_uploader("Sube un archivo PDF o TXT", type=["pdf", "txt"])
    
    if st.button("Guardar en Memoria", use_container_width=True, type="primary"):
        if archivo_subido is not None:
            texto_extraido = ""
            
            with st.spinner("Procesando documento..."):
                # Si es TXT
                if archivo_subido.name.endswith(".txt"):
                    texto_extraido = archivo_subido.read().decode("utf-8")
                
                # Si es PDF
                elif archivo_subido.name.endswith(".pdf"):
                    lector_pdf = PyPDF2.PdfReader(archivo_subido)
                    for pagina in lector_pdf.pages:
                        texto_extraido += pagina.extract_text() + "\n"
                
                # Guardar el texto extraído como un archivo local en la carpeta de memoria
                ruta_guardado = os.path.join(CARPETA_MEMORIA, f"{archivo_subido.name}.txt")
                with open(ruta_guardado, "w", encoding="utf-8") as f:
                    f.write(texto_extraido)
                    
            st.success(f"¡Documento '{archivo_subido.name}' procesado y guardado en la memoria de la IA exitosamente!")
        else:
            st.warning("Por favor, selecciona un archivo primero.")
            
    st.markdown("---")
    st.markdown("### Documentos actualmente en la memoria:")
    archivos_actuales = os.listdir(CARPETA_MEMORIA)
    if len(archivos_actuales) > 0:
        for arch in archivos_actuales:
            st.markdown(f"📄 `{arch}`")
    else:
        st.info("La memoria está vacía. Sube tu primer documento.")
