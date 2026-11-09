# Sprint 3 — Versão prévia

**Disciplina:** Computação Gráfica  
**Professor:** Rafael Ivo  
**Instituição:** Universidade Federal do Ceará — Campus de Russas  
**Curso:** Ciência da Computação  
**Entrega:** Sprint 3 — Versão prévia  
**Data:** 09 de novembro de 2026  

**Tema:** Oficina cosy da arena de mineração  

**Equipe (2 integrantes)**

| Nome | Matrícula |
|------|-----------|
| Gabriel Santos Teixeira | 515128 |
| Eloi Teles de Morais Neto | 514502 |

---

## 1. Resumo da entrega

A Sprint 3 pede a **versão prévia** do trabalho: evolução do protótipo (Sprint 2), com mais funcionalidades prontas para demonstração ao monitor, e indicação explícita de **defeitos e dificuldades**.

| Entrega | Papel |
|---------|--------|
| Sprint 1 (24/09) | Planejamento textual do tema e das ferramentas |
| Sprint 2 (15/10) | Protótipo — primeiras implementações OpenGL |
| **Sprint 3 (05/11)** | **Versão prévia — evolução demonstrável** |
| Sprint Final (01/12) | Aplicação completa + apresentação ao professor |

A Sprint 2 não foi enviada no prazo original; o conteúdo do protótipo foi absorvido e ampliado nesta versão prévia. O que falta para a Sprint Final (01/12) está listado na seção 9.

---

## 2. Evolução desde o protótipo

Em relação ao protótipo (galpão 15x9, catálogo, Phong básico, 3 câmeras e bridge com a IA do PP01), a versão prévia acrescenta:

### 2.1 Fluxo de jogo e menus

- Menu principal (Jogar / Configurações / Sair)
- Seleção de robô (Robo 3 e Robo 5 / Optimus) com vitrine 3D
- Escolha de modo: COMxCOM, P1xCOM, P1xP2
- Moeda 3D (cara/coroa) para definir quem começa
- Configuração da partida: tamanho da grade, paredes, armadilhas, bateria, rounds e quantidade por tipo de minério
- HUD com placar, bateria, carga e controles de janela (minimizar / maximizar / fechar)

### 2.2 Ambiente visual

- Hangar fechado com piso, paredes, teto, janela e mureta da arena
- Texturas (madeira, metal, painéis, hazard, minérios) e materiais Phong distintos
- Luz direcional (janela) + pontuais ligadas a luminárias/abajures
- Pós-processamento (bloom / tonemapping) e paredes holográficas conectadas na grade

### 2.3 Robôs e animação

- Clips Mixamo texturizados: walk, idle, kneel, dance1, dance2
- Robo 3 e Robo 5 com texturas próprias; danças do Robo 3 reexportadas com os mesmos materiais do walk
- Na vitória do round: robô vencedor dança no centro; música correspondente (salsa / hiphop / opaganastar)
- Sorteio de dança sem repetir a última; empate sem dança

### 2.4 Integração com a lógica de IA (PP01)

- `WorldBridge` sincroniza cena com `world/core` + `world/ia` (A*, Minimax alfa-beta, base de conhecimento)
- Se o minério-alvo some (outro robô coletou) e não há minério útil, o agente limpa a rota antiga e volta à base
- Minérios, paredes e bases da cena influenciam a arena da partida

### 2.5 Atalhos de janela

- Alt+F4 fechar, Alt+F9 minimizar, Alt+F10 maximizar/restaurar
- Ícones equivalentes no canto superior direito do HUD
- Ícone do aplicativo (atalho `.desktop` + ícone da janela GLFW)

Detalhes técnicos do ambiente: [AMBIENTE_VISUAL.md](AMBIENTE_VISUAL.md).  
Fluxo de telas e regras: [LOGICA_DO_JOGO.md](LOGICA_DO_JOGO.md).

---

## 2.6 Do planejamento (Sprint 1) → na aplicação

| Planejado / escolha estética | Já na aplicação | Onde |
|------------------------------|-----------------|------|
| Galpão fechado, grade 15×9 | Hangar + piso da arena | `scene/environment.py`, `workshop.py` |
| Catálogo ~8 itens (bancada, cadeira, luminária, abajur, planta, minério, estante, base) | Catálogo completo com T/R/S | `scene/catalog.py` |
| Fantasma verde/vermelho; Q/E; +/− | Posicionamento na grade | `scene/placeable.py`, `app/application.py` |
| 3 câmeras (planta / orbital / seguir) | Modos 1/2/3 + mouse | `gfx/camera.py` |
| Phong; luz direcional (janela) + pontuais | Shaders + luminárias/abajur | `gfx/shaders/phong.*`, hangar |
| Materiais madeira / metal / fosco / minério + texturas | PNG em `assets/textures/` | `gfx/mesh.py` (`Material`) |
| Estética low-poly / cosy | Mantida (oficina, não hiper-realismo) | cena + materiais |
| Reuso IA Arena Bot (A*, Minimax, BC) | Partida sincronizada com a cena | `world/core`, `world/ia`, `world/bridge.py` |

