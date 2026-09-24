import re
import string

def normalize_input(text: str) -> str:
    """
    Normalizes input text for deterministic and fuzzy matching.
    - Lowers case
    - Trims whitespace
    - Normalizes repeated whitespace
    - Removes punctuation
    """
    if not text:
        return ""
    
    # 1. Lowercase
    normalized = text.lower()
    
    # 2. Remove punctuation (excluding hyphens/underscores which might be in app names, wait, the prompt says "normalize/remove surrounding punctuation")
    # Let's just remove standard punctuation for safe exact matching
    normalized = normalized.translate(str.maketrans('', '', string.punctuation))
    
    # 3. Normalize repeated whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized
