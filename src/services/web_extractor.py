import requests
import cloudscraper
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from playwright.sync_api import sync_playwright
import json
import re
import time
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import lxml.html

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalWebExtractor:
    """Extrator universal de dados de qualquer página web"""
    
    def __init__(self):
        self.session = requests.Session()
        self.scraper = cloudscraper.create_scraper()
        self.setup_headers()
        
    def setup_headers(self):
        """Configura headers para parecer um navegador real"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        self.session.headers.update(self.headers)
    
    def extract_data(self, url: str, method: str = "auto") -> Dict:
        """Extrai dados de uma URL usando o método mais apropriado"""
        try:
            logger.info(f"Extraindo dados de: {url} usando método: {method}")
            
            if method == "auto":
                method = self._detect_best_method(url)
            
            if method == "requests":
                return self._extract_with_requests(url)
            elif method == "cloudscraper":
                return self._extract_with_cloudscraper(url)
            elif method == "selenium":
                return self._extract_with_selenium(url)
            elif method == "playwright":
                return self._extract_with_playwright(url)
            else:
                raise ValueError(f"Método não suportado: {method}")
                
        except Exception as e:
            logger.error(f"Erro na extração de {url}: {e}")
            return self._create_error_response(url, str(e))
    
    def _detect_best_method(self, url: str) -> str:
        """Detecta o melhor método de extração baseado na URL"""
        domain = urlparse(url).netloc.lower()
        
        # Sites que geralmente precisam de JavaScript
        js_heavy_sites = [
            'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
            'youtube.com', 'tiktok.com', 'pinterest.com', 'amazon.com'
        ]
        
        # Sites com proteção anti-bot conhecida
        protected_sites = [
            'cloudflare', 'shopify', 'wix.com', 'squarespace.com'
        ]
        
        if any(site in domain for site in js_heavy_sites):
            return "playwright"
        elif any(site in domain for site in protected_sites):
            return "cloudscraper"
        else:
            return "requests"
    
    def _extract_with_requests(self, url: str) -> Dict:
        """Extração usando requests simples"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return self._parse_html_content(soup, url, "requests")
            
        except Exception as e:
            logger.warning(f"Requests falhou para {url}: {e}")
            # Fallback para cloudscraper
            return self._extract_with_cloudscraper(url)
    
    def _extract_with_cloudscraper(self, url: str) -> Dict:
        """Extração usando cloudscraper para bypass de proteções"""
        try:
            response = self.scraper.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return self._parse_html_content(soup, url, "cloudscraper")
            
        except Exception as e:
            logger.warning(f"Cloudscraper falhou para {url}: {e}")
            # Fallback para selenium
            return self._extract_with_selenium(url)
    
    def _extract_with_selenium(self, url: str) -> Dict:
        """Extração usando Selenium para sites com JavaScript"""
        driver = None
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'--user-agent={self.headers["User-Agent"]}')
            
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            
            # Aguarda carregamento
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Scroll para carregar conteúdo lazy-loaded
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            return self._parse_html_content(soup, url, "selenium")
            
        except Exception as e:
            logger.warning(f"Selenium falhou para {url}: {e}")
            # Fallback para playwright
            return self._extract_with_playwright(url)
        finally:
            if driver:
                driver.quit()
    
    def _extract_with_playwright(self, url: str) -> Dict:
        """Extração usando Playwright para máxima compatibilidade"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.headers['User-Agent'],
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()
                
                # Intercepta requests para otimizar
                page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda route: route.abort())
                
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Scroll para carregar conteúdo
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                
                html_content = page.content()
                browser.close()
                
                soup = BeautifulSoup(html_content, 'html.parser')
                return self._parse_html_content(soup, url, "playwright")
                
        except Exception as e:
            logger.error(f"Playwright falhou para {url}: {e}")
            return self._create_error_response(url, str(e))
    
    def _parse_html_content(self, soup: BeautifulSoup, url: str, method: str) -> Dict:
        """Analisa e extrai dados estruturados do HTML"""
        try:
            extracted_data = {
                "url": url,
                "method": method,
                "timestamp": time.time(),
                "success": True,
                "data": {}
            }
            
            # Metadados básicos
            extracted_data["data"]["title"] = self._extract_title(soup)
            extracted_data["data"]["description"] = self._extract_description(soup)
            extracted_data["data"]["keywords"] = self._extract_keywords(soup)
            
            # Conteúdo principal
            extracted_data["data"]["main_content"] = self._extract_main_content(soup)
            extracted_data["data"]["headings"] = self._extract_headings(soup)
            extracted_data["data"]["paragraphs"] = self._extract_paragraphs(soup)
            
            # Links e imagens
            extracted_data["data"]["links"] = self._extract_links(soup, url)
            extracted_data["data"]["images"] = self._extract_images(soup, url)
            
            # Dados estruturados (JSON-LD, microdata)
            extracted_data["data"]["structured_data"] = self._extract_structured_data(soup)
            
            # Informações de contato
            extracted_data["data"]["contact_info"] = self._extract_contact_info(soup)
            
            # Dados de e-commerce (se aplicável)
            extracted_data["data"]["ecommerce"] = self._extract_ecommerce_data(soup)
            
            # Redes sociais
            extracted_data["data"]["social_media"] = self._extract_social_media(soup)
            
            # Formulários
            extracted_data["data"]["forms"] = self._extract_forms(soup)
            
            # Texto limpo para análise
            extracted_data["data"]["clean_text"] = self._extract_clean_text(soup)
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Erro no parsing de {url}: {e}")
            return self._create_error_response(url, str(e))
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extrai título da página"""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # Fallbacks
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        return ""
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extrai descrição da página"""
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        # Open Graph description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
        
        # Primeiro parágrafo
        first_p = soup.find('p')
        if first_p:
            return first_p.get_text().strip()[:200]
        
        return ""
    
    def _extract_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extrai palavras-chave"""
        keywords = []
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            keywords.extend([k.strip() for k in meta_keywords['content'].split(',')])
        
        # Tags (se houver)
        tag_elements = soup.find_all(['span', 'div'], class_=re.compile(r'tag|keyword', re.I))
        for tag in tag_elements:
            keywords.append(tag.get_text().strip())
        
        return list(set(keywords))
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extrai conteúdo principal da página"""
        # Tenta encontrar o conteúdo principal usando seletores comuns
        main_selectors = [
            'main', 'article', '.content', '#content', '.main-content',
            '.post-content', '.entry-content', '.article-content'
        ]
        
        for selector in main_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        # Fallback: remove header, nav, footer, sidebar
        content_soup = soup.find('body')
        if content_soup:
            # Remove elementos não relacionados ao conteúdo
            for tag in content_soup.find_all(['header', 'nav', 'footer', 'aside', 'script', 'style']):
                tag.decompose()
            
            return content_soup.get_text().strip()
        
        return soup.get_text().strip()
    
    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extrai todos os cabeçalhos"""
        headings = {}
        for i in range(1, 7):
            tag = f'h{i}'
            elements = soup.find_all(tag)
            headings[tag] = [elem.get_text().strip() for elem in elements]
        
        return headings
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        """Extrai todos os parágrafos"""
        paragraphs = soup.find_all('p')
        return [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extrai todos os links"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            links.append({
                'text': link.get_text().strip(),
                'url': absolute_url,
                'internal': urlparse(absolute_url).netloc == urlparse(base_url).netloc
            })
        
        return links
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extrai todas as imagens"""
        images = []
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src:
                absolute_url = urljoin(base_url, src)
                images.append({
                    'url': absolute_url,
                    'alt': img.get('alt', ''),
                    'title': img.get('title', '')
                })
        
        return images
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrai dados estruturados (JSON-LD, microdata)"""
        structured_data = []
        
        # JSON-LD
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                structured_data.append(data)
            except:
                continue
        
        return structured_data
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict:
        """Extrai informações de contato"""
        contact_info = {
            'emails': [],
            'phones': [],
            'addresses': []
        }
        
        text = soup.get_text()
        
        # Emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        contact_info['emails'] = list(set(re.findall(email_pattern, text)))
        
        # Telefones
        phone_pattern = r'(\(?\d{2}\)?\s?\d{4,5}-?\d{4})'
        contact_info['phones'] = list(set(re.findall(phone_pattern, text)))
        
        return contact_info
    
    def _extract_ecommerce_data(self, soup: BeautifulSoup) -> Dict:
        """Extrai dados de e-commerce"""
        ecommerce = {
            'products': [],
            'prices': [],
            'reviews': []
        }
        
        # Preços
        price_selectors = ['.price', '.valor', '.preco', '[class*="price"]', '[class*="valor"]']
        for selector in price_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text().strip()
                if re.search(r'R\$|USD|\$|€', text):
                    ecommerce['prices'].append(text)
        
        # Reviews/avaliações
        review_selectors = ['.review', '.avaliacao', '[class*="review"]', '[class*="rating"]']
        for selector in review_selectors:
            elements = soup.select(selector)
            for elem in elements:
                ecommerce['reviews'].append(elem.get_text().strip())
        
        return ecommerce
    
    def _extract_social_media(self, soup: BeautifulSoup) -> Dict:
        """Extrai links de redes sociais"""
        social_media = {}
        
        social_patterns = {
            'facebook': r'facebook\.com/[^/\s]+',
            'instagram': r'instagram\.com/[^/\s]+',
            'twitter': r'twitter\.com/[^/\s]+',
            'linkedin': r'linkedin\.com/[^/\s]+',
            'youtube': r'youtube\.com/[^/\s]+',
            'whatsapp': r'wa\.me/[^/\s]+'
        }
        
        page_text = str(soup)
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                social_media[platform] = list(set(matches))
        
        return social_media
    
    def _extract_forms(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrai informações sobre formulários"""
        forms = []
        for form in soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'get'),
                'fields': []
            }
            
            for input_elem in form.find_all(['input', 'textarea', 'select']):
                form_data['fields'].append({
                    'type': input_elem.get('type', 'text'),
                    'name': input_elem.get('name', ''),
                    'placeholder': input_elem.get('placeholder', ''),
                    'required': input_elem.has_attr('required')
                })
            
            forms.append(form_data)
        
        return forms
    
    def _extract_clean_text(self, soup: BeautifulSoup) -> str:
        """Extrai texto limpo para análise"""
        # Remove scripts, styles, etc.
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        text = soup.get_text()
        # Limpa espaços extras
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _create_error_response(self, url: str, error: str) -> Dict:
        """Cria resposta de erro padronizada"""
        return {
            "url": url,
            "method": "error",
            "timestamp": time.time(),
            "success": False,
            "error": error,
            "data": {}
        }

