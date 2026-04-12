import logging
import os
import re
import time
from typing import Dict, Optional, List
import io
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

PDF_MAX_PAGES = int(os.getenv("PDF_MAX_PAGES", "30"))
PDF_PREFER_FAST = os.getenv("PDF_PREFER_FAST", "True").lower() == "true"
MIN_TEXT_CHARS_FOR_FAST_OK = 80
LARGE_PDF_SKIP_PLUMBER_BYTES = int(os.getenv("LARGE_PDF_SKIP_PLUMBER_MB", "12")) * 1024 * 1024


def _count_embedded_images_pypdf(reader, pages_to_read: int) -> int:
    """Best-effort count of /Image XObjects on the first N pages."""
    n = 0
    limit = min(len(reader.pages), max(0, pages_to_read))
    for i in range(limit):
        try:
            page = reader.pages[i]
            resources = page.get("/Resources")
            if resources is None:
                continue
            get_obj = getattr(resources, "get_object", None)
            if callable(get_obj):
                resources = get_obj()
            if not resources:
                continue
            xobjects = resources.get("/XObject")
            if xobjects is None:
                continue
            get_x = getattr(xobjects, "get_object", None)
            if callable(get_x):
                xobjects = get_x()
            for key in xobjects:
                try:
                    obj = xobjects[key]
                    if hasattr(obj, "get_object"):
                        obj = obj.get_object()
                    if obj.get("/Subtype") == "/Image":
                        n += 1
                except Exception:
                    continue
        except Exception:
            continue
    return n


