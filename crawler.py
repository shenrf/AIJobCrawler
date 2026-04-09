from bs4 import BeautifulSoup
import threading
import requests
from urllib.parse import urljoin, urldefrag, urlparse
from collections import namedtuple
from queue import Queue, Empty
import time
import json
from pybloom_live import ScalableBloomFilter

SKIP_EXTENSIONS = {'.pdf', '.zip', '.gz', '.tar', '.jpg', '.jpeg', '.png', '.gif',
                   '.svg', '.mp4', '.mp3', '.wav', '.doc', '.docx', '.xls', '.xlsx',
                   '.ppt', '.pptx', '.exe', '.dmg', '.iso', '.bin', '.7z', '.rar'}

CrawlItem = namedtuple('CrawlItem', ['url', 'parent_url', 'depth'])

# --- BeautifulSoup demo ---

html_doc = """
<html><head><title>The Dormouse's story</title></head>
<body>
<p class="title test1"><b>The Dormouse's story</b></p>

<p class="story">Once upon a time there were three little sisters; and their names were
<a href="http://example.com/elsie" class="sister" id="link1">Elsie</a>,
<a href="http://example.com/lacie" class="sister" id="link2">Lacie</a> and
<a href="http://example.com/tillie" class="sister" id="link3">Tillie</a>;
and they lived at the bottom of a well.</p>

<p class="story">...</p>
"""

soup = BeautifulSoup(html_doc, 'html.parser')
print("hello world")
print(soup.prettify())

print("===============================================")
print(soup.title)
print(soup.title.name)
print(soup.title.string)
print(soup.title.parent.name)
print(soup.p)
print(soup.p['class'])
print(soup.a)
print(soup.b)
print(soup.find_all('a'))
print(soup.find(id="link3"))

# --- Crawler ---

class ProCrawler:
    def __init__(self, base_url, max_threads=5, delay=1.0, max_pages=50, max_depth=None, output_file="scraped_data.jsonl"):
        self.base_url = base_url
        self.max_threads = max_threads
        self.delay = delay
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.output_file = output_file

        self.queue = Queue()
        self.queue.put(CrawlItem(base_url, None, 0))
        # Option 1: Set-based dedup (simple, exact, higher memory)
        # self.visited = set()

        # Option 2: Bloom filter dedup (memory-efficient, ~0.1% false positive rate)
        self.visited = ScalableBloomFilter(
            initial_capacity=10000,
            error_rate=0.001
        )
        self.visited_count = 0

        self.data_lock = threading.Lock()
        self.print_lock = threading.Lock()
        self.rate_limit_lock = threading.Lock()
        self.file_lock = threading.Lock()

        self.stop_event = threading.Event()
        self.last_request_time = 0.0

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def safe_print(self, message):
        with self.print_lock:
            print(message)

    def enforce_rate_limit(self):
        with self.rate_limit_lock:
            current_time = time.time()
            wait_time = self.delay - (current_time - self.last_request_time)
            self.last_request_time = max(current_time, self.last_request_time + self.delay)

        if wait_time > 0:
            time.sleep(wait_time)

    def _extract_and_save(self, url, response, soup, parent_url, depth):
        """Extract page data, save to file, and return discovered links."""
        meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
        headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2'])]
        images = [{"src": img.get('src', ''), "alt": img.get('alt', '')} for img in soup.find_all('img') if img.get('src')]

        a_tags = soup.find_all('a', href=True)
        links = [urljoin(url, a['href']) for a in a_tags]

        data_packet = {
            "url": response.url,
            "title": soup.title.string.strip() if soup.title and soup.title.string else "No Title",
            "status_code": response.status_code,
            "content_type": response.headers.get('Content-Type', ''),
            "last_modified": response.headers.get('Last-Modified', ''),
            "etag": response.headers.get('ETag', ''),
            "meta_description": meta_desc_tag['content'].strip() if meta_desc_tag and meta_desc_tag.get('content') else "",
            "headings": headings,
            "full_text": soup.get_text(separator=' ', strip=True),
            "html": response.text,
            "images": images,
            "links": links,
            "parent_url": parent_url,
            "depth": depth,
            "scraped_at": time.time()
        }

        with self.file_lock:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data_packet, ensure_ascii=False) + '\n')

        return links

    def crawl(self):
        while not self.stop_event.is_set():
            try:
                item = self.queue.get(timeout=15)
                url, parent_url, depth = item.url, item.parent_url, item.depth
            except Empty:
                return

            with self.data_lock:
                if self.visited_count >= self.max_pages:
                    self.stop_event.set()
                    continue

                if url in self.visited:
                    continue

                self.visited.add(url)
                self.visited_count += 1
                count = self.visited_count

            self.safe_print(f"[{count}/{self.max_pages}] Crawling: {url}")
            self.process_url(url, parent_url, depth)

    @staticmethod
    def _should_skip_url(url):
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in SKIP_EXTENSIONS)

    def process_url(self, url, parent_url, depth):
        if self.stop_event.is_set():
            return

        self.enforce_rate_limit()

        try:
            response = self.session.get(url, timeout=10)

            # Dedup on final URL after redirects
            final_url = urldefrag(response.url).url
            if final_url != url:
                with self.data_lock:
                    if final_url in self.visited:
                        return
                    self.visited.add(final_url)

            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                self.safe_print(f"Skipping non-HTML ({content_type}): {url}")
                return

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = self._extract_and_save(url, response, soup, parent_url, depth)

                for link_url in links:
                    if self.stop_event.is_set():
                        break

                    clean_url = urldefrag(link_url).url
                    if self._should_skip_url(clean_url):
                        continue
                    if clean_url.startswith(self.base_url):
                        if self.max_depth is not None and depth + 1 > self.max_depth:
                            continue
                        with self.data_lock:
                            if clean_url not in self.visited:
                                self.queue.put(CrawlItem(clean_url, url, depth + 1))
            else:
                self.safe_print(f"HTTP {response.status_code} on {url}")

        except requests.RequestException as e:
            self.safe_print(f"Error on {url}: {e}")

    def run(self):
        with open(self.output_file, 'w') as f:
            pass

        threads = []
        self.safe_print(f"Starting crawler. Target: {self.max_pages} pages max.")

        for _ in range(self.max_threads):
            t = threading.Thread(target=self.crawl)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        self.safe_print(f"Finished. Total pages visited: {self.visited_count}")
        self.safe_print(f"Data saved to {self.output_file}")

if __name__ == "__main__":
    crawler = ProCrawler("https://www.anthropic.com", max_threads=5, delay=0.5, max_pages=15, max_depth=3)
    crawler.run()
