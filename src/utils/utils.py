
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

import re

def clean_text(text: str) -> str:
    return text.strip().replace('\xa0', ' ') if text else ""


def parse_money(text: str) -> int:
    # Removes all non-digit characters and parses as int
    if text:
        return int(re.sub(r"[^\d]", "", text))
    return 0
