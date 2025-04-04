import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin
from typing import List, Dict, Optional, Any
import logging

def get_links_from_support_page(base_url: str) -> List[str]:
    """
    Extract all links from the Angel One support page that start with the support URL pattern
    """
    logging.info(f"Fetching links from {base_url}")
    
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all anchor tags
        all_links = soup.find_all('a', href=True)
        
        # Filter links that start with the support URL pattern
        support_links = []
        for link in all_links:
            href = link['href']
            # Convert relative URLs to absolute URLs
            full_url = urljoin(base_url, href)
            
            # Check if the URL matches our pattern
            if full_url.startswith('https://www.angelone.in/support/'):
                support_links.append(full_url)
        
        # Remove duplicates
        support_links = list(set(support_links))
        
        logging.info(f"Found {len(support_links)} support links")
        return support_links
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching the support page: {e}")
        return []

def extract_text_with_spacing(element) -> str:
    """
    Extract text from an element while preserving spacing better than get_text()
    """
    # This approach preserves more natural spacing between text elements
    texts = []
    for item in element.recursiveChildGenerator():
        if isinstance(item, str):
            text = item.strip()
            if text:
                texts.append(text)
        # Add spaces between certain elements
        elif item.name in ['p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            texts.append('\n')
    
    # Join with spaces and clean up any double spaces or extra newlines
    text = ' '.join(texts)
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with one
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Keep max double newlines
    return text.strip()

def sanitize_text(text: str) -> str:
    """
    Clean and sanitize text to remove any problematic characters
    """
    if not text:
        return ""
    
    # Remove or replace problematic Unicode characters
    # Replace rightward arrow and similar characters with plain text alternatives
    text = text.replace('\u2192', '->') 
    
    # Replace other common Unicode characters that might cause issues
    replacements = {
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote
        '\u201c': '"',  # Left double quote
        '\u201d': '"',  # Right double quote
        '\u2013': '-',  # En dash
        '\u2014': '--', # Em dash
        '\u2026': '...', # Ellipsis
        '\u00a0': ' ',  # Non-breaking space
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    return text

def extract_sidebar_faq(url: str) -> Dict[str, Any]:
    """
    Extract data from the sidebar FAQ section of a given URL
    """
    logging.info(f"Processing {url}")
    
    try:
        # Add a delay to avoid overwhelming the server
        time.sleep(1)
        
        # Set explicit encoding handling in the request
        response = requests.get(url)
        response.encoding = 'utf-8'  # Force UTF-8 encoding for the response
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the sidebar FAQ section
        sidebar_faq = soup.select_one('section.sidebar-faq-section')
        
        if sidebar_faq:
            # Extract the content with better formatting preservation and sanitize it
            formatted_text = extract_text_with_spacing(sidebar_faq)
            sanitized_text = sanitize_text(formatted_text)
            
            # Also extract structured data if possible
            faq_items = []
            questions = sidebar_faq.select('.faq-item .question, .faq-item h3, .faq-question')
            answers = sidebar_faq.select('.faq-item .answer, .faq-item p, .faq-answer')
            
            # If we have matching Q&A pairs
            if len(questions) == len(answers) and len(questions) > 0:
                for i in range(len(questions)):
                    faq_items.append({
                        'question': sanitize_text(extract_text_with_spacing(questions[i])),
                        'answer': sanitize_text(extract_text_with_spacing(answers[i]))
                    })
            
            return {
                'url': url,
                'content': sanitized_text,
                'faq_items': faq_items,
                'success': True
            }
        else:
            logging.warning(f"No sidebar FAQ section found at {url}")
            return {
                'url': url,
                'content': None,
                'faq_items': [],
                'success': False
            }
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Error processing {url}: {str(e)}")
        return {
            'url': url,
            'error': str(e),
            'content': None,
            'faq_items': [],
            'success': False
        }

def scrape_and_prepare_faqs(base_url: str = 'https://www.angelone.in/support/') -> List[Dict[str, Any]]:
    """
    Scrape FAQs from Angel One support pages and prepare them for indexing
    """
    # Get all support links
    support_links = get_links_from_support_page(base_url)
    
    # Extract sidebar FAQ data from each link
    results = []
    for url in support_links:
        result = extract_sidebar_faq(url)
        if result['success'] and result['content']:
            results.append(result)
    
    return results
