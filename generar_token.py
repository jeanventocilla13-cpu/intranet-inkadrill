from google_auth_oauthlib.flow import InstalledAppFlow

# Este es el nuevo alcance: Permiso TOTAL (Lectura y Escritura)
SCOPES = ['https://www.googleapis.com/auth/drive']

def main():
    print("Iniciando proceso de autorización...")
    # Lee tus credenciales secretas
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    
    # Abre el navegador para que aceptes los permisos
    creds = flow.run_local_server(port=0)
    
    # Guarda el nuevo súper-token
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
        
    print("¡NUEVO token.json GENERADO CON ÉXITO! Ya puedes copiarlo a Streamlit.")

if __name__ == '__main__':
    main()
