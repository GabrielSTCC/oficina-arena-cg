# Oficina Arena — Computação Gráfica

Ambiente 3D (galpão / hangar sci-fi, grade **15×9**) com catálogo de objetos, iluminação **Phong**, três câmeras, menus/HUD, robôs animados (Mixamo) e reuso da **IA do Arena Bot** (PP01): A*, estratégia e partida.

Disciplina: **Computação Gráfica** (UFC Russas) · stack: **Python + OpenGL 3.3 + GLFW + PyGLM**.

## Como rodar

Requisitos: **Python 3.11+**, driver com **OpenGL 3.3+**, Linux/Windows/macOS.

```bash
git clone https://github.com/GabrielSTCC/oficina-arena-cg.git
cd oficina-arena-cg
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Atalho Linux (opcional): `OficinaArena.desktop` + `launch-oficina-arena.sh` (ajuste o caminho `Exec=` se necessário).

## Controles (resumo)

| Contexto | Ação |
|----------|------|
| Menu | Clique / Enter confirma; Esc volta |
| Volume | Slider no menu principal |
| Seleção de robô | ← → ou clique; confirma / volta |
| Em jogo — catálogo | Setas / `[` `]` ; mouse move o fantasma |
| Colocar / rotacionar / escala | Clique·Enter · Q/E · +/- |
| Câmera | `1` planta · `2` orbital · `3` seguir · botão direito órbita · scroll zoom |
| Partida | P / Espaço pausa · R reinicia · Tab troca robô da câmera 3 |
| Janela | Alt+F4 fecha · F9/F10 (atalhos de janela do projeto) · F12 screenshot |

Detalhes de lógica: [docs/LOGICA_DO_JOGO.md](docs/LOGICA_DO_JOGO.md).

## Estrutura

```text
app/           # Loop GLFW, estados (menu, seleção, jogo, vitória)
gfx/           # Shaders Phong/HUD, malhas, texturas, câmera, clips NPZ
scene/         # Hangar, oficina, catálogo, robôs, moeda
world/         # core + ia do Arena Bot (sem UI Pygame)
audio/         # Música (vitória) e fala (seleção) via pygame.mixer
assets/
  models/      # OBJ catálogo + robo3_clips / robo5_clips (NPZ)
  gltf/        # Base, parede sci-fi, minérios, moeda (embutidos no repo)
  textures/    # Piso, painéis, hazard, materiais
  audio/       # MP3 dança + voice/
  icons/       # Ícone da janela
docs/          # Guias de estudo, sprints, screenshots
```

## Documentação para estudar

| Doc | Conteúdo |
|-----|----------|
| [docs/GUIA_ESTUDO.md](docs/GUIA_ESTUDO.md) | Mapa **aula → código** (Phong, câmera, texturas, animação, IA…) |
| [docs/CREDITOS_ASSETS.md](docs/CREDITOS_ASSETS.md) | Mixamo, Open3DModel, Sketchfab e demais fontes |
| [docs/ADICIONAR_ROBO.md](docs/ADICIONAR_ROBO.md) | Como incluir um novo robô no jogo |
| [docs/AMBIENTE_VISUAL.md](docs/AMBIENTE_VISUAL.md) | Hangar, texturas, shader |
| [docs/SPRINT2_PROTOTIPO.md](docs/SPRINT2_PROTOTIPO.md) / [SPRINT3_PREVIA.md](docs/SPRINT3_PREVIA.md) | Entregas de sprint |

## Conformidade com o enunciado

- **Gráficos:** só OpenGL moderno (3.3 core), janela/input com **GLFW**.
- **Auxiliares permitidos:** Pillow (HUD/texturas), NumPy, PyGLM, **pygame.mixer** só para áudio (não substitui o render).

## Licença / uso

Trabalho acadêmico. Assets de terceiros mantêm as licenças originais — ver [docs/CREDITOS_ASSETS.md](docs/CREDITOS_ASSETS.md).
