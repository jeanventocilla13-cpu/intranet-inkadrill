import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io  # <- Nueva librería para procesar el Excel en memoria
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
# --- 1. SISTEMA DE SEGURIDAD (CONTRASEÑA) ---
st.set_page_config(page_title="InkaDrill Intranet", page_icon="⛏️", layout="wide")

# --- INICIALIZAR VARIABLES DE SEGURIDAD ---
if "acceso_concedido" not in st.session_state:
    st.session_state["acceso_concedido"] = False

if "pestaña_actual" not in st.session_state:
    st.session_state["pestaña_actual"] = "Inicio"

# --- 1. SISTEMA DE SEGURIDAD Y LOGIN (ESTILO PODEROSA) ---
if not st.session_state["acceso_concedido"]:
    
    # 1.1 CSS Antibalas para destruir las capas blancas de Streamlit
    st.markdown("""
    <style>
        /* FORZAR LA IMAGEN DE FONDO EN LA CAPA MÁS PROFUNDA */
        .stApp {
            background: url("https://images.unsplash.com/photo-1578593173274-cf47d3e69123?auto=format&fit=crop&w=1920&q=80") no-repeat center center fixed !important;
            background-size: cover !important;
        }
        
        /* VOLVER INVISIBLES TODAS LAS CAPAS BLANCAS SUPERPUESTAS */
        [data-testid="stAppViewContainer"], 
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
        }
        
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* EL PANEL DE VIDRIO (Ahora sí se verá el desenfoque) */
        [data-testid="stForm"] {
            background-color: rgba(40, 40, 40, 0.6) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 15px !important;
            padding: 40px !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8) !important;
            max-width: 400px !important;
            margin: 10vh auto auto auto !important;
        }

        /* ETIQUETAS AMARILLAS */
        [data-testid="stForm"] label p { color: #F1C40F !important; font-weight: bold !important; font-size: 12px !important; }

        /* ARREGLO DE LAS CAJAS DE TEXTO Y EL "OJITO" BLANCO */
        div[data-baseweb="input"] {
            background-color: #222222 !important;
            border: 1px solid #555 !important;
            border-radius: 5px !important;
        }
        div[data-baseweb="input"] input {
            color: white !important;
            background-color: transparent !important;
            -webkit-text-fill-color: white !important;
        }
        /* Pintar el ícono del ojito de gris oscuro */
        div[data-baseweb="input"] svg { fill: #888 !important; }
        div[data-baseweb="input"]:focus-within { border-color: #F1C40F !important; }

        /* ESTILO DEL BOTÓN VERDE */
        [data-testid="stFormSubmitButton"] button {
            background-color: #3b7b63 !important;
            color: white !important;
            border: none !important;
            font-weight: bold !important;
            border-radius: 5px !important;
            padding: 10px !important;
        }
        [data-testid="stFormSubmitButton"] button:hover {
            background-color: #2c5c4a !important;
            color: #F1C40F !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # 1.2 Creamos el formulario visual interactivo
    with st.form("login_form"):
        st.markdown("<h1 style='text-align: center; color: #F1C40F; margin-bottom: 0; font-weight: 900;'>INKADRILL</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #ccc; font-size: 11px; margin-bottom: 35px; letter-spacing: 1px;'>VERSION 2.1.0</p>", unsafe_allow_html=True)
        
        usuario = st.text_input("TIPO DE AUTENTICACIÓN (USUARIO)")
        contrasena = st.text_input("CONTRASEÑA", type="password")
        
        # EL BOTÓN CON ANCHO COMPLETO NATIVO
        submit_btn = st.form_submit_button("INICIAR SESIÓN", use_container_width=True)
        
        st.markdown("<p style='text-align: center; color: #888; font-size: 10px; margin-top: 30px;'>INKADRILL 2026 © - Todos los derechos reservados</p>", unsafe_allow_html=True)
        
        # 1.3 Lógica de validación
        if submit_btn:
            if usuario == "CMPMINA" and contrasena == "1234":
                st.session_state["acceso_concedido"] = True
                st.rerun() 
            else:
                st.error("Credenciales incorrectas. Acceso denegado.")
    
    # 1.4 DETENER LA EJECUCIÓN
    st.stop()

# --- 2. CONFIGURACIÓN DE LA INTELIGENCIA ARTIFICIAL Y SECRETOS ---
# (A partir de aquí hacia abajo va TODO tu código original intacto)
# --- 1. CONFIGURACIÓN ---
#st.set_page_config(page_title="InkaDrill Intranet", page_icon="⛏️", layout="wide")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
modelo = genai.GenerativeModel('gemini-2.5-flash')
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Reemplaza con tus 3 IDs reales de Drive

DOC_WORD_1_ID = '1zaJVdGMqmKAf-GTQx6oY8fkCTOX_Lvaj3uwB1RDwOso'
DOC_WORD_2_ID = '1INIfPGcq7gS5uYgw_Qd_R3Emz2D8TEz34teJ3ysECGs'
EXCEL_DATOS_ID = '18qcBENgyhsEh340d-AINcKfh4sArAWz-OBchn5HCFZY'
# Truco maestro: Crear el token de Drive temporalmente en la nube usando el secreto
if "GOOGLE_TOKEN" in st.secrets:
    with open('token.json', 'w') as f:
        f.write(st.secrets["GOOGLE_TOKEN"])

# --- 2. CSS PARA EL DISEÑO CORPORATIVO ---
estilo_dashboard = """
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #e9ecef; }
    .top-nav {
        background-color: white; padding: 15px 30px; display: flex; align-items: center;
        justify-content: space-between; border-bottom: 2px solid #105c24;
        margin-top: -60px; margin-left: -4rem; margin-right: -4rem; margin-bottom: 20px;
    }
    .logo-text { color: #105c24; font-size: 24px; font-weight: 900; }
    .nav-links span { margin: 0 15px; color: #333; font-weight: bold; cursor: pointer; }
    .nav-links span.active { color: white; background-color: #105c24; padding: 10px 15px; border-radius: 5px; }
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
</style>
"""
st.markdown(estilo_dashboard, unsafe_allow_html=True)

# --- 3. BARRA SUPERIOR ESTILO INKADRILL PREMIUM ---
    
# 1. Inyectamos los colores corporativos a los botones
st.markdown("""
    <style>
        /* 1. Fondo general de la app */
        .stApp { background-color: #E8ECEF !important; }
        
        /* 2. Transformar botones en PESTAÑAS CUADRADAS EXACTAS */
        div.stButton > button {
            height: 65px !important;
            border-radius: 0px !important; /* Esquinas totalmente cuadradas */
            font-size: 16px !important;
            font-weight: 600 !important;
            margin: 0 !important;
            box-shadow: none !important;
            border: none !important;
            background-color: transparent !important;
            color: #555 !important;
        }

        /* 3. El Botón ACTIVO (El verde corporativo) */
        div.stButton > button[kind="primary"] {
            background-color: #0F3F23 !important; /* Verde oscuro InkaDrill */
            color: white !important;
            border-bottom: 6px solid #f1c40f !important; /* Línea dorada gruesa */
        }
        
        div.stButton > button[kind="secondary"]:hover {
            color: #0F3F23 !important;
            background-color: #e0e0e0 !important;
        }
        
        /* 4. La Franja Verde del Buscador (Tu IA) */
        div[data-testid="stForm"] {
            background-color: #0F3F23 !important;
            padding: 30px !important;
            border-radius: 8px !important;
            border: none !important;
        }
        /* Limpiar input y botón del buscador */
        div[data-testid="stForm"] input { border-radius: 5px !important; font-size: 16px !important; }
        div[data-testid="stForm"] button { background-color: #1b5e20 !important; color: white !important; border: 1px solid white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. Creamos las columnas
col_logo, col_nav1, col_nav2, col_nav3, col_espacio, col_perfil = st.columns([2.5, 1.2, 1.3, 1.2, 2, 2.5])

with col_logo:
    st.markdown("<div style='display: flex; align-items: center;'><img src='https://cdn-icons-png.flaticon.com/512/2950/2950711.png' width='40' style='margin-right: 10px;'><div style='line-height: 1.1;'><strong style='color:#0F3F23; font-size:18px; letter-spacing: 1px;'>INKADRILL</strong><br><span style='color:gray; font-size:11px; letter-spacing: 1px;'>INTRANET</span></div></div>", unsafe_allow_html=True)

with col_nav1:
    btn_tipo = "primary" if st.session_state["pestaña_actual"] == "Inicio" else "secondary"
    if st.button("🏠 Inicio", type=btn_tipo, use_container_width=True, key="btn_inicio_premium"):
        st.session_state["pestaña_actual"] = "Inicio"
        st.rerun()

with col_nav2:
    btn_tipo = "primary" if st.session_state["pestaña_actual"] == "Topografía" else "secondary"
    if st.button("📍 Topografía", type=btn_tipo, use_container_width=True, key="btn_topo_premium"):
        st.session_state["pestaña_actual"] = "Topografía"
        st.rerun()

with col_nav3:
    btn_tipo = "primary" if st.session_state["pestaña_actual"] == "Datos" else "secondary"
    if st.button("🗄️ Datos", type=btn_tipo, use_container_width=True, key="btn_datos_premium"):
        st.session_state["pestaña_actual"] = "Datos"
        st.rerun()

with col_perfil:
    st.markdown("<div style='display: flex; align-items: center; justify-content: flex-end;'><div style='text-align: right; line-height: 1.2; margin-right: 12px;'><strong style='color:#333; font-size:14px;'>Perfil</strong><br><span style='color:gray; font-size:13px;'>Jean Ventocilla</span></div><img src='https://cdn-icons-png.flaticon.com/512/3135/3135715.png' width='42' style='border-radius: 50%; border: 2px solid #ddd;'></div>", unsafe_allow_html=True)
    
st.markdown("---")

# --- 4. FUNCIÓN PARA DESCARGAR DATOS DE DRIVE ---
@st.cache_data(ttl=300)
def cargar_datos_excel():
    try:
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        service = build('drive', 'v3', credentials=creds)
        
        # Descargamos el archivo como un verdadero Excel (.xlsx)
        respuesta = service.files().export_media(fileId=EXCEL_DATOS_ID, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet').execute()
        
        # Abrimos el Excel en la memoria de Python
        archivo_excel = io.BytesIO(respuesta)
        
        # Extraemos la Hoja 1 (Datos de Coordenadas)
        df_hoja1 = pd.read_excel(archivo_excel, sheet_name=0)
        
        # Extraemos la Hoja 2 (Datos Geomecánicos) y le damos formato
        df_hoja2 = pd.read_excel(archivo_excel, sheet_name='Hoja 2', header=None)
        df_hoja2.columns = ['Parámetro', 'Valor / Rango', 'Clasificación']
        
        return df_hoja1, df_hoja2, service
        
    except Exception as e:
        st.error(f"Error técnico exacto: {e}")
        return None, None, None

# Cargamos las bases de datos maestras (Ambas hojas a la vez)
datos_reales, datos_geomecanicos, drive_service = cargar_datos_excel()

if st.session_state["pestaña_actual"] == "Inicio":
        
        # ==========================================================
        # EL BUSCADOR DE IA AHORA VA PRIMERO (Al inicio de la página)
        # ==========================================================
        # --- 5. BUSCADOR INTELIGENTE CON IA ---
        col_busq1, col_busq2, col_busq3 = st.columns([1, 4, 1])
        
        with col_busq2:
            # Envolvemos el formulario en un container para estilizar el fondo verde
            st.markdown('<div class="franja-verde-buscador">', unsafe_allow_html=True)
            
            # Formulario de IA con estilo corporativo
            with st.form(key='formulario_ia_premium', clear_on_submit=False):
                col_in1, col_in2 = st.columns([4, 1])
                
                with col_in1:
                    pregunta_usuario = st.text_input(
                        label="Buscar en la intranet",
                        placeholder="🔍 Buscar en la intranet: topografía, datos mineros, informes, perforaciones...",
                        label_visibility="collapsed"
                    )
                with col_in2:
                    boton_buscar = st.form_submit_button("Buscar", use_container_width=True)
                    
            st.markdown('</div>', unsafe_allow_html=True)

            if boton_buscar and pregunta_usuario:
                with st.spinner("Analizando documentos operativos..."):
                    if drive_service:
                        try:
                            # Descargamos ambos documentos
                            doc1 = drive_service.files().export_media(fileId=DOC_WORD_1_ID, mimeType='text/plain').execute().decode('utf-8')
                            doc2 = drive_service.files().export_media(fileId=DOC_WORD_2_ID, mimeType='text/plain').execute().decode('utf-8')
                            
                            # Preparamos las instrucciones para Gemini
                            instruccion = f"""
                            Eres un ingeniero de minas experto. Responde a la pregunta del usuario basándote UNICAMENTE
                            en la información de los siguientes dos documentos operativos de la empresa.
                            Sé preciso, profesional y directo.

                            DOCUMENTO 1 (Procedimientos y Seguridad):
                            {doc1}

                            DOCUMENTO 2 (Contexto Geomecánico):
                            {doc2}

                            PREGUNTA DEL USUARIO: {pregunta_usuario}
                            """
                            
                            # Generamos la respuesta
                            respuesta_ia = modelo.generate_content(instruccion)
                            st.success("Respuesta generada según los datos de la empresa:")
                            st.info(respuesta_ia.text)
                            
                        except Exception as e:
                            st.error(f"Error al leer los documentos de texto: {e}")
                    else:
                        st.error("No se pudo conectar a Google Drive.")
        
        # Un espacio elegante entre bloques
       # Un separador ajustado sin espacios gigantes
        st.markdown("<hr style='margin: 15px 0px; border-color: #ddd;'>", unsafe_allow_html=True)
    
    # ==========================================================
    # LA HISTORIA DE INKADRILL AHORA VA DESPUÉS (Abajo del buscador)
    # ==========================================================
    # --- SECCIÓN DE HISTORIA INKADRILL (Tarjetón gris) ---
        st.markdown("""
<style>
.historia-container { background-color: #E8E8E8; padding: 50px; border-radius: 15px; border: 1px solid #ccc; box-shadow: 0 4px 8px rgba(0,0,0,0.05); }
.historia-title { color: #0F3F23; font-weight: 800; font-size: 22px; margin-top: 0; margin-bottom: 15px; text-transform: uppercase; border-left: 4px solid #f1c40f; padding-left: 10px; }
.historia-text { color: #333; font-size: 16px; line-height: 1.6; }
.historia-img { width: 100%; border-radius: 10px; border: 1px solid #bbb; box-shadow: 0 4px 6px rgba(0,0,0,0.1); object-fit: cover; height: 280px; }
.row-spacing { margin-bottom: 20px; }
.divisor { border-color: #d0d0d0; margin: 40px 0; border-width: 1px; }
</style>

<div class="historia-container">
<div style="display: flex; gap: 40px; align-items: center;" class="row-spacing">
<div style="flex: 1.5;" class="historia-text">
<h2 class="historia-title">El Origen: De la Teoría a la Transformación Digital</h2>
<p>La historia de <strong>InkaDrill Corporation</strong> no nació en un laboratorio de Silicon Valley, sino en el corazón de la ingeniería peruana, gestándose entre las aulas de Ate durante las intensas jornadas de análisis para el proyecto <em>Túneles y movimiento de tierra</em>.</p>
<p>El problema fundacional se hizo evidente al contrastar la teoría académica con la cruda realidad operativa de las minas subterráneas, como las que se observan en operaciones del nivel de Minera Condestable. En el ciclo de minado tradicional, después de cada voladura, existía un punto ciego y crítico: la <strong>evaluación geomecánica</strong>.</p>
<p>La frustración era palpable. Quienes conocen de cerca la gestión logística y la operación de maquinaria pesada de gran tonelaje saben que los equipos no pueden detenerse. Tener un frente paralizado, con flotas enteras esperando durante horas mientras se realizaba un mapeo estructural manual con brújula y wincha, no solo representaba una pérdida masiva de OPEX por sobreexcavación (overbreak), sino que exponía innecesariamente vidas humanas bajo roca inestable. La industria necesitaba urgencia, pero la consultoría tradicional respondía con lentitud.</p>
</div>
<div style="flex: 1;"><img src="https://images.unsplash.com/photo-1578593173274-cf47d3e69123?auto=format&fit=crop&w=600&q=80" class="historia-img"></div>
</div>

<hr class="divisor">

<div style="display: flex; gap: 40px; align-items: center; flex-direction: row-reverse;" class="row-spacing">
<div style="flex: 1.5;" class="historia-text">
<h2 class="historia-title">La Convergencia de Dos Mundos</h2>
<p>La solución no provino de hacer lo mismo más rápido, sino de cambiar las reglas del juego. La chispa que originó InkaDrill surgió de la intersección entre la geomecánica pura y la pasión por la automatización digital.</p>
<p>Si era posible estructurar lógicas de programación en lenguajes como <strong>Python</strong> y desarrollar scripts para crear asistentes virtuales basados en inteligencia artificial, esa misma arquitectura digital podía aplicarse para resolver el dolor más grande de la minería subterránea.</p>
<p>La idea evolucionó rápidamente: en lugar de depender exclusivamente del ojo humano y herramientas analógicas, se utilizaría tecnología láser LiDAR para capturar el entorno y algoritmos de procesamiento para interpretar los datos.</p>
</div>
<div style="flex: 1;"><img src="https://images.unsplash.com/photo-1555949963-ff9fe0c870eb?auto=format&fit=crop&w=600&q=80" class="historia-img"></div>
</div>

<hr class="divisor">

<div style="display: flex; gap: 40px; align-items: center;" class="row-spacing">
<div style="flex: 1.5;" class="historia-text">
<h2 class="historia-title">El Nacimiento del Sistema SST-3D</h2>
<p>El concepto maduró y tomó forma corporativa. Así nació <strong>InkaDrill Corporation S.A.C.</strong>, bajo la premisa de convertirse en un contratista Tier 2 especializado en predictibilidad estructural.</p>
<p>El equipo fundador desarrolló el servicio <strong>SST-3D (Smart Support Technology 3D)</strong>, diseñado para ingresar al frente inmediatamente después de la ventilación y el desatado de rocas. En solo tres minutos, el escáner capturaría una nube de puntos milimétrica, mientras el software procesaría el espaciado y la volumetría para integrarse con la evaluación táctil del ingeniero.</p>
<p>El resultado: el cálculo instantáneo del RQD, RMR y GSI, y la emisión de una cartilla de sostenimiento digital directamente a la tablet del operador del Jumbo.</p>
</div>
<div style="flex: 1;"><img src="https://images.unsplash.com/photo-1620325867502-221ddb5b48bc?auto=format&fit=crop&w=600&q=80" class="historia-img"></div>
</div>

<hr class="divisor">

<div style="display: flex; gap: 40px; align-items: center; flex-direction: row-reverse; margin-bottom: 0;">
<div style="flex: 1.5;" class="historia-text">
<h2 class="historia-title">Nuestra Misión Hoy</h2>
<p>Hoy, InkaDrill Corporation representa la evolución del ingeniero de minas peruano: profesionales con botas en el barro, pero con la mente en la nube.</p>
<p>Bajo el lema <em>"Ingeniería inteligente para túneles seguros"</em>, la empresa no solo busca optimizar el consumo de shotcrete o maximizar las horas-máquina, sino transformar la geomecánica en una herramienta predictiva en tiempo real.</p>
<p>InkaDrill nació para garantizar que cada avance subterráneo sea seguro, eficiente y esté respaldado por la precisión irrefutable de la tecnología digital.</p>
</div>
<div style="flex: 1;"><img src="https://images.unsplash.com/photo-1581092160562-40aa08e78837?auto=format&fit=crop&w=600&q=80" class="historia-img"></div>
</div>
</div>
""", unsafe_allow_html=True)
elif st.session_state["pestaña_actual"] == "Topografía":
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: #2c3e50; font-family: sans-serif; font-weight: 800; font-size: 22px;'>PANEL DE DATOS EN TIEMPO REAL (Desde Google Sheets)</h2>", unsafe_allow_html=True)
    

# --- 6. GRÁFICOS Y TABLAS ALIMENTADOS POR EL EXCEL ---
    if datos_reales is not None:
        # Fila 1
        fila1_col1, fila1_col2 = st.columns(2)
    
        with fila1_col1:
            with st.container(border=True):
                st.subheader("Resumen Topográfico")
                m1, m2 = st.columns(2)
                # Contamos cuántas filas (puntos) hay en el Excel
                m1.metric("Puntos Capturados (Total)", f"{len(datos_reales)}")
                m2.metric("Estado de Conexión", "Online (Drive)")
    
        with fila1_col2:
            with st.container(border=True):
                st.subheader("Avance Topográfico")
                # Graficamos directamente desde las columnas 'Día' y 'Metros' del Excel
                if 'Día' in datos_reales.columns and 'Metros' in datos_reales.columns:
                    fig_barras = px.bar(datos_reales, x="Día", y="Metros", color_discrete_sequence=['#105c24'])
                    fig_barras.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200)
                    st.plotly_chart(fig_barras, use_container_width=True)
                else:
                    st.warning("El Excel no tiene las columnas 'Día' y 'Metros'.")
    
        # Fila 2
        fila2_col1, fila2_col2 = st.columns(2)
    
        with fila2_col1:
            with st.container(border=True):
                st.subheader("Datos Crudos de Perforación")
                # Mostramos toda la tabla del Excel
                st.dataframe(datos_reales, hide_index=True, use_container_width=True)
    
        with fila2_col2:
            with st.container(border=True):
                st.subheader("Distribución de Coordenadas (UTM)")
                # Mapeamos los puntos usando las coordenadas del Excel
                if 'Coordenada E' in datos_reales.columns and 'Coordenada N' in datos_reales.columns:
                    fig_dispersion = px.scatter(datos_reales, x="Coordenada E", y="Coordenada N", color_discrete_sequence=['#e67e22'])
                    fig_dispersion.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=220)
                    st.plotly_chart(fig_dispersion, use_container_width=True)
                else:
                    st.warning("El Excel no tiene las columnas 'Coordenada E' y 'Coordenada N'.")
                    
                # --- Fila 3: Datos Geomecánicos ---
        st.markdown("---") # Esto dibuja una línea horizontal elegante para separar
        
        with st.container(border=True):
            st.subheader("⛏️ Parámetros Geomecánicos del Macizo Rocoso")
            # Mostramos la tabla de la Hoja 2
            st.dataframe(datos_geomecanicos, hide_index=True, use_container_width=True)
    else:
        st.error("No se pudo cargar la base de datos de Google Sheets. Verifica el ID.")
# ==========================================
# PÁGINA 3: DATOS (Tablas de Excel)
# ==========================================
elif st.session_state["pestaña_actual"] == "Datos":
    
    st.markdown("### BASE DE DATOS GENERAL")
    
    st.subheader("Datos Topográficos Reales")
    st.dataframe(datos_reales, use_container_width=True)
    
    st.subheader("Datos Geomecánicos")
    st.dataframe(datos_geomecanicos, use_container_width=True)
