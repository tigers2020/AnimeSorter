import re
from guessit import guessit
from rapidfuzz import process, fuzz
from typing import List

# 1. 서수/품질 토큰 정규식
ORDINAL = re.compile(r'\b\d+(?:st|nd|rd|th)\b', re.I)
QUALITY = re.compile(r'\b(?:TV|WEB[- ]?DL|BDRip|BluRay|ReRip|OVA|Film|Theatrical|Special)\b', re.I)

# 2. 정제 함수

def clean_title(raw: str) -> str:
    """서수/품질 토큰 제거 및 정제"""
    txt = ORDINAL.sub('', raw)
    txt = QUALITY.sub('', txt)
    txt = re.sub(r'\s{2,}', ' ', txt)
    return txt.strip().title()

# 3. GuessIt + 정제

def guess_and_clean(filename: str) -> dict:
    meta = guessit(filename, {'type': 'episode'})
    title = meta.get('title', '')
    clean = clean_title(title)
    meta['clean_title'] = clean
    return meta

# 4. Fuzzy match (후보군은 TMDB 등 외부에서 받아온다고 가정)
def fuzzy_match_title(clean_title: str, candidates: List[str]) -> str:
    if not candidates:
        return clean_title
    match, score, _ = process.extractOne(clean_title, candidates, scorer=fuzz.ratio)
    return match if score >= 80 else clean_title 