# Guia de estudo — o que foi implementado das aulas

Mapa rápido: **conceito da disciplina → onde está no código**. Use para revisar antes da apresentação ou para o grupo estudar o mesmo projeto.

## 1. Janela, contexto e loop

| Conceito | Onde |
|----------|------|
| OpenGL 3.3 core + GLFW | `app/application.py`, `main.py` |
| Clear, viewport, swap | loop de `Application.run` |
| Input teclado/mouse | callbacks GLFW no mesmo módulo |

## 2. Pipeline gráfico e Phong

| Conceito | Onde |
|----------|------|
| Vertex/fragment shaders | `gfx/shaders/phong.vert`, `phong.frag` |
| Compilar/ligar programa | `gfx/shader.py` |
| Material Kd/Ks, shininess, emissive | `gfx/mesh.py` (`Material`) |
| Luz direcional + pontuais do teto | uniforms em `application` / hangar |
| Textura + normal map + aniso | `gfx/texture.py`, amostragem no `phong.frag` |
| Pós-processo (bloom / ACES) | `gfx/postprocess.py`, `gfx/shaders/composite.frag` |
| Shadow map (profundidade) | `gfx/shadow_map.py`, `gfx/shaders/depth.*` |

Leitura visual do hangar: [AMBIENTE_VISUAL.md](AMBIENTE_VISUAL.md).

## 3. Câmera e transformações

| Conceito | Onde |
|----------|------|
| Look-at, perspectiva, órbita | `gfx/camera.py` |
| Modos planta / orbital / seguir | `CameraMode` + teclas 1/2/3 |
| T-R-S na grade (objeto / fantasma) | `scene/placeable.py`, `scene/workshop.py` |
| Matriz modelo + normal matrix | `draw_textured` em `placeable.py` |

## 4. Modelagem / cena

| Conceito | Onde |
|----------|------|
| Grade 15×9, ocupação | `scene/workshop.py`, `scene/catalog.py` |
| Hangar (piso, paredes, teto, mureta) | `scene/environment.py` |
| Catálogo cosy (bancada, base, minério…) | `scene/catalog.py` + OBJ/`assets/gltf` |
| Backface cull “dollhouse” | `GL_CULL_FACE` no draw do hangar |
| Z-fighting no piso | piso da arena ligeiramente acima do topo da plataforma (`environment.py`) |

## 5. Animação (Mixamo → GPU)

| Conceito | Onde |
|----------|------|
| Clip de vértices por frame (NPZ) | `gfx/anim_clip.py` |
| Walk / idle / kneel / dança | `scene/robot_models.py`, `scene/robot_actor.py` |
| Root motion removido (`in_place`) | `AnimClip.make_in_place` |
| Vitória: dança + música | estado `VITORIA` em `application.py` + `audio/music.py` |

## 6. HUD e UI 2D sem Pygame display

| Conceito | Onde |
|----------|------|
| Raster Pillow → textura OpenGL | `gfx/hud.py` |
| Menus, seleção de robô, placar | estados `AppState` |
| Ícones / volume | HUD + `audio.music.set_volume` |

## 7. Áudio auxiliar

| Conceito | Onde |
|----------|------|
| Música em loop (vitória) | `audio/music.py` (`pygame.mixer.music`) |
| Fala one-shot (seleção) | `audio/sfx.py` (`Sound` + canal) |

Permitido pelo enunciado como módulo auxiliar (não substitui OpenGL).

## 8. Inteligência Artificial (reuso PP01)

| Conceito | Onde |
|----------|------|
| Arena, agentes, partida | `world/core/` |
| A* / navegação / estratégia | `world/ia/` |
| Ponte CG ↔ simulação | `world/bridge.py` |

A tela 2D antiga em Pygame **não** faz parte deste trabalho de CG.

## Ordem sugerida de leitura

1. `main.py` → `app/application.py` (estados)
2. `gfx/camera.py` + `phong.frag`
3. `scene/environment.py` + `workshop.py`
4. `scene/robot_actor.py` + `anim_clip.py`
5. `world/bridge.py` (como a IA mexe nos atores)

Screenshots: `docs/screenshots/`.
