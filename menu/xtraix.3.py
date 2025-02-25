import os
import re
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from colorama import Fore, Style, init
import pyfiglet
import concurrent.futures

# Inicializar colorama para el color de la terminal
init(autoreset=True)

# Lista de 15 agentes de usuario
userAgents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/58.0.3039.10 Safari/537.3',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:42.0) Gecko/20100101 Firefox/42.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:39.0) Gecko/20100101 Firefox/39.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36 Edge/74.0.1371.47',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:36.0) Gecko/20100101 Firefox/36.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:85.0) Gecko/20100101 Firefox/85.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
]

# Función para mostrar un banner con pyfiglet
def print_figlet(text, font='slant', color=Fore.BLUE):
    figlet_text = pyfiglet.Figlet(font=font).renderText(text)
    ancho_consola = os.get_terminal_size().columns
    for linea in figlet_text.splitlines():
        print(color + linea.center(ancho_consola) + Style.RESET_ALL)

# Función para obtener el contenido de una URL
def fetch_url(url):
    user_agent = random.choice(userAgents)
    headers = {'User-Agent': user_agent}
    try:
        response = requests.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a {url}: {e}")
        return None

# Función para extraer URLs de una página
def extract_urls_from_page(url, base_url):
    html_content = fetch_url(url)
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    urls = set()
    for link in soup.find_all('a', href=True):
        full_url = urljoin(base_url, link['href'])
        urls.add(full_url)
    return list(urls)

# Función para indexar URLs por niveles
def index_urls_by_level(start_url, max_level):
    visited = set()
    to_visit = [(start_url, 0)]
    all_urls = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        while to_visit:
            current_url, current_level = to_visit.pop(0)
            if current_url in visited or current_level > max_level:
                continue
            visited.add(current_url)
            print(f"Nivel {current_level}: Indexando {current_url}")
            all_urls.append(current_url)
            future_urls = executor.submit(extract_urls_from_page, current_url, start_url)
            new_urls = future_urls.result()
            for new_url in new_urls:
                if new_url not in visited:
                    to_visit.append((new_url, current_level + 1))
    
    return all_urls

# Función para clasificar URLs multimedia
def obtener_urls_multimedia(url):
    html_content = fetch_url(url)
    if not html_content:
        return None
    
    soup = BeautifulSoup(html_content, 'html.parser')
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

# Ejecución del script interactivo
if __name__ == "__main__":
    print_figlet("\nBunkerWallx", font='slant', color=Fore.CYAN)
    url_input = input(Fore.WHITE + f"\n\nIngresa la URL de la página: ").strip()
    
    # Indexar URLs por niveles
    max_level = int(input("Ingresa el nivel máximo de indexación: "))
    indexed_urls = index_urls_by_level(url_input, max_level)
    
    # Guardar las URLs indexadas en un archivo
    carpeta_usuario = os.path.expanduser('~')
    ruta_resultados = os.path.join(carpeta_usuario, 'resultados', 'urls_indexadas.txt')
    os.makedirs(os.path.dirname(ruta_resultados), exist_ok=True)
    
    with open(ruta_resultados, 'w') as archivo:
        for url in indexed_urls:
            archivo.write(f"{url}\n")
    
    print(f"\nResultados guardados en {ruta_resultados}")

    # Solicitar al usuario ingresar una URL para análisis multimedia
    url = input("INGRESA UNA URL para extraer contenido multimedia: ")
    recursos = obtener_urls_multimedia(url)

    if recursos:
        for tipo, urls in recursos.items():
            print(f"{tipo.capitalize()}: {len(urls)} encontrados")
            for recurso in urls:
                print(f"  - {recurso}")

