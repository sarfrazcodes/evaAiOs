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
    normalized = text.lower().strip()

    # Strip sentence-ending punctuation like '.', '!', '?'
    normalized = re.sub(r'[\.!?]+$', '', normalized).strip()
    
    # 2. Remove punctuation but preserve '.', '+', '-', '_' which occur in filenames and languages (e.g. dfs.cpp, c++)
    punct_to_remove = ''.join(c for c in string.punctuation if c not in {'.', '+', '_', '-'})
    normalized = normalized.translate(str.maketrans('', '', punct_to_remove))
    
    # 3. Normalize repeated whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized
