# Convenções Blender → Oficina Arena

## Escala e origem

- 1 unidade Blender = 1 célula da grade (≈ 1 m visual)
- Origem no **centro da base** do objeto (pés no Y=0)
- Objeto cabe aproximadamente em XZ ∈ [-0.45, 0.45] salvo peças longas (estante)

## Export OBJ

1. Selecionar a malha
2. File → Export → Wavefront (.obj)
3. Opções:
   - Forward: **-Y Forward**
   - Up: **Z Up**
   - Include Normals: sim
   - Include UVs: sim
   - Triangulate Faces: sim
4. Salvar em `assets/models/<id>.obj` com o mesmo id do catálogo:
   `bancada`, `cadeira`, `luminaria`, `abajur`, `planta`, `minerio`, `estante`, `base`, `robo`

## Texturas

PNG low-res em `assets/textures/<id>.png` (opcional no MVP; Phong usa Kd sem textura se ausente).

## Batch

```bash
blender --background --python assets/blender/export_catalog.py
```

## Rig bípede mecânico (`create_robot_rig.py`)

Gera a Armature `Robot_Rig` (Root, Spine, Head, braços/pernas L/R), com **In Front**, origem nos **pés**, parent **Empty Groups** (`ARMATURE_NAME`) e **Assign rígido automático** (peso 1.0 no osso mais próximo — sem borracha).

1. Abra o `.blend` do robô; se houver várias meshes, junte com `Ctrl+J`.
2. Object Mode → selecione a Mesh.
3. Scripting → Text Editor → Open → `create_robot_rig.py` → **Run Script**.
4. Selecione `Robot_Rig` → **Pose Mode** → `R` para testar.
5. (Opcional) refine uma peça: Edit Mode → Assign manual no Vertex Group.
