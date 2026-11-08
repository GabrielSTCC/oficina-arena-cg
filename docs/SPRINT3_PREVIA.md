# Sprint 3 — Versão prévia

**Disciplina:** Computação Gráfica  
**Tema:** Oficina cosy da arena de mineração  
**Data:** 05–07/11/2026

## Evolução desde o protótipo

- Luzes pontuais ligadas a luminárias/abajures colocados no cenário
- Bridge `WorldBridge`: objetos da cena influenciam paredes/minérios da partida
- Simulação Alfa/Beta (`P`/`Espaço`) com turnos visuais; câmera 3 segue o robô (`Tab`)
- Agentes Cursor (`.cursor/rules/`) por critério de avaliação + `AGENTS.md`
- Documentação de export Blender e pacote de entrega

## Funcionalidades demonstráveis ao monitor

1. Abrir a oficina 3D e orbitar / ver em planta
2. Escolher item do catálogo, ver fantasma, colocar (verde) ou bloquear (vermelho)
3. Colocar luminária e perceber pontual; materiais distintos sob Phong
4. Iniciar simulação e ver robôs andando com A*/Minimax/BC do PP01
5. Pausar, editar de novo, reiniciar (`R`)

## Defeitos e dificuldades

| Item | Situação |
|------|----------|
| Malhas ainda boxy | Aceitável low-poly; falta modelagem artesanal no Blender |
| Texturas pouco usadas no shader | Uniform preparado; prioridade foi Phong + Kd |
| Picking em câmera planta | Ray no plano Y=0; em ângulos extremos pode falhar |
| Sprint 2 não enviada no prazo 15/10 | Conteúdo absorvido nesta prévia |
| Integração cena→arena | Só paredes/minérios do catálogo; armadilhas ainda vêm da geração IA se o usuário não personalizar tudo |

## Próximos passos (Sprint Final 01/12)

- Modelar peças mais legíveis no Blender (cadeira/luminária reconhecíveis)
- Ativar texturas madeira/metal no fragment shader
- Polir animação entre células e feedback de coleta
- Vídeo de demonstração + zip SIGAA