class PDFProcessor:
    def __init__(self):
        self._pdfplumber_available = True
        self._pypdf_available = True
        
        try:
            import pdfplumber
        except ImportError:
            self._pdfplumber_available = False
            logger.warning("pdfplumber not available")
        
        try:
            import pypdf
        except ImportError:
            self._pypdf_available = False
            logger.warning("pypdf not available")
    
    def extract_text(self, pdf_file) -> Dict[str, any]:
        if not self._pdfplumber_available and not self._pypdf_available:
            return {
                'success': False,
                'error': 'No PDF library available. Install pdfplumber or pypdf.',
                'text': '',
                'pages': 0
            }
        
        try:
            file_size = getattr(pdf_file, "size", 0) or 0
            if PDF_PREFER_FAST and self._pypdf_available:
                fast = self._extract_with_pypdf(pdf_file)
                text_ok = fast.get("success") and len((fast.get("text") or "").strip()) >= MIN_TEXT_CHARS_FOR_FAST_OK
                if file_size >= LARGE_PDF_SKIP_PLUMBER_BYTES:
                    if not text_ok:
                        logger.info("Large PDF: skipping pdfplumber fallback.")
                    return fast
                if text_ok:
                    return fast
                if self._pdfplumber_available:
                    logger.info("Fast PDF path returned little text; retrying with pdfplumber.")
                    return self._extract_with_pdfplumber(pdf_file)
                return fast

            if self._pdfplumber_available:
                return self._extract_with_pdfplumber(pdf_file)
            return self._extract_with_pypdf(pdf_file)

        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'pages': 0
            }
    
    def _extract_with_pdfplumber(self, pdf_file) -> Dict[str, any]:
        import pdfplumber
        
        text_parts = []
        page_count = 0
        
        if hasattr(pdf_file, 'read'):
            pdf_file.seek(0)
            pdf_bytes = pdf_file.read()
            pdf_file.seek(0)
        else:
            pdf_bytes = pdf_file
        
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_count = len(pdf.pages)
                pages_to_read = min(page_count, PDF_MAX_PAGES) if PDF_MAX_PAGES > 0 else page_count
                metadata = self._extract_metadata_pdfplumber(pdf)

                embedded_img = 0
                for page in pdf.pages[:pages_to_read]:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    try:
                        embedded_img += len(page.images or [])
                    except Exception:
                        pass

            combined_text = '\n\n'.join(text_parts)

            return {
                'success': True,
                'text': combined_text,
                'pages': page_count,
                'pages_extracted': pages_to_read,
                'embedded_image_objects': embedded_img,
                'metadata': metadata,
            }
        except Exception as e:
            logger.error(f"pdfplumber extraction error: {e}")
            return {
                'success': False,
                'error': f'PDF extraction failed: {str(e)}',
                'text': '',
                'pages': 0
            }
    
    def _extract_with_pypdf(self, pdf_file) -> Dict[str, any]:
        from pypdf import PdfReader
        
        if hasattr(pdf_file, 'read'):
            pdf_file.seek(0)
            pdf_bytes = pdf_file.read()
            pdf_file.seek(0)
        else:
            pdf_bytes = pdf_file
        
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            page_count = len(reader.pages)
            pages_to_read = min(page_count, PDF_MAX_PAGES) if PDF_MAX_PAGES > 0 else page_count

            text_parts = []

            for page in reader.pages[:pages_to_read]:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            combined_text = '\n\n'.join(text_parts)

            embedded_images = _count_embedded_images_pypdf(reader, pages_to_read)
            
            metadata = {}
            if reader.metadata:
                metadata = {
                    'title': reader.metadata.get('/Title', ''),
                    'author': reader.metadata.get('/Author', ''),
                    'subject': reader.metadata.get('/Subject', ''),
                    'creator': reader.metadata.get('/Creator', ''),
                }
            
            return {
                'success': True,
                'text': combined_text,
                'pages': page_count,
                'pages_extracted': pages_to_read,
                'embedded_image_objects': embedded_images,
                'metadata': metadata
            }
        except Exception as e:
            logger.error(f"pypdf extraction error: {e}")
            return {
                'success': False,
                'error': f'PDF extraction failed: {str(e)}',
                'text': '',
                'pages': 0
            }
    
    def _extract_metadata_pdfplumber(self, pdf) -> Dict[str, any]:
        metadata = {}
        try:
            if hasattr(pdf, 'metadata') and pdf.metadata:
                metadata = {
                    'title': pdf.metadata.get('Title', ''),
                    'author': pdf.metadata.get('Author', ''),
                    'subject': pdf.metadata.get('Subject', ''),
                    'creator': pdf.metadata.get('Creator', ''),
                    'producer': pdf.metadata.get('Producer', ''),
                }
        except:
            pass
        return metadata
    
    def extract_title_from_pdf(self, text: str) -> str:
        """Extract title from PDF text - improved algorithm."""
        lines = text.split('\n')
        lines = [l.strip() for l in lines if l.strip()]
        
        skip_patterns = [
            'abstract', 'introduction', 'figure', 'table', 'doi', 'copyright',
            '©', 'journal', 'conference', 'proceeding', 'volume', 'issue',
            'page', 'pp.', 'isbn', 'issn', 'http', 'www', 'email', 'arxiv'
        ]
        
        for line in lines[:15]:
            line_clean = re.sub(r'^\d+\.?\s*', '', line)
            line_clean = line_clean.strip()
            
            if 10 < len(line_clean) < 250:
                if not any(skip in line_clean.lower() for skip in skip_patterns):
                    if not line_clean.startswith(('http', 'www', '#', '1.', '2.', '3.')):
                        words = line_clean.split()
                        if len(words) >= 2:
                            return line_clean
        
        for line in lines[:20]:
            line_clean = line.strip()
            if 15 < len(line_clean) < 200:
                if not any(c in line_clean.lower() for c in ['abstract', 'keywords', 'doi']):
                    return line_clean
        
        return "Untitled Document"
    
    def extract_images(self, pdf_file, max_images: int = 30) -> List[Dict[str, any]]:
        """Extract and save images from PDF files."""
        extracted_images = []
        
        if not self._pdfplumber_available:
            logger.warning("pdfplumber not available for image extraction")
            return extracted_images
        
        try:
            import pdfplumber
            
            if hasattr(pdf_file, 'read'):
                pdf_file.seek(0)
                pdf_bytes = pdf_file.read()
                pdf_file.seek(0)
            else:
                pdf_bytes = pdf_file
            
            images_dir = Path(settings.MEDIA_ROOT) / 'extracted_images'
            images_dir.mkdir(parents=True, exist_ok=True)
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_limit = min(len(pdf.pages), PDF_MAX_PAGES if PDF_MAX_PAGES > 0 else len(pdf.pages), 15)
                
                for page_num in range(page_limit):
                    if len(extracted_images) >= max_images:
                        break
                    
                    page = pdf.pages[page_num]
                    
                    try:
                        page_images = page.images or []
                        if not page_images:
                            # Try alternative: extract from page objects
                            try:
                                page_objs = page.objects
                                if page_objs and 'image' in page_objs:
                                    page_images = page_objs.get('image', [])
                            except:
                                pass
                        
                        if not page_images:
                            continue
                        
                        for img_num, img in enumerate(page_images):
                            if len(extracted_images) >= max_images:
                                break
                            
                            try:
                                # Handle different image formats
                                if isinstance(img, dict):
                                    x0 = max(0, img.get('x0', 0))
                                    top = max(0, img.get('top', 0))
                                    x1 = img.get('x1', page.width)
                                    bottom = img.get('bottom', page.height)
                                else:
                                    continue
                                
                                if x1 <= x0 or bottom <= top:
                                    continue
                                
                                width = x1 - x0
                                height = bottom - top
                                
                                # Lower threshold for small but valid images
                                if width < 30 or height < 30:
                                    continue
                                
                                crop_box = (x0, top, x1, bottom)
                                cropped_image = page.crop(crop_box).to_image(resolution=150)
                                
                                timestamp = int(time.time() * 1000000 + page_num * 1000 + img_num)
                                filename = f"page{page_num+1}_img{img_num}_{timestamp}.png"
                                filepath = images_dir / filename
                                
                                cropped_image.save(str(filepath), 'PNG')
                                
                                file_size = os.path.getsize(filepath)
                                # Lower threshold from 3000 to 1000 bytes
                                if file_size > 1000:
                                    extracted_images.append({
                                        'filename': filename,
                                        'path': str(filepath),
                                        'url': f"{settings.MEDIA_URL}extracted_images/{filename}",
                                        'page': page_num + 1,
                                        'width': int(width),
                                        'height': int(height),
                                        'size': file_size
                                    })
                                else:
                                    try:
                                        os.remove(filepath)
                                    except:
                                        pass
                            
                            except Exception as e:
                                logger.warning(f"Failed to extract image {img_num} from page {page_num+1}: {e}")
                                continue
                    
                    except Exception as e:
                        logger.warning(f"Error processing page {page_num+1} for images: {e}")
                        continue
            
            logger.info(f"Extracted {len(extracted_images)} images from PDF")
            return extracted_images
        
        except ImportError as e:
            logger.warning(f"Required library not available for image extraction: {e}")
            return extracted_images
        except Exception as e:
            logger.error(f"Error extracting images from PDF: {e}")
            return extracted_images
    
    def extract_tables(self, pdf_file) -> List[Dict[str, any]]:
        """Extract tables from PDF files."""
        extracted_tables = []
        
        if not self._pdfplumber_available:
            logger.warning("pdfplumber not available for table extraction")
            return extracted_tables
        
        try:
            import pdfplumber
            
            if hasattr(pdf_file, 'read'):
                pdf_file.seek(0)
                pdf_bytes = pdf_file.read()
                pdf_file.seek(0)
            else:
                pdf_bytes = pdf_file
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_limit = min(len(pdf.pages), PDF_MAX_PAGES if PDF_MAX_PAGES > 0 else len(pdf.pages), 15)
                
                for page_num in range(page_limit):
                    page = pdf.pages[page_num]
                    
                    try:
                        # Primary: extract_tables() method
                        tables = page.extract_tables()
                        if tables:
                            for table_idx, table in enumerate(tables):
                                if table and len(table) > 0:
                                    row_count = len(table)
                                    col_count = len(table[0]) if table else 0
                                    extracted_tables.append({
                                        'page': page_num + 1,
                                        'table_index': table_idx,
                                        'rows': row_count,
                                        'columns': col_count,
                                        'has_data': any(any(cell for cell in row) for row in table)
                                    })
                        
                        # Fallback: detect table-like structures in text
                        if not tables:
                            try:
                                text = page.extract_text()
                                if text:
                                    # Look for tabular text patterns
                                    lines = text.split('\n')
                                    for line in lines:
                                        # Count pipes or tabs (markdown/structured tables)
                                        if '|' in line and line.count('|') >= 2:
                                            extracted_tables.append({
                                                'page': page_num + 1,
                                                'table_index': 0,
                                                'rows': 1,
                                                'columns': line.count('|') + 1,
                                                'has_data': True,
                                                'detection': 'text_pattern'
                                            })
                                            break
                            except:
                                pass
                    except Exception as e:
                        logger.warning(f"Error extracting tables from page {page_num+1}: {e}")
                        continue
            
            logger.info(f"Extracted {len(extracted_tables)} tables from PDF")
            return extracted_tables
        
        except Exception as e:
            logger.error(f"Error extracting tables from PDF: {e}")
            return extracted_tables
    
    def detect_charts(self, pdf_file) -> List[Dict[str, any]]:
        """Detect charts and diagrams in PDF files."""
        detected_charts = []
        
        if not self._pdfplumber_available:
            return detected_charts
        
        try:
            import pdfplumber
            
            if hasattr(pdf_file, 'read'):
                pdf_file.seek(0)
                pdf_bytes = pdf_file.read()
                pdf_file.seek(0)
            else:
                pdf_bytes = pdf_file
            
            chart_keywords = [
                'figure', 'chart', 'graph', 'plot', 'diagram', 'fig.', ' fig ', 'fig ',
                'bar chart', 'bar graph', 'line graph', 'line chart', 'pie chart', 'pie graph',
                'scatter plot', 'scatter diagram', 'histogram', 'box plot', 'area chart',
                'axis', 'x-axis', 'y-axis', 'y axis', 'x axis', 'legend', 'data points',
                'flowchart', 'algorithm', 'network', 'architecture', 'framework'
            ]
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_limit = min(len(pdf.pages), PDF_MAX_PAGES if PDF_MAX_PAGES > 0 else len(pdf.pages), 15)
                
                for page_num in range(page_limit):
                    page = pdf.pages[page_num]
                    page_text = page.extract_text() or ''
                    page_text_lower = page_text.lower()
                    
                    found_chart = False
                    chart_type = None
                    detection_method = 'text'
                    
                    # Method 1: Keyword search in text
                    for keyword in chart_keywords:
                        if keyword in page_text_lower:
                            found_chart = True
                            detection_method = 'text'
                            if 'bar' in keyword:
                                chart_type = 'Bar Chart/Graph'
                            elif 'line' in keyword:
                                chart_type = 'Line Graph'
                            elif 'pie' in keyword:
                                chart_type = 'Pie Chart'
                            elif 'scatter' in keyword:
                                chart_type = 'Scatter Plot'
                            elif 'histogram' in keyword:
                                chart_type = 'Histogram'
                            elif 'box plot' in keyword:
                                chart_type = 'Box Plot'
                            elif 'area' in keyword:
                                chart_type = 'Area Chart'
                            elif 'flowchart' in keyword:
                                chart_type = 'Flowchart'
                            elif 'algorithm' in keyword:
                                chart_type = 'Algorithm'
                            elif 'network' in keyword:
                                chart_type = 'Network Diagram'
                            elif 'architecture' in keyword or 'framework' in keyword:
                                chart_type = 'Architecture Diagram'
                            elif 'fig' in keyword:
                                chart_type = 'Figure/Diagram'
                            break
                    
                    # Method 2: Visual detection (if not found by keywords)
                    if not found_chart:
                        try:
                            page_objs = page.objects or {}
                            curves = page_objs.get('curves', [])
                            lines = page_objs.get('lines', [])
                            rects = page_objs.get('rects', [])
                            
                            # More sensitive detection - charts often have many lines/curves
                            if (len(curves) > 3 or len(lines) > 8 or len(rects) > 15):
                                found_chart = True
                                detection_method = 'visual'
                                chart_type = 'Visual Chart/Diagram'
                        except:
                            pass
                    
                    # Method 3: Look for table-like content (tables are often near charts)
                    if not found_chart:
                        try:
                            tables = page.extract_tables()
                            if tables and len(tables) > 0:
                                found_chart = True
                                chart_type = 'Table Data'
                                detection_method = 'table'
                        except:
                            pass
                    
                    if found_chart:
                        detected_charts.append({
                            'page': page_num + 1,
                            'type': chart_type or 'Chart/Diagram',
                            'detection_method': detection_method
                        })
            
            logger.info(f"Detected {len(detected_charts)} charts/diagrams in PDF")
            return detected_charts
        
        except Exception as e:
            logger.error(f"Error detecting charts in PDF: {e}")
            return detected_charts
    
    def detect_paper_standard(self, text: str) -> str:
        """Detect paper standard (IEEE, ACM, APA, etc.)"""
        text_lower = text.lower()
        
        standards = {
            'IEEE': ['ieee', 'conference on', 'transactions on'],
            'ACM': ['acm', 'association for computing machinery', 'sigchi', 'sigmod'],
            'APA': ['apa style', 'american psychological association', 'doi:'],
            'MLA': ['mla style', 'modern language association'],
            'Chicago': ['chicago style', 'chicago manual of style'],
            'Harvard': ['harvard style', 'harvard reference'],
            'Nature': ['nature', 'nature publishing'],
            'Science': ['science', 'sciencemag'],
            'Elsevier': ['elsevier', 'procedia', 'journal of'],
            'Springer': ['springer', 'lecture notes', 'computer science']
        }
        
        for standard, keywords in standards.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return standard
        
        return "Academic Standard"


pdf_processor = PDFProcessor()
