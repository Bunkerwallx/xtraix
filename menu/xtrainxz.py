import os
import re
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from colorama import Fore, Style, init
import pyfiglet
from concurrent.futures import ThreadPoolExecutor

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
def extraer_urls(url):
    try:
        respuesta = requests.get(url, headers={'User-Agent': random.choice(userAgents)})
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        enlaces = soup.find_all('a', href=True)
        
        urls = []
        for enlace in enlaces:
            url_completa = urljoin(url, enlace['href'])
            urls.append(url_completa)
        
        return urls
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a la página {url}: {e}")
        return []

# Función para clasificar URLs multimedia
def obtener_urls_multimedia(url):
    try:
        response = requests.get(url, headers={'User-Agent': random.choice(userAgents)})
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
                elif re.search(r'\.(mp4|webm|avi|mov)$', recurso_url, re.IGNORECASE):
                    recursos["videos"].append(recurso_url)
                elif re.search(r'\.(mp3|wav|ogg|flac)$', recurso_url, re.IGNORECASE):
                    recursos["audios"].append(recurso_url)
                elif re.search(r'\.(pdf|docx|txt|xlsx|pptx)$', recurso_url, re.IGNORECASE):
                    recursos["documentos"].append(recurso_url)
                else:
                    recursos["otros"].append(recurso_url)
        
        return recursos
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a la URL {url}: {e}")
        return None

# Función para guardar recursos multimedia
def guardar_recursos(recursos, directorio):
    os.makedirs(directorio, exist_ok=True)
    
    for tipo, urls in recursos.items():
        tipo_dir = os.path.join(directorio, tipo)
        os.makedirs(tipo_dir, exist_ok=True)
        
        for url in urls:
            try:
                response = requests.get(url, headers={'User-Agent': random.choice(userAgents)})
                response.raise_for_status()
                
                filename = os.path.basename(url)
                filepath = os.path.join(tipo_dir, filename)
                
                with open(filepath, 'wb') as file:
                    file.write(response.content)
                
                print(f"Guardado: {filepath}")
            except requests.exceptions.RequestException as e:
                print(f"Error al descargar {url}: {e}")

# Ejecución del script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Herramienta de extracción y clasificación de contenido multimedia")
    parser.add_argument("urls", nargs="+", help="Una o más URLs a procesar")
    parser.add_argument("-o", "--output-dir", default="resultados", help="Directorio para guardar los recursos multimedia")
    args = parser.parse_args()

    print_figlet("BunkerWallx", font='slant', color=Fore.CYAN)

    with ThreadPoolExecutor() as executor:
        for url in args.urls:
            enlaces = executor.submit(extraer_urls, url).result()
            recursos = executor.submit(obtener_urls_multimedia, url).result()
            
            if recursos:
                guardar_recursos(recursos, os.path.join(args.output_dir, os.path.basename(url)))
            
            print(f"\nEnlaces encontrados en {url}:")
            for enlace in enlaces:
                print(Fore.LIGHTGREEN_EX + enlace)

