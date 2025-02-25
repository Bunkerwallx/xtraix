import os
import re
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
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

# Lista de user-agents
userAgents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
]

# Lista de proxies
proxies = [
    'http://proxy1:port',
    'http://proxy2:port',
]

def get_proxy():
    return random.choice(proxies) if proxies else None

# Función para mostrar un banner
def print_figlet(text, font='slant', color=Fore.BLUE):
    figlet_text = pyfiglet.Figlet(font=font).renderText(text)
    ancho_consola = os.get_terminal_size().columns
    for linea in figlet_text.splitlines():
        print(color + linea.center(ancho_consola) + Style.RESET_ALL)

# Validar URLs
def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

# Consultar robots.txt
def can_scrape(url):
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    try:
        response = requests.get(robots_url, timeout=5)
        if response.status_code == 200 and 'Disallow' in response.text:
            return False
    except requests.exceptions.RequestException:
        pass
    return True

# Obtener contenido con manejo de proxies y CAPTCHA
def fetch_url(url, retries=3):
    if not can_scrape(url):
        logging.warning(f"Acceso denegado por robots.txt: {url}")
        return None
    
    user_agent = random.choice(userAgents)
    headers = {
        'User-Agent': user_agent,
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/'
    }
    proxy = get_proxy()
    
    for attempt in range(retries):
        try:
            time.sleep(random.uniform(1, 5))  # Simula comportamiento humano
            response = requests.get(url, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=10)
            response.raise_for_status()
            
            if "captcha" in response.text.lower():
                logging.warning(f"CAPTCHA detectado en {url}")
                return None
            
            return response.text
        except requests.exceptions.RequestException as e:
            logging.warning(f"Intento {attempt + 1} fallido para {url}: {e}")
            time.sleep(2 ** attempt)
    
    logging.error(f"No se pudo acceder a {url}")
    return None

# Extraer URLs de una página
def extract_urls_from_page(url, base_url):
    html_content = fetch_url(url)
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, 'html.parser')
    urls = {urljoin(base_url, link['href']) for link in soup.find_all('a', href=True) if is_valid_url(urljoin(base_url, link['href']))}
    return list(urls)

# Indexar URLs por niveles
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

# Guardar en SQLite
def save_to_database(urls):
    conn = sqlite3.connect('scraped_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY, url TEXT UNIQUE)''')
    for url in urls:
        cursor.execute("INSERT OR IGNORE INTO urls (url) VALUES (?)", (url,))
    conn.commit()
    conn.close()

# Ejecución del script
if __name__ == "__main__":
    print_figlet("BunkerWallx", font='slant', color=Fore.CYAN)
    parser = argparse.ArgumentParser(description="Scraper avanzado con protección contra detección.")
    parser.add_argument("url", help="URL inicial para el scraping.")
    parser.add_argument("--level", type=int, default=2, help="Nivel máximo de profundidad.")
    args = parser.parse_args()

    start_time = time.time()
    indexed_urls = index_urls_by_level(args.url, args.level)
    save_to_database(indexed_urls)
    print(f"\nTiempo total: {time.time() - start_time:.2f} s")
    print(f"Total de URLs indexadas: {len(indexed_urls)}")
