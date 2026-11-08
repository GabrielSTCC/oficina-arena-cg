"""Mundo lógico: reuso do Arena Bot (core + ia) sem Pygame."""

from __future__ import annotations

import sys
from pathlib import Path

# Importações do PP01 usam `config`, `core`, `ia` na raiz do pacote.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
