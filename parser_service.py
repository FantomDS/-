import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta
import time
import urllib.parse
import re
import json
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager


class ScholarParser:
    """Парсер научных статей из русскоязычных источников"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.driver = None
    
    def _init_selenium_driver(self):
        """Инициализация Selenium WebDriver (Firefox + Chrome fallback)"""
        if self.driver is None:
            # Сначала пробуем Firefox (как в Lfdd/Parser)
            firefox_works = self._init_firefox_driver()
            
            # Если Firefox не сработал, пробуем Chrome
            if not firefox_works:
                print("   Firefox не сработал, пробуем Chrome...")
                self._init_chrome_driver()
    
    def _init_firefox_driver(self):
        """Инициализация Firefox WebDriver с geckodriver"""
        try:
            from selenium.webdriver.firefox.service import Service as FirefoxService
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            
            firefox_options = FirefoxOptions()
            firefox_options.add_argument('--headless')
            firefox_options.add_argument('--window-size=1920,1080')
            firefox_options.add_argument('--lang=ru')
            
            # Отключаем загрузку изображений для ускорения
            firefox_options.set_preference('permissions.default.image', 2)
            firefox_options.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')
            
            # Пробуем автоматическую установку geckodriver
            try:
                from webdriver_manager.firefox import GeckoDriverManager
                service = FirefoxService(GeckoDriverManager().install())
            except:
                # Ручной путь
                gecko_path = os.path.join(os.path.dirname(__file__), '..', 'bin', 'geckodriver')
                if sys.platform == 'win32':
                    gecko_path += '.exe'
                
                if not os.path.exists(gecko_path):
                    print(f"   geckodriver не найден: {gecko_path}")
                    return False
                
                service = FirefoxService(executable_path=gecko_path)
            
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(5)
            
            print("   Firefox WebDriver инициализирован")
            return True
            
        except Exception as e:
            print(f"   Ошибка Firefox: {str(e)[:100]}")
            return False
    
    def _init_chrome_driver(self):
        """Инициализация Chrome WebDriver (запасной вариант)"""
        try:
            chrome_options = ChromeOptions()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--lang=ru')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0')
            
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(5)
            
            print("   Chrome WebDriver инициализирован")
            
        except Exception as e:
            print(f"   Ошибка Chrome: {str(e)[:100]}")
            raise
    
    def _close_selenium_driver(self):
        """Закрытие Selenium WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            print("   Selenium WebDriver закрыт")
    
    # =====================================================================
    #  ГЛАВНЫЙ МЕТОД СБОРА
    # =====================================================================
    
    def parse_all(self, limit_per_source=300):
        """Сбор статей со всех источников"""
        all_articles = []
        
        print("\n" + "="*60)
        print("СБОР НАУЧНЫХ СТАТЕЙ")
        print("="*60)
        
        # 1. eLibrary через Selenium
        print("\n1. Парсинг eLibrary (Selenium)...")
        elibrary = self.parse_elibrary_selenium(limit_per_source)
        all_articles.extend(elibrary)
        print(f"   Собрано: {len(elibrary)} статей")
        
        # 2. Хабр
        print("\n2. Парсинг Хабра...")
        habr = self.parse_habr_science(limit_per_source)
        all_articles.extend(habr)
        print(f"   Собрано: {len(habr)} статей")
        
        # 3. Crossref API
        print("\n3. Парсинг Crossref API...")
        crossref = self.parse_crossref(limit_per_source)
        all_articles.extend(crossref)
        print(f"   Собрано: {len(crossref)} статей")
        
        # 4. Google Scholar
        print("\n4. Парсинг Google Scholar...")
        scholar = self.parse_google_scholar(limit_per_source)
        all_articles.extend(scholar)
        print(f"   Собрано: {len(scholar)} статей")
        
        # 5. RSS ленты
        print("\n5. Парсинг RSS лент...")
        rss = self.parse_science_rss(limit_per_source)
        all_articles.extend(rss)
        print(f"   Собрано: {len(rss)} статей")
        
        # 6. DOAJ
        print("\n6. Парсинг DOAJ...")
        doaj = self.parse_doaj(limit_per_source)
        all_articles.extend(doaj)
        print(f"   Собрано: {len(doaj)} статей")
        
        # Закрываем Selenium
        self._close_selenium_driver()
        
        # Удаление дубликатов
        seen_titles = set()
        seen_urls = set()
        unique = []
        for article in all_articles:
            title = article.get('title', '').lower().strip()
            url = article.get('url', '')
            
            if title and title in seen_titles:
                continue
            if url and url in seen_urls:
                continue
            
            if title:
                seen_titles.add(title)
            if url:
                seen_urls.add(url)
            unique.append(article)
        
        print(f"\n{'='*60}")
        print(f"ВСЕГО УНИКАЛЬНЫХ СТАТЕЙ: {len(unique)}")
        print(f"{'='*60}")
        
        return unique
    
    # =====================================================================
    #  ПАРСИНГ ELIBRARY (SELENIUM)
    #  На основе подхода https://github.com/Lfdd/Parser
    # =====================================================================
    
    def parse_elibrary_selenium(self, limit=300):
        """
        Парсинг eLibrary через Selenium
        
        Алгоритм:
        1. Загружаем главную страницу для получения кук
        2. Для каждого запроса открываем страницу поиска
        3. Ищем ссылки на статьи (a[href*='item.asp'])
        4. Переходим на страницу каждой статьи
        5. Извлекаем: заголовок, авторов, аннотацию, ключевые слова, год, DOI, цитирования
        """
        articles = []
        
        try:
            self._init_selenium_driver()
            
            # Загружаем главную для кук
            print("   Загружаем главную страницу eLibrary...")
            try:
                self.driver.get("https://elibrary.ru")
                time.sleep(3)
                print(f"   Главная загружена: '{self.driver.title[:80]}'")
            except Exception as e:
                print(f"   Ошибка загрузки главной: {str(e)[:100]}")
            
            # Проверка на блокировку
            if '403' in self.driver.title or 'Доступ запрещен' in self.driver.page_source:
                print("   ДОСТУП ЗАПРЕЩЁН. Пропускаем eLibrary.")
                return articles[:limit]
            
            # Поисковые запросы
            queries = [
                'машинное обучение',
                'нейронные сети',
                'искусственный интеллект',
                'глубокое обучение',
                'большие данные',
                'робототехника',
                'квантовые вычисления',
                'биоинформатика',
                'генетика',
                'молекулярная биология',
                'нанотехнологии',
                'кибербезопасность',
                'экономика',
                'психология',
                'социология',
                'история',
                'философия',
                'педагогика',
                'медицина',
                'кардиология',
                'онкология',
                'неврология',
                'экология',
                'климат',
                'энергетика',
                'математическое моделирование',
                'органическая химия',
                'квантовая физика',
                'астрофизика',
                'геология',
            ]
            
            for query in queries:
                if len(articles) >= limit:
                    break
                
                try:
                    print(f"   Поиск: '{query}'")
                    
                    # Формируем URL поиска
                    search_url = f"https://elibrary.ru/query_results.asp?query={urllib.parse.quote(query)}"
                    self.driver.get(search_url)
                    time.sleep(4)
                    
                    # Получаем исходный код страницы
                    page_source = self.driver.page_source
                    current_url = self.driver.current_url
                    
                    print(f"      URL: {current_url[:100]}...")
                    
                    # Сохраняем для отладки (если нет результатов)
                    if 'item.asp' not in page_source:
                        os.makedirs('data/debug', exist_ok=True)
                        debug_file = f"data/debug/elibrary_{query.replace(' ', '_')}.html"
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(page_source[:15000])
                    
                    # Парсим HTML
                    soup = BeautifulSoup(page_source, 'html.parser')
                    
                    # Ищем ссылки на статьи
                    article_links = []
                    
                    # Способ 1: все ссылки с item.asp
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        if 'item.asp' in href and len(text) > 15:
                            full_url = f"https://elibrary.ru{href}" if href.startswith('/') else href
                            article_links.append({'href': full_url, 'title': text})
                    
                    # Способ 2: через Selenium (если BS не нашёл)
                    if not article_links:
                        try:
                            elements = self.driver.find_elements(By.TAG_NAME, "a")
                            for elem in elements:
                                try:
                                    href = elem.get_attribute('href')
                                    text = elem.text.strip()
                                    if href and 'item.asp' in href and len(text) > 15:
                                        article_links.append({'href': href, 'title': text})
                                except:
                                    continue
                        except:
                            pass
                    
                    # Способ 3: строки таблицы
                    if not article_links:
                        try:
                            rows = self.driver.find_elements(By.CSS_SELECTOR, "tr[valign='top']")
                            for row in rows:
                                try:
                                    links = row.find_elements(By.TAG_NAME, "a")
                                    for link in links:
                                        href = link.get_attribute('href')
                                        text = link.text.strip()
                                        if href and 'item.asp' in href and len(text) > 15:
                                            article_links.append({'href': href, 'title': text})
                                            break
                                except:
                                    continue
                        except:
                            pass
                    
                    print(f"      Найдено ссылок: {len(article_links)}")
                    
                    # Переходим на страницу каждой статьи
                    articles_before = len(articles)
                    for i, link_info in enumerate(article_links[:15]):
                        if len(articles) >= limit:
                            break
                        
                        try:
                            article_data = self._parse_elibrary_article_page(
                                link_info['href'],
                                link_info['title'],
                                query
                            )
                            if article_data:
                                articles.append(article_data)
                                
                                # Прогресс каждые 5 статей
                                if (i + 1) % 5 == 0:
                                    print(f"         [{i+1}/{min(len(article_links), 15)}] {article_data['title'][:60]}...")
                            
                        except Exception as e:
                            continue
                        
                        time.sleep(0.5)
                    
                    found = len(articles) - articles_before
                    print(f"      Собрано: {found} статей (всего: {len(articles)})")
                    
                    # Задержка между запросами
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"   Ошибка запроса '{query}': {str(e)[:150]}")
                    continue
            
        except Exception as e:
            print(f"   Общая ошибка парсинга eLibrary: {str(e)[:150]}")
        
        return articles[:limit]
    
    def _parse_elibrary_article_page(self, url, fallback_title, category):
        """
        Детальный парсинг страницы статьи на eLibrary
        
        Извлекает:
        - Точный заголовок
        - Список авторов
        - Аннотацию
        - Ключевые слова
        - Год публикации
        - DOI
        - Количество цитирований
        - Название журнала
        """
        try:
            # Загружаем страницу статьи
            self.driver.get(url)
            time.sleep(1)
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Весь текст страницы
            all_text = soup.get_text()
            all_text_clean = re.sub(r'\s+', ' ', all_text)
            
            # 1. ЗАГОЛОВОК
            title = fallback_title
            
            # Селекторы для заголовка (по приоритету)
            title_selectors = [
                "td[style*='font-size:14px'] span",
                "td[style*='font-size:14px'] b",
                "font[color='#000080'] b",
                "td b",
                "span[style*='font-size:14px']",
            ]
            
            for selector in title_selectors:
                elems = soup.select(selector)
                for elem in elems:
                    text = elem.get_text(strip=True)
                    if 20 < len(text) < 500:
                        title = text
                        break
                if title != fallback_title:
                    break
            
            # 2. АВТОРЫ
            authors = []
            
            # Через ссылки authorid
            for link in soup.select("a[href*='authorid']"):
                name = link.get_text(strip=True)
                if name and len(name) > 5 and not name.startswith('http'):
                    # Проверяем, что это не дубликат
                    if not any(a['name'] == name for a in authors):
                        authors.append({'name': name})
            
            # Через паттерн Фамилия И.О.
            if not authors:
                author_pattern = re.findall(
                    r'([А-ЯЁ][а-яё]+)\s+([А-ЯЁ])\.\s*([А-ЯЁ])\.',
                    all_text_clean
                )
                seen_names = set()
                for surname, initial1, initial2 in author_pattern[:10]:
                    name = f'{surname} {initial1}.{initial2}.'
                    if name not in seen_names:
                        seen_names.add(name)
                        authors.append({'name': name})
            
            if not authors:
                authors = [{'name': 'Неизвестен'}]
            
            # 3. АННОТАЦИЯ
            abstract = ''
            
            abstract_patterns = [
                r'(?:Аннотация|Реферат|Abstract|РЕФЕРАТ)\s*[.:]\s*(.*?)(?:\s*(?:Ключевые|Keywords|Автор|Источник|Литература|$))',
                r'(?:Аннотация|Реферат)\s*[.:]\s*(.*?)$',
            ]
            
            for pattern in abstract_patterns:
                match = re.search(pattern, all_text_clean, re.DOTALL | re.IGNORECASE)
                if match:
                    abstract_text = match.group(1).strip()
                    if len(abstract_text) > 50:
                        abstract = abstract_text[:1000]
                        break
            
            if not abstract:
                # Берём всё, что не заголовок и не авторы
                clean = all_text_clean
                for author in authors:
                    clean = clean.replace(author['name'], '')
                clean = clean.replace(title, '')
                abstract = clean.strip()[:500]
            
            # 4. ГОД ПУБЛИКАЦИИ
            pub_date = None
            
            year_patterns = [
                r'(?:Год:|год|Год издания:)\s*(\d{4})',
                r'(?:Published:|Year:)\s*(\d{4})',
                r'(\d{4})\s*(?:г\.|год|году)',
                r'(\d{4})',
            ]
            
            for pattern in year_patterns:
                match = re.search(pattern, all_text_clean, re.IGNORECASE)
                if match:
                    year = int(match.group(1))
                    if 1950 <= year <= 2025:
                        pub_date = datetime(year, 1, 1)
                        break
            
            # 5. КЛЮЧЕВЫЕ СЛОВА
            keywords = []
            
            kw_patterns = [
                r'(?:Ключевые слова|Keywords|КЛЮЧЕВЫЕ СЛОВА)\s*[.:]\s*(.*?)(?:\s*(?:$|\n|Автор|Источник|Литература))',
            ]
            
            for pattern in kw_patterns:
                match = re.search(pattern, all_text_clean, re.DOTALL | re.IGNORECASE)
                if match:
                    kw_text = match.group(1).strip()
                    # Разделяем по запятым, точкам с запятой, точкам
                    keywords = [k.strip().lower() for k in re.split(r'[,;.]', kw_text) 
                              if len(k.strip()) > 3]
                    if keywords:
                        break
            
            if not keywords:
                keywords = self._extract_keywords(title + ' ' + abstract)
            
            # 6. ЦИТИРОВАНИЯ
            citation_count = 0
            
            cit_patterns = [
                r'(?:Цитирований|Cited|Цитируется|Всего ссылок)\s*[.:]\s*(\d+)',
                r'(?:цитирований|цитирования|цитирование)\s*[.:]\s*(\d+)',
            ]
            
            for pattern in cit_patterns:
                match = re.search(pattern, all_text_clean, re.IGNORECASE)
                if match:
                    citation_count = int(match.group(1))
                    break
            
            # 7. DOI
            doi = None
            doi_match = re.search(r'(10\.\d{4,}/[^\s<>"]+)', all_text_clean)
            if doi_match:
                doi = doi_match.group(1).rstrip('.,;')
            
            # 8. ЖУРНАЛ
            journal = ''
            journal_match = re.search(
                r'(?:Журнал:|Издание:|Journal:|Источник:)\s*([^\n]+)',
                all_text_clean, re.IGNORECASE
            )
            if journal_match:
                journal = journal_match.group(1).strip()[:200]
            
            return {
                'title': title,
                'abstract': abstract[:500] if abstract else title,
                'content': abstract if abstract else title,
                'url': url,
                'doi': doi,
                'source': 'elibrary',
                'source_id': f'elib_{abs(hash(title))}',
                'authors': authors,
                'keywords': keywords,
                'categories': [category, journal] if journal else [category],
                'published_date': pub_date,
                'language': 'ru',
                'citation_count': citation_count
            }
            
        except Exception as e:
            # Fallback: возвращаем хотя бы заголовок
            return {
                'title': fallback_title,
                'abstract': fallback_title,
                'content': fallback_title,
                'url': url,
                'source': 'elibrary',
                'source_id': f'elib_{abs(hash(fallback_title))}',
                'authors': [{'name': 'Неизвестен'}],
                'keywords': self._extract_keywords(fallback_title),
                'categories': [category],
                'published_date': None,
                'language': 'ru',
                'citation_count': 0
            }
    
    # =====================================================================
    #  ПАРСИНГ ХАБРА
    # =====================================================================
    
    def parse_habr_science(self, limit=400):
        """Парсинг статей с Хабра"""
        articles = []
        
        hubs = [
            ('machine_learning', 'Машинное обучение'),
            ('data_science', 'Data Science'),
            ('artificial_intelligence', 'ИИ'),
            ('algorithms', 'Алгоритмы'),
            ('programming', 'Программирование'),
            ('maths', 'Математика'),
            ('physics', 'Физика'),
            ('biotech', 'Биотехнологии'),
            ('space', 'Космос'),
            ('neural_networks', 'Нейронные сети'),
            ('bigdata', 'Большие данные'),
            ('robotics', 'Робототехника'),
            ('electronics', 'Электроника'),
            ('health', 'Здоровье'),
            ('ecology', 'Экология'),
            ('energy', 'Энергетика'),
        ]
        
        for hub_slug, hub_name in hubs:
            if len(articles) >= limit:
                break
            
            page = 1
            while len(articles) < limit and page <= 5:
                try:
                    url = f"https://habr.com/ru/hubs/{hub_slug}/articles/page{page}/"
                    response = self.session.get(url, timeout=15)
                    
                    if response.status_code != 200:
                        break
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    cards = soup.find_all('article', class_='tm-articles-list__item')
                    
                    if not cards:
                        break
                    
                    for card in cards:
                        if len(articles) >= limit:
                            break
                        
                        try:
                            title_elem = card.find('a', class_='tm-title__link')
                            if not title_elem:
                                continue
                            
                            title = title_elem.get_text(strip=True)
                            href = title_elem.get('href', '')
                            link = 'https://habr.com' + href if href.startswith('/') else href
                            
                            body = card.find('div', class_='tm-article-body')
                            content = body.get_text(strip=True)[:2000] if body else title
                            
                            author_elem = card.find('a', class_='tm-user-info__username')
                            author_name = author_elem.get_text(strip=True) if author_elem else 'Хабр'
                            
                            pub_date = None
                            date_elem = card.find('time')
                            if date_elem:
                                datetime_attr = date_elem.get('datetime')
                                if datetime_attr:
                                    try:
                                        pub_date = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                                    except:
                                        pass
                            
                            tag_elems = card.find_all('a', class_='tm-tags-list__link')
                            tags = [t.get_text(strip=True).replace('*', '') for t in tag_elems[:5]]
                            
                            articles.append({
                                'title': title,
                                'abstract': content[:500] if len(content) > 500 else content,
                                'content': content,
                                'url': link,
                                'source': 'habr',
                                'source_id': f'habr_{href}',
                                'authors': [{'name': author_name}],
                                'keywords': tags if tags else self._extract_keywords(title + ' ' + content),
                                'categories': [hub_name],
                                'published_date': pub_date,
                                'language': 'ru',
                                'citation_count': 0
                            })
                            
                        except:
                            continue
                    
                    page += 1
                    time.sleep(0.3)
                    
                except Exception as e:
                    print(f"   Ошибка хаба {hub_name}: {e}")
                    break
        
        return articles[:limit]
    
    # =====================================================================
    #  ПАРСИНГ CROSSREF
    # =====================================================================
    
    def parse_crossref(self, limit=400):
        """Парсинг через Crossref API"""
        articles = []
        
        queries = [
            'машинное обучение', 'нейронные сети', 'искусственный интеллект',
            'большие данные', 'компьютерное зрение', 'робототехника',
            'квантовая физика', 'молекулярная биология', 'органическая химия',
            'кардиология', 'онкология', 'неврология', 'генетика',
            'экология', 'климат', 'энергетика', 'нанотехнологии',
            'экономика', 'психология', 'социология', 'история',
        ]
        
        for query in queries:
            if len(articles) >= limit:
                break
            
            try:
                url = f"https://api.crossref.org/works?query={urllib.parse.quote(query)}&rows=20"
                response = self.session.get(url, timeout=15)
                data = response.json()
                
                items = data.get('message', {}).get('items', [])
                
                for item in items:
                    if len(articles) >= limit:
                        break
                    
                    try:
                        title_list = item.get('title', ['Без названия'])
                        title = title_list[0] if title_list else 'Без названия'
                        
                        if len(title) < 10:
                            continue
                        
                        authors = []
                        for author in item.get('author', [])[:5]:
                            family = author.get('family', '')
                            given = author.get('given', '')
                            if family or given:
                                authors.append({'name': f'{given} {family}'.strip()})
                        
                        if not authors:
                            authors = [{'name': 'Неизвестен'}]
                        
                        pub_date = None
                        date_parts = item.get('published-print', {}).get('date-parts', [[]])[0]
                        if not date_parts:
                            date_parts = item.get('created', {}).get('date-parts', [[]])[0]
                        if date_parts and len(date_parts) >= 1:
                            year = date_parts[0]
                            month = date_parts[1] if len(date_parts) > 1 else 1
                            day = date_parts[2] if len(date_parts) > 2 else 1
                            if 1990 <= year <= 2025:
                                pub_date = datetime(year, month, day)
                        
                        abstract = item.get('abstract', '')
                        if abstract:
                            soup_abs = BeautifulSoup(abstract, 'html.parser')
                            abstract = soup_abs.get_text(strip=True)
                        
                        doi = item.get('DOI', '')
                        article_url = item.get('URL', f'https://doi.org/{doi}' if doi else '')
                        
                        articles.append({
                            'title': title,
                            'abstract': abstract[:500] if abstract else title,
                            'content': abstract if abstract else title,
                            'url': article_url,
                            'doi': doi,
                            'source': 'crossref',
                            'source_id': doi or f'crossref_{hash(title)}',
                            'authors': authors,
                            'keywords': item.get('subject', []),
                            'categories': [query],
                            'published_date': pub_date,
                            'language': 'ru',
                            'citation_count': item.get('is-referenced-by-count', 0)
                        })
                        
                    except:
                        continue
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   Ошибка '{query}': {e}")
                continue
        
        return articles[:limit]
    
    # =====================================================================
    #  ПАРСИНГ GOOGLE SCHOLAR
    # =====================================================================
    
    def parse_google_scholar(self, limit=300):
        """Парсинг Google Scholar"""
        articles = []
        
        queries = [
            'машинное обучение', 'нейронные сети', 'искусственный интеллект',
            'квантовая физика', 'молекулярная биология', 'генетика',
            'экономика', 'история', 'психология',
            'медицина', 'экология', 'астрономия',
            'робототехника', 'нанотехнологии', 'биотехнологии',
            'социология', 'философия', 'педагогика',
        ]
        
        for query in queries:
            if len(articles) >= limit:
                break
            
            try:
                url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(query)}&hl=ru&as_sdt=0,5&num=20"
                response = self.session.get(url, timeout=15)
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = soup.find_all('div', class_='gs_r')
                
                for item in results:
                    if len(articles) >= limit:
                        break
                    
                    try:
                        title_elem = item.find('h3', class_='gs_rt')
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        if len(title) < 10:
                            continue
                        
                        link = ''
                        link_elem = title_elem.find('a')
                        if link_elem:
                            link = link_elem.get('href', '')
                        
                        abstract_elem = item.find('div', class_='gs_rs')
                        abstract = abstract_elem.get_text(strip=True) if abstract_elem else title
                        
                        info_elem = item.find('div', class_='gs_a')
                        info_text = info_elem.get_text(strip=True) if info_elem else ''
                        
                        authors_part = info_text.split('-')[0] if '-' in info_text else info_text
                        author_names = [a.strip() for a in authors_part.split(',') if a.strip()]
                        authors = [{'name': a} for a in author_names[:5]]
                        
                        if not authors:
                            authors = [{'name': 'Неизвестен'}]
                        
                        year_match = re.search(r'(\d{4})', info_text)
                        pub_date = None
                        if year_match:
                            year = int(year_match.group(1))
                            if 1990 <= year <= 2025:
                                pub_date = datetime(year, 1, 1)
                        
                        articles.append({
                            'title': title,
                            'abstract': abstract[:500],
                            'content': abstract,
                            'url': link,
                            'source': 'google_scholar',
                            'source_id': f'scholar_{hash(title)}',
                            'authors': authors,
                            'keywords': self._extract_keywords(title + ' ' + abstract),
                            'categories': [query],
                            'published_date': pub_date,
                            'language': 'ru',
                            'citation_count': 0
                        })
                        
                    except:
                        continue
                
                time.sleep(2)
                
            except Exception as e:
                print(f"   Ошибка '{query}': {e}")
                continue
        
        return articles[:limit]
    
    # =====================================================================
    #  ПАРСИНГ RSS ЛЕНТ
    # =====================================================================
    
    def parse_science_rss(self, limit=300):
        """Парсинг RSS лент"""
        articles = []
        
        rss_feeds = [
            ('https://nplus1.ru/rss', 'nplus1', 'ru'),
            ('https://postnauka.org/feed', 'postnauka', 'ru'),
            ('https://naked-science.ru/rss', 'naked_science', 'ru'),
            ('https://indicator.ru/feed', 'indicator', 'ru'),
            ('https://habr.com/ru/rss/articles/?fl=ru', 'habr_rss', 'ru'),
        ]
        
        for feed_url, source_name, lang in rss_feeds:
            if len(articles) >= limit:
                break
            
            try:
                print(f"   {source_name}...")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries:
                    if len(articles) >= limit:
                        break
                    
                    title = entry.get('title', '').strip()
                    if not title:
                        continue
                    
                    desc = entry.get('description', entry.get('summary', ''))
                    soup_entry = BeautifulSoup(desc, 'html.parser')
                    clean_text = soup_entry.get_text(strip=True)
                    
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    
                    articles.append({
                        'title': title,
                        'abstract': clean_text[:500] if len(clean_text) > 500 else clean_text,
                        'content': clean_text,
                        'url': entry.get('link', ''),
                        'source': source_name,
                        'source_id': f'{source_name}_{hash(title)}',
                        'authors': [{'name': entry.get('author', 'Редакция')}],
                        'keywords': self._extract_keywords(title + ' ' + clean_text),
                        'categories': [],
                        'published_date': pub_date,
                        'language': lang,
                        'citation_count': 0
                    })
                    
            except Exception as e:
                print(f"   Ошибка {source_name}: {e}")
                continue
        
        return articles[:limit]
    
    # =====================================================================
    #  ПАРСИНГ DOAJ
    # =====================================================================
    
    def parse_doaj(self, limit=200):
        """Парсинг DOAJ"""
        articles = []
        
        queries = [
            'machine learning', 'neural networks', 'artificial intelligence',
            'quantum physics', 'molecular biology', 'genetics',
            'climate change', 'renewable energy', 'nanotechnology',
            'medicine', 'psychology', 'economics',
        ]
        
        for query in queries:
            if len(articles) >= limit:
                break
            
            try:
                url = f"https://doaj.org/api/search/articles/{urllib.parse.quote(query)}?pageSize=20"
                response = self.session.get(url, timeout=15)
                data = response.json()
                
                results = data.get('results', [])
                
                for item in results:
                    if len(articles) >= limit:
                        break
                    
                    try:
                        bibjson = item.get('bibjson', {})
                        title = bibjson.get('title', 'Без названия')
                        
                        if len(title) < 10:
                            continue
                        
                        authors = []
                        for author in bibjson.get('author', [])[:5]:
                            name = author.get('name', '')
                            if name:
                                authors.append({'name': name})
                        
                        if not authors:
                            authors = [{'name': 'Неизвестен'}]
                        
                        abstract = bibjson.get('abstract', '')
                        
                        pub_date = None
                        year = bibjson.get('year')
                        if year:
                            try:
                                pub_date = datetime(int(year), 1, 1)
                            except:
                                pass
                        
                        link = ''
                        for identifier in bibjson.get('identifier', []):
                            if identifier.get('type') == 'url':
                                link = identifier.get('id', '')
                                break
                        
                        articles.append({
                            'title': title,
                            'abstract': abstract[:500] if abstract else title,
                            'content': abstract if abstract else title,
                            'url': link,
                            'source': 'doaj',
                            'source_id': item.get('id', f'doaj_{hash(title)}'),
                            'authors': authors,
                            'keywords': bibjson.get('keywords', []),
                            'categories': [query],
                            'published_date': pub_date,
                            'language': 'ru',
                            'citation_count': 0
                        })
                        
                    except:
                        continue
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   Ошибка '{query}': {e}")
                continue
        
        return articles[:limit]
    
    # =====================================================================
    #  ВСПОМОГАТЕЛЬНЫЙ МЕТОД
    # =====================================================================
    
    def _extract_keywords(self, text, max_kw=8):
        """Извлечение ключевых слов"""
        if not text:
            return []
        
        stop_words = {
            'и', 'в', 'на', 'с', 'по', 'к', 'от', 'для', 'как', 'что',
            'это', 'не', 'но', 'или', 'быть', 'был', 'была', 'были',
            'он', 'она', 'оно', 'они', 'мы', 'вы', 'я', 'ты',
            'его', 'ее', 'их', 'мой', 'твой', 'наш', 'ваш',
            'весь', 'вся', 'все', 'сам', 'сама', 'сами', 'себя',
            'который', 'которая', 'которые', 'очень', 'более', 'менее',
            'также', 'еще', 'уже', 'бы', 'же', 'ли', 'то', 'того',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them'
        }
        
        words = text.lower().split()
        keywords = [w.strip('.,!?:;()[]{}""\'«»') for w in words
                   if w.strip('.,!?:;()[]{}""\'«»') not in stop_words
                   and len(w.strip('.,!?:;()[]{}""\'«»')) > 3]
        
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
        
        return unique[:max_kw]