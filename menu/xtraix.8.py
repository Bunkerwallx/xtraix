import os
import re
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from colorama import Fore, Style, init
import pyfiglet
import concurrent.futures
import sqlite3
from queue import Queue
import logging
import argparse
import time

# Inicializar colorama para el color de la terminal
init(autoreset=True)

# Configuración de logging
logging.basicConfig(filename='scraper.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

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

# Lista de proxies (puedes usar un servicio de proxies rotativos)
proxies = [
    'http://proxy1:port',
    'http://proxy2:port',
    # Añade más proxies aquí
]

# Función para seleccionar un proxy aleatorio
def select_proxy():
    return random.choice(proxies) if proxies else None

# Función para rotar los proxies
def rotate_proxies():
    global proxies
    if proxies:
        proxies = proxies[1:] + [proxies[0]]  # Rotar la lista de proxies

# Función para mostrar un banner con pyfiglet
def print_figlet(text, font='slant', color=Fore.BLUE):
    figlet_text = pyfiglet.Figlet(font=font).renderText(text)
    ancho_consola = os.get_terminal_size().columns
    for linea in figlet_text.splitlines():
        print(color + linea.center(ancho_consola) + Style.RESET_ALL)

# Función para obtener el contenido de una URL con reintentos, proxies y delay aleatorio
def fetch_url(url, retries=3):
    user_agent = random.choice(userAgents)
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
        'Connection': 'keep-alive',
    }
    proxy = select_proxy()
    for attempt in range(retries):
        try:
            time.sleep(random.uniform(1, 3))  # Delay aleatorio entre solicitudes
            response = requests.get(url, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=10)
            response.raise_for_status()
            
            # Detectar CAPTCHA en la respuesta
            if "captcha" in response.text.lower():
                logging.warning(f"CAPTCHA detectado en {url}. Pausando el scraping.")
                return None
            
            return response.text
        except requests.exceptions.RequestException as e:
            logging.warning(f"Intento {attempt + 1} fallido para {url}: {e}")
            rotate_proxies()  # Rotar proxies en caso de error
            proxy = select_proxy()
            time.sleep(2 ** attempt)  # Espera exponencial
    logging.error(f"No se pudo acceder a {url} después de {retries} intentos")
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
    to_visit = Queue()
    to_visit.put((start_url, 0))
    all_urls = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        while not to_visit.empty():
            current_url, current_level = to_visit.get()
            if current_url in visited or current_level > max_level:
                continue
            visited.add(current_url)
            print(f"Nivel {current_level}: Indexando {current_url}")
            all_urls.append(current_url)
            future_urls = executor.submit(extract_urls_from_page, current_url, start_url)
            new_urls = future_urls.result()
            for new_url in new_urls:
                if new_url not in visited:
                    to_visit.put((new_url, current_level + 1))
    
    return all_urls

# Función para guardar resultados en una base de datos SQLite
def save_to_database(urls):
    conn = sqlite3.connect('scraped_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS urls
                      (id INTEGER PRIMARY KEY, url TEXT)''')
    for url in urls:
        cursor.execute("INSERT INTO urls (url) VALUES (?)", (url,))
    conn.commit()
    conn.close()

# Ejecución del script interactivo
if __name__ == "__main__":
    print_figlet("\nBunkerWallx", font='slant', color=Fore.CYAN)
    parser = argparse.ArgumentParser(description="Herramienta de scraping avanzada.")
    parser.add_argument("url", help="URL inicial para el scraping.")
    parser.add_argument("--level", type=int, default=2, help="Nivel máximo de profundidad.")
    args = parser.parse_args()

    start_time = time.time()
    indexed_urls = index_urls_by_level(args.url, args.level)
    save_to_database(indexed_urls)
    print(f"\nTiempo total de ejecución: {time.time() - start_time:.2f} segundos")
    print(f"Total de URLs indexadas: {len(indexed_urls)}")

