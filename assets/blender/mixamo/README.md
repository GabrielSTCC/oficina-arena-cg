# Mixamo → Robo 3 (melhor vinculação)

O Mixamo **Auto-Rigger** gera um esqueleto humanoide + pesos (skinning) melhores que o Assign por proximidade.

## Arquivo pronto para upload

`robo3_mixamo_upload.fbx` — malha única, ~1,80 m de altura, sem armature antiga.

## Passos no Mixamo (precisa de conta Adobe)

1. Abra https://www.mixamo.com e faça **Log in**.
2. Clique em **Upload Character** / ícone de upload.
3. Envie `robo3_mixamo_upload.fbx`.
4. No Auto-Rigger, posicione os marcadores (queixo, pulsos, cotovelos, joelhos, virilha) no mecha o melhor possível → **Next** / **Finish**.
5. Teste uma animação (ex.: *Idle* ou *Walking*).
6. **Download**:
   - Format: **FBX**
   - Skin: **With Skin**
   - Frames: 30 (ou default)
7. Salve o arquivo baixado nesta pasta como `robo3_mixamo_rigged.fbx`.

## Importar de volta no Blender

```bash
blender --python import_mixamo_rig.py
```

Ou: File → Import → FBX → `robo3_mixamo_rigged.fbx`.

## Limitações

Mixamo foi feito para personagens humanoides. No mecha (Unicorn/Gundam) o Auto-Rigger **pode falhar** ou gerar pesos estranhos nas placas. Se falhar no upload, use o rig manual (`create_robot_rig.py`) e refine os Vertex Groups à mão.

## Controle WASD no Blender

Arquivo: `wasd_control.py` (usar com `robot3_mixamo_anims.blend`)

```bash
blender assets/blender/robot3_mixamo_anims.blend --python assets/blender/mixamo/wasd_control.py
```

Ou no Blender: Scripting → Open `wasd_control.py` → Run Script.

| Tecla | Ação |
|-------|------|
| W / S | Andar frente / trás |
| A / D | Virar |
| Shift | Correr |
| Esc | Sair do modo WASD |