---

## 2.7 Modificações em relação ao planejamento e ao protótipo

O **tema** permanece o mesmo (oficina cosy da arena de mineração). Mudanças são incrementais:

| Antes (planejamento / protótipo) | Agora (versão prévia) |
|----------------------------------|------------------------|
| Ênfase em teclado; menu gráfico “simples” | Tutorial + menus/HUD (Pillow→textura GL), volume, ícones de janela |
| Galpão com volumes mais simples | Hangar com painéis, hazard, janela e pós-processo (ainda ambiente fechado) |
| Robôs placeholder / pouca animação | Robo 3 e Robo 5 com clips Mixamo (walk/idle/kneel/dança) |
| Sem fluxo de partida “de jogo” completo na UI | Seleção de robô, modos, moeda 3D, vitória com dança/música |
| Grade fixa 15×9 no planejamento | Configurável (até 28×17) + quantidades de minério/paredes/armadilhas |
| Sprint 2 atrasada | Conteúdo do protótipo absorvido e ampliado nesta prévia |

Áudio usa `pygame.mixer` apenas como auxiliar (enunciado permite efeitos sonoros; o render continua só em OpenGL).

---

## 3. Atendimento aos critérios do enunciado

| Critério (enunciado) | Peso | Situação na versão prévia |
|----------------------|------|---------------------------|
| Modelagem e transformações | 2,5 | Ambiente fechado; catálogo com pelo menos 8 itens; T/R/S na grade; fantasma de posicionamento |
| Visualização e câmera | 1,5 | Planta (ortográfica), orbital (perspectiva) e seguir robô; mouse/teclado |
| Iluminação e materiais | 2,5 | Phong; luz direcional + pontuais; materiais madeira/metal/fosco/minério + texturas |
| Interação | 2,0 | Catálogo, fantasma verde/vermelho, menus, moeda, config, seleção de robô |
| Desenvolvimento e criatividade | 1,5 | POO (`app/`, `gfx/`, `scene/`, `world/`); tema oficina + robôs do PP01; sprints documentadas |

**Fora de escopo (respeitado):** sem física complexa; menus são HUD/teclado simples; estética low-poly / estilizada.

---

## 4. Funcionalidades demonstráveis ao monitor

Roteiro sugerido (~5–8 min):

1. Abrir a aplicação e mostrar o hangar (câmera orbital / planta / seguir).
2. Em **Configurações**, alterar tamanho da arena e quantidades de minério; voltar.
3. **Jogar** -> escolher Robo 3 ou Robo 5 na vitrine -> modo COM x COM -> moeda.
4. Iniciar a partida (`P` / Espaço): robôs andam com A*/Minimax/BC; placar e bateria no HUD.
5. Colocar luminária/abajur e observar luz pontual; colocar parede/minério e ver efeito na grade.
6. Ao fim de um round com vencedor: dança no centro + música; Enter continua.
7. Mostrar atalhos/ícones de minimizar, maximizar e fechar.

---

## 5. Como executar

Ver [README.md](../README.md) e [ENTREGA_SPRINT3.md](ENTREGA_SPRINT3.md).

