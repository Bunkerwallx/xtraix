import os
import re
import json
import random
import logging
import requests
import queue
import threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from colorama import Fore, Style, init
import pyfiglet

# Inicializar colorama
init(autoreset=True)

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Agentes de usuario
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3039.10 Safari/537.3',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
]

# Función para mostrar un banner
def print_figlet(text, font='slant', color=Fore.BLUE):
    figlet_text = pyfiglet.Figlet(font=font).renderText(text)
    print(color + figlet_text + Style.RESET_ALL)

# Función para obtener el contenido de una URL
def fetch_url(url):
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logging.warning(f"Error accediendo a {url}: {e}")
        return None

# Función para extraer URLs de una página
def extract_urls_from_page(url, base_url):
    html_content = fetch_url(url)
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    return list(set(urljoin(base_url, link['href']) for link in soup.find_all('a', href=True)))

# Función para indexar URLs por niveles
def index_urls_by_level(start_url, max_level):
    visited = set()
    url_queue = queue.Queue()
    url_queue.put((start_url, 0))
    all_urls = []
    
    while not url_queue.empty():
        current_url, current_level = url_queue.get()
        if current_url in visited or current_level > max_level:
            continue
        
        visited.add(current_url)
        logging.info(f"Nivel {current_level}: Indexando {current_url}")
        all_urls.append(current_url)
        
        for new_url in extract_urls_from_page(current_url, start_url):
            if new_url not in visited:
                url_queue.put((new_url, current_level + 1))
    
    return all_urls

# Función para extraer recursos multimedia
def obtener_urls_multimedia(url):
    html_content = fetch_url(url)
    if not html_content:
        return None
    
    soup = BeautifulSoup(html_content, 'html.parser')
    recursos = {"imagenes": [], "videos": [], "audios": [], "documentos": [], "otros": []}
    
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

# Guardar resultados en un archivo JSON
def guardar_resultados_json(nombre_archivo, datos):
    ruta = os.path.join(os.path.expanduser('~'), 'resultados', nombre_archivo)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as archivo:
        json.dump(datos, archivo, indent=4, ensure_ascii=False)
    logging.info(f"Resultados guardados en {ruta}")

# Ejecución del script interactivo
if __name__ == "__main__":
    print_figlet("BunkerWallx", font='slant', color=Fore.CYAN)
    url_input = input(Fore.WHITE + "\nIngresa la URL de la página: ").strip()
    
    max_level = int(input("Ingresa el nivel máximo de indexación: "))
    indexed_urls = index_urls_by_level(url_input, max_level)
    guardar_resultados_json('urls_indexadas.json', indexed_urls)
    
    url_multimedia = input("\nIngresa una URL para extraer contenido multimedia: ").strip()
    recursos = obtener_urls_multimedia(url_multimedia)
    
    if recursos:
        guardar_resultados_json('recursos_multimedia.json', recursos)
        for tipo, urls in recursos.items():
            print(f"{tipo.capitalize()}: {len(urls)} encontrados")
            for recurso in urls:
                print(f"  - {recurso}")
