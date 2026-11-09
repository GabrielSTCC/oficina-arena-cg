# Entrega Sprint 3 — Versão prévia (SIGAA)

**Disciplina:** Computação Gráfica · **Professor:** Rafael Ivo  
**Equipe:** Gabriel Santos Teixeira (515128) · Eloi Teles de Morais Neto (514502)

## O que anexar no SIGAA

1. **Código-fonte** — recomendado no SIGAA: `dist/oficina-arena-sprint3-codigo-docs.zip` (~15 MiB; sem NPZ/glTF/texturas).  
   Há também `dist/oficina-arena-sprint3.zip` (~197 MiB, jogo completo) se o limite do SIGAA permitir.
2. **Documento PDF único:** `SPRINT3_VERSAO_PREVIA.pdf` — capa + relatório (na **raiz** do ZIP e em `docs/`).
3. **Link do repositório** (assets grandes / clone completo):  
   https://github.com/GabrielSTCC/oficina-arena-cg

No campo de observações do SIGAA, cole o link do GitHub e indique o PDF único.

## Conteúdo do ZIP

- `main.py`, `requirements.txt`, `README.md`
- Pacotes: `app/`, `gfx/`, `scene/`, `world/`, `audio/`
- `assets/` (se o tamanho couber no SIGAA; senão use o ZIP código+docs + clone)
- `docs/` (MD, screenshots, **SPRINT3_VERSAO_PREVIA.pdf**)
- `OficinaArena.desktop`, `launch-oficina-arena.sh`

**Não inclui:** `.venv/`, `.git/`, `__pycache__/`.

## Como rodar (monitor / colegas)

```bash
git clone https://github.com/GabrielSTCC/oficina-arena-cg.git
cd oficina-arena-cg
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Requisitos: Python 3.11+, OpenGL 3.3+.

## Documentos de texto desta entrega

| Arquivo | Uso |
|---------|-----|
| `SPRINT3_VERSAO_PREVIA.pdf` | **Entregável** (capa + Sprint 3) |
| `SPRINT3_PREVIA.md` | Fonte editável do relatório |
| `CAPA_SPRINT3.md` | Fonte editável da capa |
| `SPRINT2_PROTOTIPO.md` | Protótipo (contexto) |
| `AMBIENTE_VISUAL.md`, `LOGICA_DO_JOGO.md`, `GUIA_ESTUDO.md` | Material de apoio |
| `CREDITOS_ASSETS.md` | Mixamo, Sketchfab, etc. |
| `docs/screenshots/` | Capturas da demonstração |

Não há vídeo nesta prévia; o roteiro ao monitor está no PDF/MD (seção 4).