```bash
git clone https://github.com/GabrielSTCC/oficina-arena-cg.git
cd oficina-arena-cg
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Atalho de aplicativo (Linux): `OficinaArena.desktop` (ícone em `assets/icons/app_icon.png`).

Estados úteis para demo rápida:

```bash
python main.py --state robo      # seleção de robô
python main.py --state vitoria  # dança da vitória (Alfa)
```

**Repositório (assets / código completo):** https://github.com/GabrielSTCC/oficina-arena-cg

---

## 5.1 Atividades e dúvidas para o monitor

**Equipe:** Gabriel Santos Teixeira (515128) e Eloi Teles de Morais Neto (514502).

**Atividades feitas nesta prévia (resumo):** evolução visual do hangar; fluxo tutorial → menus → seleção → moeda → partida; animação Mixamo; integração IA; documentação e pacote SIGAA.

**Dúvidas / pontos a validar com o monitor:**

1. Decoração `LIVRE` aparece na cena mas não bloqueia a arena lógica — o robô “atravessa” a malha na simulação. Devemos bloquear na grade até a final?
2. Root motion das danças Mixamo: `make_in_place` ajuda, mas frames extremos ainda podem oscilar. Isso é aceitável na prévia?
3. Picking do fantasma no plano Y=0 falha em ângulos muito rasantes — priorizar correção agora ou na Sprint Final?

Roteiro de demonstração: seção 4.

---

## 6. Capturas de tela

Arquivos em `docs/screenshots/`:

| Arquivo | Conteúdo |
|---------|----------|
| `depois_orbital.png` | Câmera orbital no hangar |
| `depois_planta.png` | Visão de planta |
| `depois_seguir.png` | Câmera seguindo o robô |
| `selecao_robo.png` | Vitrine Robo 3 / Robo 5 |
| `vitoria_danca.png` | Dança da vitória |
| `shot_moeda_opt.png` | Moeda 3D |
| `shot_jogo_opt.png` / `partida_5_tipos.png` | Partida em andamento |
| `config_minerios.png` / `arena_config_28x17.png` | Menu de configurações |
| `arena_15x9.png` / `arena_28x17.png` | Grades diferentes |
| `robo_ajoelhado_base.png` | Pose ajoelhada na base |

---

## 7. Defeitos e dificuldades

| Item | Situação |
|------|----------|
| Sprint 2 fora do prazo 15/10 | Conteúdo absorvido nesta prévia; documentado para o monitor |
| Danças Mixamo com root motion | Export no blend texturizado + `make_in_place`; pose ainda pode oscilar em frames extremos |
| Malhas de decoração ainda simples | Low-poly aceitável; modelagem artesanal fica para a final |
| Decoração `LIVRE` na grade | Ocupa a cena mas não bloqueia a arena -> robô “atravessa” a malha na simulação |
| Áudio `opaganastar` | Arquivo original veio como AAC com extensão `.mp3`; reencodado para MP3 real |
| Picking em ângulos extremos | Ray no plano Y=0; em vistas muito rasantes pode falhar |

---

## 8. Organização do código

| Pacote | Papel |
|--------|--------|
| `app/` | Janela GLFW, input, fluxo de telas |
| `gfx/` | Shaders Phong, malhas, câmera, HUD, texturas, pós-processamento |
| `scene/` | Oficina, catálogo, placeables, atores (robô, moeda), modelos Mixamo |
| `world/` | `core` + `ia` do Arena Bot (partida, A*, Minimax, BC) |
| `audio/` | Música da dança de vitória (pygame.mixer) |
| `assets/` | Modelos OBJ/NPZ, glTF, texturas, áudio, ícones |

---

## 9. Próximos passos (Sprint Final — 01/12)

- Polir modelagem das peças do catálogo (cadeira/luminária mais legíveis)
- Revisar animações Mixamo (idle/dança) e feedback visual de coleta
- Vídeo de demonstração + pacote de código no SIGAA
- Apresentação final (no máximo 15 min; ambos os membros apresentam)

---

## 10. Originalidade

- **Reutilizado do PP01 (IA):** grade, agentes Alfa/Beta, A* (Manhattan), Minimax com poda alfa-beta, base de conhecimento de coleta/descarga.
- **Desenvolvido para CG:** cena OpenGL 3.3, shaders Phong, câmeras, materiais/texturas, interação de organização, menus/HUD, animação Mixamo e integração visual.
- A UI 2D em Pygame do trabalho de IA **não** faz parte desta disciplina.
- Malhas/texturas de material de referência do professor ou de outros trabalhos **não** foram copiadas como solução pronta.

---

## 11. Controles principais

| Tecla / ação | Efeito |
|--------------|--------|
| Mouse / clique | Catálogo, menus, fantasma, botões do HUD |
| C ou 1 / 2 / 3 | Câmera planta / orbital / seguir |
| P ou Espaço | Iniciar ou pausar a simulação |
| R | Reiniciar / nova série conforme o estado |
| Tab | Trocar robô da câmera “seguir” |
| Q / E, + / − | Rotação e escala do fantasma |
| Alt+F4 / F9 / F10 | Fechar / minimizar / maximizar janela |
| Esc | Voltar menu / cancelar fantasma |

Lista completa: [README.md](../README.md).

---

## 12. Conclusão

A versão prévia já permite demonstrar ambiente fechado customizável, câmeras, Phong com texturas e luzes, interação de catálogo, fluxo completo de partida com IA reutilizada e diferenciais (seleção de robô, dança/música da vitória, configuração de arena). Os pontos fracos listados na seção 7 orientam o que falta até a Sprint Final de 01/12.
