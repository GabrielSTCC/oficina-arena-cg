# Ambiente Visual e Texturas — Oficina Arena (CG)

Resumo técnico das melhorias visuais implementadas no mapa 15×9 para a apresentação da disciplina de Computação Gráfica.

## 1. Arquitetura Fechada (Hangar Sci-Fi)

- **Plataforma elevada (`Y = 0`)** para a grade 15×9 com mureta metálica chanfrada, faixa de perigo (*hazard stripes*) no topo, filete neon ciano interno e postes nos quatro cantos.
- **Piso externo de concreto (`Y = -0.14`)** ocupando o salão 30×22 m (`WetConcrete` do warehouse reamostrado para 1024² + normal map).
- **Quatro paredes de painéis sci-fi + teto com vigas e luminárias emissivas**, fechando o ambiente conforme exigido no Critério 1 do trabalho.
- **Janela industrial luminosa na parede norte**, alinhada com a direção da luz direcional (`_DIR_LIGHT_DIR`), dando origem visual coerente à iluminação direcional prometida na Sprint 1.
- **Dollhouse Culling (`GL_CULL_FACE`):** as paredes e o teto do hangar têm normais voltadas para o interior; quando a câmera orbital recua para fora do salão, as paredes entre a câmera e a arena deixam de ser desenhadas automaticamente, sem bloquear a visão.

## 2. Texturas (`assets/textures/`)

Texturas tileáveis já geradas (histórico: script offline NumPy/PIL) em 512²–1024²:

| Textura | Técnica | Uso |
|---|---|---|
| `concreto.png` + `concreto_normal.png` | Reamostragem 1024² + ajuste tonal frio | Chão externo do hangar |
| `painel.png` + `painel_normal.png` + `painel_emissive.png` | SDF de placas chanfradas, rebites, grelha de ventilação, ruído `1/f` via FFT e derivadas Sobel com wrap (`np.roll`) | Paredes do hangar |
| `hazard.png` | Listras diagonais 45° periódicas + máscara de desgaste | Topo da mureta da arena |
| `armadilha.png` + `armadilha_emissive.png` + `armadilha_normal.png` | Moldura hazard + 5 fendas incandescentes com normal map | Células de armadilha (custo dobrado no A*) |
| `metal_escovado.png` | Ruído anisotrópico (box blur direcional com wrap) | Mureta, trilhos emissores, luminária |
| `madeira.png` | Anéis senoidais perturbados por ruído fractal + juntas de tábuas | Bancada e cadeira (material fosco) |
| `fosco.png` | Trama ortogonal de tecido | Planta e cúpula do abajur |
| `anel_base.png` / `brilho.png` (RGBA) | SDF radial com segmentos/chevrons e halo gaussiano | Decals das bases Alfa/Beta e minérios |

## 3. Conceitos do Cap. 4 e Cap. 5 no Shader (`phong.frag`)

1. **Propriedades de textura (`gfx/texture.py`):** `GL_REPEAT` / `GL_CLAMP_TO_EDGE`, mipmapping trilinear (`GL_LINEAR_MIPMAP_LINEAR`) e **filtro anisotrópico (`GL_TEXTURE_MAX_ANISOTROPY_EXT = 8x`)** para evitar borrado no piso em ângulos rasantes.
2. **Mapeamento em duas etapas — caixa/triplanar (`uTriplanarScale`):** projeta coordenadas de mundo no plano dominante da normal (superfície intermediária cúbica), evitando distorção em muretas e móveis escalados.
3. **Quebra de repetição por célula + grade tática (`uFloorMode = 1`):** cada célula `(x, z)` rotaciona seu UV em múltiplos de 90° a partir de um hash determinístico e desenha linhas de grade ciano com *antialiasing* via `fwidth`.
4. **Textura de dados `uCellMap` (15×9 `RGBA8` com filtro linear):**
   - Canal `R`: oclusão de ambiente por proximidade (*contact AO*) ao redor das paredes;
   - Canal `G`: halo avermelhado sob armadilhas;
   - Canais `B`/`A`: assinatura luminosa ciano (Base Alfa) e laranja (Base Beta).
5. **Iluminação ambiente hemisférica:** interpola entre `uGroundAmbient` e `uSkyAmbient` usando `N.y`, mantendo leitura de forma nas regiões em sombra.
6. **Pós-processamento (`composite.frag`):** bloom + curva de *tonemapping* **ACES** + leve vinheta.

## 4. Paredes Holográficas Conectadas (Auto-Tiling)

- `Workshop._wall_segments_and_isolates` detecta pares ortogonais adjacentes no conjunto lógico `PAREDE` e desenha **trilhos emissores contínuos** e **painéis holográficos conectados** entre centros de células vizinhas.
- Pilares metálicos verticais aparecem apenas em pontas soltas, cantos em L e junções T/X.
- O shader `hologram.frag` calcula a grelha e as linhas de scan em **coordenadas de mundo**, garantindo continuidade visual entre segmentos adjacentes.
