import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class URLScraper:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def scrape(self, url: str) -> Dict[str, any]:
        try:
            if not self._is_valid_url(url):
                raise ValueError(f"Invalid URL format: {url}")
            
            # Special handling for Google Scholar (requires different approach)
            if 'scholar.google' in url.lower():
                return self._handle_google_scholar(url)
            
            # Special handling for YouTube videos
            if 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
                return self._handle_youtube(url)
            
            # Special handling for ResearchGate
            if 'researchgate.net' in url.lower():
                return self._handle_researchgate(url)
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            # Allow HTML, XHTML, PDF, and JSON (for research paper APIs)
            supported_types = ['text/html', 'application/xhtml', 'application/pdf', 'application/json', 'text/plain']
            is_supported = any(stype in content_type for stype in supported_types)
            
            if not is_supported and len(response.content) < 1000:
                return {
                    'success': False,
                    'error': 'Unsupported source. This URL does not contain readable content. Supported sources: Research papers (arXiv, ResearchGate), Academic blogs, News articles, and HTML webpages.',
                    'url': url
                }
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            for script in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                script.decompose()
            
            title = self._extract_title(soup)
            main_content = self._extract_main_content(soup)
            text_content = self._clean_text(main_content)
            
            if len(text_content) < 100:
                text_content = self._fallback_extraction(soup)
            
            return {
                'success': True,
                'url': url,
                'title': title,
                'content': text_content,
                'raw_html': str(soup),
                'links': self._extract_links(soup, url),
                'metadata': self._extract_metadata(soup),
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while scraping: {url}")
            return {'success': False, 'error': 'Request timed out. The page took too long to load. Please try another source or check the URL.', 'url': url}
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for: {url}")
            return {'success': False, 'error': 'Could not connect to the URL. Please verify the link is correct. Supported sources: arXiv, ResearchGate, academic blogs, and HTML webpages.', 'url': url}
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for: {url}")
            if e.response.status_code == 404:
                return {'success': False, 'error': 'Page not found (404). Please check the URL and try again.', 'url': url}
            elif e.response.status_code == 403:
                host = urlparse(url).netloc
                return {
                    'success': False,
                    'error': f'Access denied (403) from {host}. This site may require registration or have scraping protection. Try: 1) Accessing directly in browser, 2) Using a different source (arXiv, ResearchGate), 3) Uploading the PDF directly.',
                    'url': url
                }
            elif e.response.status_code == 429:
                return {'success': False, 'error': 'Too many requests (429). The server rate-limited us. Please wait a moment and try again.', 'url': url}
            else:
                return {'success': False, 'error': f'HTTP Error {e.response.status_code}. Unable to fetch the page.', 'url': url}
        
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {'success': False, 'error': f'Error accessing URL: {str(e)}. Supported sources: arXiv, research blogs, academic sites, and HTML pages. Please verify the URL is correct.', 'url': url}
    
    def _is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        if soup.title:
            return soup.title.string.strip() if soup.title.string else ""
        
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        return ""
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        # Try to find main content area while PRESERVING paragraph formatting
        article = soup.find('article')
        if article:
            # Use \n\n as separator to preserve paragraph breaks for better extraction
            return article.get_text(separator='\n\n', strip=True)
        
        main = soup.find('main')
        if main:
            return main.get_text(separator='\n\n', strip=True)
        
        content_div = soup.find('div', class_=re.compile(r'content|article|post|entry|main|text|body', re.I))
        if content_div:
            return content_div.get_text(separator='\n\n', strip=True)
        
        # Fallback: preserve paragraph structure in full text
        all_text = soup.get_text(separator='\n\n', strip=True)
        return all_text
    
    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()
    
    def _fallback_extraction(self, soup: BeautifulSoup) -> str:
        paragraphs = soup.find_all('p')
        text_parts = []
        
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50:
                text_parts.append(text)
        
        return '\n\n'.join(text_parts) if text_parts else soup.get_text(separator=' ', strip=True)
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        links = []
        seen = set()
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            if href.startswith(('javascript:', 'mailto:', 'tel:')):
                continue
            
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"
            
            if clean_url not in seen and len(clean_url) < 500:
                links.append(clean_url)
                seen.add(clean_url)
        
        return links[:50]
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        metadata = {}
        
        meta_tags = {
            'description': ['description', 'og:description'],
            'author': ['author', 'article:author'],
            'published_time': ['article:published_time'],
            'keywords': ['keywords'],
        }
        
        for key, names in meta_tags.items():
            for name in names:
                tag = soup.find('meta', attrs={'name': name}) or soup.find('meta', attrs={'property': name})
                if tag and tag.get('content'):
                    metadata[key] = tag['content'].strip()
                    break
        
        return metadata
    
    # ----------------------------------------------------------------------
    # Special handlers for protected/academic sources
    # ----------------------------------------------------------------------
    def _handle_google_scholar(self, url: str) -> Dict[str, any]:
        """Try to handle Google Scholar with special approach."""
        try:
            # Use more complete headers for Scholar
            scholar_headers = self.headers.copy()
            scholar_headers['Referer'] = 'https://www.google.com/'
            
            response = requests.get(url, headers=scholar_headers, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract the search results or article info
            results = []
            for result in soup.find_all('div', class_='gs_ri'):
                text = result.get_text()
                if len(text) > 20:
                    results.append(text)
            
            if results:
                content = '\n\n'.join(results[:10])
            else:
                content = soup.get_text()
            
            if len(content.strip()) < 100:
                return {
                    'success': False,
                    'error': 'Google Scholar limits automated access. Please: 1) Copy the article title and search within the app, 2) Use arXiv or ResearchGate links directly, or 3) Upload the PDF file.',
                    'url': url
                }
            
            return {
                'success': True,
                'url': url,
                'title': 'Google Scholar Search Results',
                'content': content[:5000],
                'metadata': {},
                'links': [],
            }
        except Exception as e:
            logger.warning(f"Google Scholar scraping failed: {e}")
            return {
                'success': False,
                'error': 'Cannot access Google Scholar content due to access restrictions. Please try: 1) Using the article DOI directly, 2) Accessing through ResearchGate or arXiv, or 3) Uploading as PDF.',
                'url': url
            }
    
    def _handle_researchgate(self, url: str) -> Dict[str, any]:
        """Handle ResearchGate with special approach."""
        try:
            rg_headers = self.headers.copy()
            rg_headers['Referer'] = 'https://www.researchgate.net/'
            
            response = requests.get(url, headers=rg_headers, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Try to extract publication metadata
            title = self._extract_title(soup)
            
            # Try to find abstract or description
            content_parts = []
            
            # Look for abstract
            abstract_elem = soup.find('div', class_=re.compile(r'abstract', re.I))
            if abstract_elem:
                content_parts.append(abstract_elem.get_text())
            
            # Look for publication info
            pub_info = soup.find('div', class_=re.compile(r'publication|document', re.I))
            if pub_info:
                content_parts.append(pub_info.get_text())
            
            # Fallback: general content
            if not content_parts:
                content_parts.append(soup.get_text(separator='\n', strip=True)[:3000])
            
            content = '\n\n'.join(content_parts)
            
            if len(content.strip()) < 100:
                return {
                    'success': False,
                    'error': 'ResearchGate requires login for full content. You can: 1) Create a free ResearchGate account, 2) Request the PDF from the author, or 3) Upload the PDF directly to our analyzer.',
                    'url': url
                }
            
            return {
                'success': True,
                'url': url,
                'title': title or 'ResearchGate Publication',
                'content': content[:5000],
                'metadata': self._extract_metadata(soup),
                'links': [],
            }
        except Exception as e:
            logger.warning(f"ResearchGate scraping failed: {e}")
            return {
                'success': False,
                'error': 'Cannot fully access ResearchGate content. Please: 1) Upload the PDF directly, 2) Use an arXiv or DOI link, or 3) Request the publication from the author.',
                'url': url
            }
    
    def _handle_youtube(self, url: str) -> Dict[str, any]:
        """Handle YouTube video URLs - extract transcript and video info."""
        try:
            try:
                import yt_dlp
                
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    if not info:
                        return {'success': False, 'error': 'Could not extract video information', 'url': url}
                    
                    title = info.get('title', 'YouTube Video')
                    description = info.get('description', '')
                    transcript = ''
                    
                    try:
                        subtitles = info.get('subtitles') or info.get('automatic_captions')
                        if subtitles:
                            for lang, subs in subtitles.items():
                                if lang == 'en' or lang.startswith('en'):
                                    for sub in subs:
                                        if 'data' in sub:
                                            transcript += sub['data'] + ' '
                                    break
                    except Exception:
                        pass
                    
                    if not transcript and description:
                        transcript = description
                    
                    content = f"Video Title: {title}\n\n"
                    if description:
                        content += f"Description: {description}\n\n"
                    if transcript:
                        content += f"Transcript: {transcript}"
                    
                    if len(content.strip()) < 100:
                        return {
                            'success': False,
                            'error': 'Could not extract transcript from this YouTube video. The video may not have subtitles available.',
                            'url': url
                        }
                    
                    return {
                        'success': True,
                        'url': url,
                        'title': title,
                        'content': content[:50000],
                        'metadata': {
                            'duration': info.get('duration'),
                            'uploader': info.get('uploader'),
                            'upload_date': info.get('upload_date'),
                            'view_count': info.get('view_count'),
                            'like_count': info.get('like_count'),
                        },
                        'links': [url],
                    }
                    
            except ImportError:
                response = requests.get(url, headers=self.headers, timeout=self.timeout, allow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'lxml')
                title = self._extract_title(soup)
                
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                description = meta_desc['content'] if meta_desc and meta_desc.get('content') else ''
                
                content = f"Video Title: {title}\n\nDescription: {description}"
                
                if len(content.strip()) < 100:
                    return {
                        'success': False,
                        'error': 'YouTube video analysis requires yt-dlp library for transcript extraction. Please install: pip install yt-dlp',
                        'url': url
                    }
                
                return {
                    'success': True,
                    'url': url,
                    'title': title,
                    'content': content,
                    'metadata': {},
                    'links': [url],
                }
                
        except Exception as e:
            logger.warning(f"YouTube scraping failed: {e}")
            return {
                'success': False,
                'error': f'Could not analyze YouTube video: {str(e)}. Please try uploading the paper as PDF.',
                'url': url
            }


url_scraper = URLScraper()
