"""PARDES layer detection for content metadata auto-tagging."""
from enum import Enum

class PardesLayer(str, Enum):
    """PARDES content layers (fractal structure)."""
    SEED = "seed"           # One sentence that generates the whole
    PARAGRAPH = "paragraph" # 3-5 sentences, napkin-ready  
    PAGE = "page"           # Single printable page
    DOCUMENT = "document"   # 1-3 pages executive summary
    SYSTEM = "system"       # Full document with all detail

def detect_pardes_layer(body: str) -> PardesLayer:
    """Detect PARDES layer based on content length."""
    # Split by sentences (rough heuristic)
    sentences = [s.strip() for s in body.replace('!', '.').replace('?', '.').split('.') if s.strip()]
    word_count = len(body.split())
    
    if len(sentences) <= 1 or word_count < 25:
        return PardesLayer.SEED
    elif len(sentences) <= 5 or word_count < 150:
        return PardesLayer.PARAGRAPH
    elif word_count < 800:
        return PardesLayer.PAGE
    elif word_count < 2500:
        return PardesLayer.DOCUMENT
    else:
        return PardesLayer.SYSTEM
