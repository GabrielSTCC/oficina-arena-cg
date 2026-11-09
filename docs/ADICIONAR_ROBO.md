# Como adicionar um robô

O jogo lista personagens a partir de pastas `assets/models/<key>_clips/` registradas em `scene/robot_models.py`.

## 1. Preparar os clips

Crie `assets/models/<key>_clips/` (exemplo: `robo7_clips`) com:

| Arquivo | Obrigatório | Função |
|---------|-------------|--------|
| `walk.npz` | sim | Locomoção |
| `idle.npz` | recomendado | Parado (senão reusa walk) |
| `kneel.npz` | opcional | Ajoelhar na base |
| `dance1.npz`, `dance2.npz` | opcional | Vitória |
| `textures/` | sim se o NPZ referenciar | Albedo/normal do modelo |

Os `.npz` são animações por vértice (pipeline Mixamo → export OpenGL). Sem o Blender no repo, use um conjunto já exportado no mesmo formato dos `robo3`/`robo5`.

## 2. Registrar no código

Em `scene/robot_models.py`:

1. Inclua a chave e o nome em `load_robot_models`:

```python
for key, nome in (("robo3", "Robo 3"), ("robo5", "Robo 5"), ("robo7", "Robo 7")):
```

2. Se tiver danças, mapeie música em `_DANCES`:

```python
"robo7": [("dance1", "hiphop"), ("dance2", "salsa")],
```

3. Coloque os MP3 correspondentes em `assets/audio/<chave_musica>.mp3` (ex.: `hiphop.mp3`).

## 3. Fala na seleção (opcional)

Salve `assets/audio/voice/<key>.mp3` (ex.: `robo7.mp3`).  
A seleção toca `assets/audio/voice/{model.key}.mp3` automaticamente.

## 4. Testar

```bash
python main.py
```

Menu → Iniciar → tela de seleção deve listar o novo nome; ← → troca o destaque e a fala; confirmar aplica o modelo em Alfa (e o “outro” em Beta).

## Observações

- Alfa usa o robô escolhido; Beta usa o **outro** índice da lista (ciclo).
- Hotkeys de OBJ externos (`T` / 5–8) são debug e **não** entram no fluxo normal com clips NPZ.
- Músicas de dança: ver `DanceEntry.music_path` → `assets/audio/{music_key}.mp3`.
