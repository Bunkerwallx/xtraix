import os
import re
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from colorama import Fore, Style, init
import pyfiglet

# Inicializar colorama para el color de la terminal
init(autoreset=True)

# Lista de agentes de usuario
userAgents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/58.0.3039.10 Safari/537.3',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    
]

# Función para mostrar un banner con pyfiglet
def print_figlet(text, font='slant', color=Fore.BLUE):
    figlet_text = pyfiglet.Figlet(font=font).renderText(text)
    ancho_consola = os.get_terminal_size().columns
    for linea in figlet_text.splitlines():
        print(color + linea.center(ancho_consola) + Style.RESET_ALL)

# Función para extraer URLs de enlaces de la página
def extraer_urls():
    print_figlet("BunkerWallx", font='slant', color=Fore.CYAN)
    url_input = input("\nIngresa la URL de la página: ").strip()
    
    try:
        respuesta = requests.get(url_input)
        respuesta.raise_for_status()  
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        enlaces = soup.find_all('a', href=True)
        
        carpeta_usuario = os.path.expanduser('~')
        ruta_resultados = os.path.join(carpeta_usuario, 'resultados', 'urls_extraidas.txt')
        os.makedirs(os.path.dirname(ruta_resultados), exist_ok=True)
        
        with open(ruta_resultados, 'w') as archivo:
            print("\nURLs encontradas:")
            for contador, enlace in enumerate(enlaces, start=1):
                url_completa = urljoin(url_input, enlace['href'])
                print(Fore.LIGHTGREEN_EX + f"{contador}: {url_completa}")
                archivo.write(f"{contador}: {url_completa}\n")
        
        print(f"\nResultados guardados en {ruta_resultados}")
    
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a la página: {e}")

# Función para clasificar URLs multimedia
def obtener_urls_multimedia(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        recursos = {
            "imagenes": [],
            "videos": [],
            "audios": [],
            "documentos": [],
            "otros": []
        }
        
        for tag in soup.find_all(['img', 'a', 'video', 'audio', 'source']):
            recurso_url = tag.get('src') or tag.get('href')
            if recurso_url:
                if re.search(r'\.(jpg|jpeg|png|gif|svg)$', recurso_url, re.IGNORECASE):
                    recursos["imagenes"].append(recurso_url)
                elif re.search(r'\.(mp4|webm|avi)$', recurso_url, re.IGNORECASE):
                    recursos["videos"].append(recurso_url)
                elif re.search(r'\.(mp3|wav|ogg)$', recurso_url, re.IGNORECASE):
                    recursos["audios"].append(recurso_url)
                elif re.search(r'\.(pdf|docx|txt)$', recurso_url, re.IGNORECASE):
                    recursos["documentos"].append(recurso_url)
                else:
                    recursos["otros"].append(recurso_url)
        
        return recursos
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a la URL: {e}")
        return None

# Ejecución del script interactivo
if __name__ == "__main__":
    extraer_urls()

    # Solicitar al usuario ingresar una URL para análisis multimedia
    url = input("INGRESA UNA URL para extraer contenido multimedia: ")
    recursos = obtener_urls_multimedia(url)

    if recursos:
        for tipo, urls in recursos.items():
            print(f"{tipo.capitalize()}: {len(urls)} encontrados")
            for recurso in urls:
                print(f"  - {recurso}")

