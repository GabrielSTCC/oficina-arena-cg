# Sprint 2 — Protótipo

**Disciplina:** Computação Gráfica  
**Tema:** Oficina cosy da arena de mineração  
**Data:** novembro/2026 (entrega conjunta com Sprint 3)

## O que o protótipo já contém

- Projeto Python + OpenGL 3.3 + GLFW + PyGLM
- Galpão fechado (chão, paredes, teto) sobre grade 15×9
- Catálogo com 8 itens (bancada, cadeira, luminária, abajur, planta, minério, estante, base)
- Malhas OBJ exportadas via Blender (pipeline de export já concluído; assets em `assets/models`)
- Transformações: translação na grade, rotação (`Q`/`E`), escala (`+/-`)
- Fantasma de posicionamento (verde/vermelho)
- Shader Phong mínimo + luz direcional
- Três modos de câmera (planta, orbital, seguir)
- Reuso de `core/` + `ia/` do Arena Bot (sem Pygame)

## Escolhas estéticas

- Low-poly / caixas estilizadas (oficina cosy)
- Materiais: madeira, metal, fosco, minério
- Cores Alfa (azul) e Beta (vermelho)

## Diferenças em relação ao planejamento (Sprint 1)

- Malhas ainda são volumes simples (não detalhe artesanal); export Blender já feito nos assets finais
- Texturas PNG existem, mas o MVP prioriza Kd no Phong (flag de textura preparada)
- Entrega Sprint 2 atrasada; empacotada junto com a Sprint 3

## Como rodar

Ver [README.md](../README.md).
