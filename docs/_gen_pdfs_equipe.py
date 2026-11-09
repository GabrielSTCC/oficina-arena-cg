#!/usr/bin/env python3
"""Gera CAPA_SPRINT3.pdf/png e SPRINT3_PREVIA.pdf a partir dos .md."""

from __future__ import annotations

import shutil
import unicodedata
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FAC = Path(__file__).resolve().parents[3] / "docs"


def ascii_fold(s: str) -> str:
    repl = {
        "—": "-",
        "–": "-",
        "•": "-",
        "×": "x",
        "α": "a",
        "β": "b",
        "→": "->",
        "≥": ">=",
        "≤": "<=",
        "…": "...",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "−": "-",
        "≈": "~",
        "²": "2",
        "³": "3",
        "°": "o",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def gen_capa_pdf() -> Path:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    left = 20.0
    pdf.set_left_margin(left)
    pdf.set_right_margin(left)

    def line(txt: str, *, size: int = 12, bold: bool = False, h: float = 8) -> None:
        pdf.set_x(left)
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.cell(0, h, txt, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(30)
    line("UNIVERSIDADE FEDERAL DO CEARA", size=14, bold=True)
    pdf.ln(4)
    line("CAMPUS DE RUSSAS", size=12)
    line("CURSO DE CIENCIA DA COMPUTACAO", size=12)
    pdf.ln(28)
    line("GABRIEL SANTOS TEIXEIRA  -  Matricula 515128", size=12, bold=True)
    line("ELOI TELES DE MORAIS NETO  -  Matricula 514502", size=12, bold=True)
    pdf.ln(36)
    line("OFICINA COSY DA ARENA DE MINERACAO", size=16, bold=True, h=9)
    pdf.ln(6)
    line("Versao previa (Sprint 3)", size=13)
    pdf.set_y(-45)
    line("RUSSAS", size=12)
    line("2026", size=12)
    out = ROOT / "CAPA_SPRINT3.pdf"
    pdf.output(out)
    return out


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    )
    roots = (
        Path("/usr/share/fonts/TTF"),
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/Adwaita"),
    )
    for root in roots:
        for name in names:
            p = root / name
            if p.is_file():
                try:
                    return ImageFont.truetype(str(p), size)
                except Exception:
                    pass
        for p in root.glob("*.ttf"):
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()


def gen_capa_png() -> Path:
    w, h = 1240, 1754
    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)

    def center(y: int, text: str, f: ImageFont.ImageFont) -> None:
        bbox = d.textbbox((0, 0), text, font=f)
        tw = bbox[2] - bbox[0]
        d.text(((w - tw) // 2, y), text, font=f, fill=(0, 0, 0))

    center(220, "UNIVERSIDADE FEDERAL DO CEARÁ", _font(36, True))
    center(280, "CAMPUS DE RUSSAS", _font(28))
    center(330, "CURSO DE CIÊNCIA DA COMPUTAÇÃO", _font(28))
    center(560, "GABRIEL SANTOS TEIXEIRA — Matrícula 515128", _font(26, True))
    center(620, "ELOI TELES DE MORAIS NETO — Matrícula 514502", _font(26, True))
    center(900, "OFICINA COSY DA ARENA DE MINERAÇÃO", _font(34, True))
    center(980, "Versão prévia (Sprint 3)", _font(28))
    center(1500, "RUSSAS", _font(28))
    center(1560, "2026", _font(28))
    out = ROOT / "CAPA_SPRINT3.png"
    img.save(out)
    return out


class Doc(FPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Sprint 3 - Versao previa | Oficina Arena", align="R")
        self.ln(10)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"{self.page_no()}", align="C")


def write_md(pdf: FPDF, text: str) -> None:
    left = pdf.l_margin

    def block(txt: str, *, size: int = 10, bold: bool = False, h: float = 5) -> None:
        pdf.set_x(left)
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.multi_cell(0, h, ascii_fold(txt))

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            pdf.ln(3)
            continue
        s = ascii_fold(line)
        if s.startswith("# "):
            pdf.ln(2)
            block(s[2:].strip(), size=16, bold=True, h=8)
            pdf.ln(2)
        elif s.startswith("## "):
            pdf.ln(3)
            block(s[3:].strip(), size=13, bold=True, h=7)
            pdf.ln(1)
        elif s.startswith("### "):
            pdf.ln(2)
            block(s[4:].strip(), size=11, bold=True, h=6)
        elif s.startswith("|") and "---" in s:
            continue
        elif s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            block(" | ".join(cells), size=9, h=5)
        elif s.startswith("- "):
            block("  - " + s[2:], size=10, h=5)
        else:
            block(s.replace("**", ""), size=10, h=5)


def _draw_capa_page(pdf: FPDF) -> None:
    left = 20.0
    pdf.set_left_margin(left)
    pdf.set_right_margin(left)

    def line(txt: str, *, size: int = 12, bold: bool = False, h: float = 8) -> None:
        pdf.set_x(left)
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.cell(0, h, txt, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(30)
    line("UNIVERSIDADE FEDERAL DO CEARA", size=14, bold=True)
    pdf.ln(4)
    line("CAMPUS DE RUSSAS", size=12)
    line("CURSO DE CIENCIA DA COMPUTACAO", size=12)
    pdf.ln(28)
    line("GABRIEL SANTOS TEIXEIRA  -  Matricula 515128", size=12, bold=True)
    line("ELOI TELES DE MORAIS NETO  -  Matricula 514502", size=12, bold=True)
    pdf.ln(36)
    line("OFICINA COSY DA ARENA DE MINERACAO", size=16, bold=True, h=9)
    pdf.ln(6)
    line("Versao previa (Sprint 3)", size=13)
    pdf.set_y(-45)
    line("RUSSAS", size=12)
    line("2026", size=12)


def gen_unified_pdf() -> Path:
    """Capa (pag. 1) + corpo SPRINT3_PREVIA.md — entregavel unico."""
    md = (ROOT / "SPRINT3_PREVIA.md").read_text(encoding="utf-8")
    doc = Doc(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=True, margin=18)
    doc.add_page()
    _draw_capa_page(doc)
    doc.add_page()
    doc.set_margins(18, 18, 18)
    write_md(doc, md)
    out = ROOT / "SPRINT3_VERSAO_PREVIA.pdf"
    doc.output(out)
    return out


def sync_faculty_previa_md() -> None:
    src = ROOT / "SPRINT3_PREVIA.md"
    dst = FAC / "SPRINT3_PREVIA.md"
    if FAC.is_dir():
        shutil.copy2(src, dst)


def main() -> None:
    print(gen_capa_png())
    print(gen_unified_pdf())
    # remove PDFs antigos separados (entregavel = unificado)
    for obsolete in ("CAPA_SPRINT3.pdf", "SPRINT3_PREVIA.pdf"):
        p = ROOT / obsolete
        if p.is_file():
            p.unlink()
            print("removed", p.name)
        fac_p = FAC / obsolete
        if fac_p.is_file():
            fac_p.unlink()
            print("removed faculty", obsolete)
    sync_faculty_previa_md()
    for name in (
        "SPRINT3_VERSAO_PREVIA.pdf",
        "CAPA_SPRINT3.png",
        "CAPA_SPRINT3.md",
        "SPRINT3_PREVIA.md",
        "ENTREGA_SPRINT3.md",
    ):
        src = ROOT / name
        if src.is_file() and FAC.is_dir():
            shutil.copy2(src, FAC / name)
            print("copied", name)


if __name__ == "__main__":
    main()
