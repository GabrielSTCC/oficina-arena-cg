# Créditos e fontes de assets

Uso **acadêmico** (Computação Gráfica). Respeite as licenças originais de cada site ao redistribuir ou reutilizar fora da disciplina.

## Mixamo ([mixamo.com](https://www.mixamo.com))

Animações dos robôs (walk, idle, kneel, danças), exportadas para clips de vértice `.npz` em:

- `assets/models/robo3_clips/`
- `assets/models/robo5_clips/`

O jogo carrega esses clips em `gfx/anim_clip.py` / `scene/robot_models.py` (root motion removido com `in_place`).

## Open3DModel / modelos de robôs

Malhas base dos personagens (ex.: Optimus / robôs low-poly) obtidas em repositórios de modelos 3D (incluindo **Open3DModel** e pastas locais `modelos3D/Robos` no ambiente de desenvolvimento).

No repositório público, o runtime usa sobretudo os **NPZ texturizados** sob `assets/models/robo*_clips/` (não é necessário baixar OBJs externos para jogar).

## Sketchfab ([sketchfab.com](https://www.sketchfab.com))

Referência / downloads usados na ambientação e props (conforme pastas do projeto):

| Pasta no repo | Uso |
|---------------|-----|
| `assets/gltf/Base2/` | Plataforma / base na grade |
| `assets/gltf/sci-fi_wall/` | Parede tipo “estante” |
| `assets/gltf/Minerios/{diamante,ouro,prata}/` | Minérios 3D |
| `assets/gltf/Moeda/euro/` | Moeda (vitória / HUD) |
| `assets/textures/` (chao, concreto, painéis, etc.) | Piso, hangar, materiais — parte gerada/ajustada no projeto a partir de referências industriais / Sketchfab |

Consulte a página de cada modelo no Sketchfab para licença (CC, download pessoal, etc.).

## Áudio

| Arquivo | Uso |
|---------|-----|
| `assets/audio/hiphop.mp3`, `salsa.mp3`, `opaganastar.mp3` | Música na tela de vitória (conforme dança) |
| `assets/audio/voice/robo3.mp3`, `robo5.mp3` | Fala na seleção de personagem |

Trilhas e falas de uso interno do trabalho; se forem de terceiros, mantenha a atribuição do autor original ao republicar.

## Código / lógica

- **OpenGL + GLFW + shaders:** implementados para a disciplina de CG.
- **IA / partida:** reuso adaptado do **Arena Bot (PP01)** em `world/core` e `world/ia` (sem a UI Pygame original).

## Ícones

`assets/icons/app_icon*.png` — ícone do aplicativo (tema Autobot / trabalho).
