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

if "pestaña_activa" not in st.session_state:
    st.session_state.pestaña_activa = "Chat Asistente Operativo"
if "archivo_activo" not in st.session_state:
    st.session_state.archivo_activo = "Base de datos general (Simulación)"

# --- FUNCIÓN INTELIGENTE PARA LOGOS DE ARCHIVOS ---
def obtener_icono(nombre_archivo):
    nombre_lower = nombre_archivo.lower()
    if "simulación" in nombre_lower or "simulacion" in nombre_lower:
        return "⚙️"  
    elif nombre_lower.endswith('.pdf'):
        return "📕"  
    elif nombre_lower.endswith(('.csv', '.xlsx', '.xls')):
        return "📗"  
    elif nombre_lower.endswith(('.png', '.jpg', '.jpeg')):
        return "🖼️"  
    elif nombre_lower.endswith('.txt'):
        return "📝"  
    else:
        return "📄"  

# --- INYECCIÓN DE ESTÉTICA GEMINI (CSS Customizado) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Google Sans', sans-serif !important;
    }
    
    /* 1. FONDO DE PANTALLA COMPLETO */
    .stApp {
        background: linear-gradient(rgba(19, 19, 20, 0.65), rgba(19, 19, 20, 0.65)), 
                    url("https://github.com/jeanventocilla13-cpu/intranet-inkadrill/blob/main/fondo%20de%20escaneo.png?raw=true") no-repeat center center fixed !important;
        background-size: cover !important;
    }
    [data-testid="stHeader"] { background-color: transparent !important; }

    /* 2. BARRA LATERAL (CRISTAL) */
    [data-testid="stSidebar"] {
        background-color: rgba(19, 19, 20, 0.3) !important;
        backdrop-filter: blur(12px) !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important; 
    }

    /* 3. ALINEACIÓN PERFECTA (NAVEGACIÓN) */
    [data-testid="stSidebar"] button[kind="secondary"] {
        padding-left: 10px !important; 
        background-color: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        display: flex !important;
        justify-content: flex-start !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"] div {
        display: flex !important;
        justify-content: flex-start !important;
        width: 100% !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"] p {
        text-align: left !important;
        color: #c4c7c5 !important;
        margin: 0 !important;
        font-size: 14px !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
    }

    /* Botón Nueva Conversación */
    [data-testid="stSidebar"] button[kind="primary"] {
        border-radius: 30px !important;
        background-color: rgba(30, 31, 32, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #e3e3e3 !important;
        font-weight: 500 !important;
    }
    
    /* 4. RECIENTES CON CUADRO AMARILLO PERFECTO */
    div[role="radiogroup"] > label {
        background-color: transparent !important;
        padding: 8px 10px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        margin-bottom: 2px !important;
        transition: 0.2s;
    }
    div[role="radiogroup
