# Oficina Arena — Computação Gráfica

Ambiente 3D cosy (galpão 15×9) com catálogo de objetos, Phong, 3 câmeras e robôs Alfa/Beta reusando a IA do PP01 (Arena Bot).

## Requisitos

- Python 3.11+
- OpenGL 3.3+
- (Opcional) Blender 4/5 para reexportar malhas

```bash
cd Trabalho/oficina-arena
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Controles

| Tecla | Ação |
|-------|------|
| Setas / `[` `]` | Percorrer catálogo |
| Mouse | Mover fantasma na grade |
| Clique / Enter | Confirmar posição (fantasma verde) |
| Q / E | Rotacionar fantasma |
| + / - | Escala |
| Delete | Remover objeto na célula |
| Esc | Cancelar fantasma / sair |
| C ou 1/2/3 | Câmera planta / orbital / seguir |
| Botão direito + arrastar | Órbita |
| Scroll | Zoom |
| P / Espaço | Iniciar ou pausar simulação |
| R | Reiniciar partida a partir da cena |
| Tab | Trocar robô da câmera 3 |

## Blender

Ver [assets/blender/EXPORT.md](assets/blender/EXPORT.md).

```bash
blender --background --python assets/blender/export_catalog.py
```

## Estrutura

- `app/` — GLFW e input
- `gfx/` — shaders Phong, malhas, câmera
- `scene/` — galpão, catálogo, fantasma
- `world/` — `core` + `ia` do Arena Bot
- `assets/models` — OBJ; `assets/blender` — fontes `.blend`

## Docs de sprint

- [docs/SPRINT2_PROTOTIPO.md](docs/SPRINT2_PROTOTIPO.md)
- [docs/SPRINT3_PREVIA.md](docs/SPRINT3_PREVIA.md)
