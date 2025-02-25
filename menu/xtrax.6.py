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

# Inicializar colorama
init(autoreset=True)

# Configuración de logging
logging.basicConfig(filename='scraper.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Agentes de usuario
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
]

# Lista de proxies (añadir proxies reales si se desea anonimato)
PROXIES = [
    'http://proxy1:port',
    'http://proxy2:port',
]

# Inicializar sesión de requests para reutilizar conexiones
session = requests.Session()

# Función para mostrar un banner con pyfiglet
def print_figlet(text, font='slant', color=Fore.BLUE):
    figlet_text = pyfiglet.Figlet(font=font).renderText(text)
    ancho_consola = os.get_terminal_size().columns
    for linea in figlet_text.splitlines():
        print(color + linea.center(ancho_consola) + Style.RESET_ALL)

# Función para obtener el contenido de una URL con reintentos
def fetch_url(url, retries=3):
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    proxy = random.choice(PROXIES) if PROXIES else None
    for attempt in range(retries):
        try:
            response = session.get(url, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logging.warning(f"Intento {attempt + 1} fallido para {url}: {e}")
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
    
    try:
        for link in soup.find_all('a', href=True):
            full_url = urljoin(base_url, link['href'])
            if re.match(r'^https?://', full_url):
                urls.add(full_url)
    except Exception as e:
        logging.error(f"Error procesando {url}: {e}")
    
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
            logging.info(f"Nivel {current_level}: Indexando {current_url}")
            print(f"Nivel {current_level}: Indexando {current_url}")
            all_urls.append(current_url)

            # Extraer nuevas URLs de forma concurrente
            future = executor.submit(extract_urls_from_page, current_url, start_url)
            new_urls = future.result()
            for new_url in new_urls:
                if new_url not in visited:
                    to_visit.put((new_url, current_level + 1))

    return all_urls

# Función para guardar URLs en SQLite
def save_to_database(urls):
    conn = sqlite3.connect('scraped_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS urls
                      (id INTEGER PRIMARY KEY, url TEXT UNIQUE)''')

    for url in urls:
        try:
            cursor.execute("INSERT INTO urls (url) VALUES (?)", (url,))
        except sqlite3.IntegrityError:
            logging.info(f"URL duplicada ignorada: {url}")

    conn.commit()
    conn.close()

# Función para obtener el total de URLs en la base de datos
def count_saved_urls():
    conn = sqlite3.connect('scraped_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM urls")
    count = cursor.fetchone()[0]
    conn.close()
    return count

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

    total_urls = count_saved_urls()
    print(f"\nTiempo total de ejecución: {time.time() - start_time:.2f} segundos")
    print(f"Total de URLs indexadas y guardadas: {total_urls}")

