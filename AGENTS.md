# Agentes Cursor — Oficina Arena (CG)

Cada regra em `.cursor/rules/` tem **um dever**. Use o rule picker / @-mention da regra ao trabalhar naquela frente.

| Agente | Arquivo | Dever |
|--------|---------|--------|
| Scaffold | `cg-scaffold.mdc` | Estrutura POO, GLFW, deps; sem Pygame |
| Blender | `cg-blender.mdc` | Convenções e export OBJ/PNG |
| Modelagem | `cg-modelagem.mdc` | MeshLoader, catálogo, T/R/S, placeholders |
| Câmera | `cg-camera.mdc` | Planta / orbital / seguir robô |
| Iluminação | `cg-iluminacao.mdc` | Phong GLSL, materiais, luzes |
| Interação | `cg-interacao.mdc` | Input, fantasma verde/vermelho |
| Integração IA | `cg-integracao-ia.mdc` | Bridge grade ↔ `world/core`+`ia` |
| Entrega | `cg-entrega.mdc` | Docs Sprint 2/3, SIGAA, vídeo |

**Paralelismo sugerido:** Blender ∥ scaffold/câmera/shaders → loader+catálogo → bridge → docs.

**Fora de escopo dos agentes:** melhorar Minimax/A* do PP01; portar UI Pygame; sprint final 01/12.
