import sys

import bpy
from mathutils import Vector

source, output, width, height, samples, device = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=source)
scene = bpy.context.scene
for obj in scene.objects:
    if obj.type == "MESH" and (obj.get("rigCameraHidden") or obj.name.startswith("Потолок")):
        obj.visible_camera = False
camera = next((obj for obj in scene.objects if obj.type == "CAMERA"), None)
if camera is None:
    raise RuntimeError("Scene has no render camera")
scene.camera = camera
scene.render.engine = "CYCLES"
if device != "CPU":
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = device
    preferences.refresh_devices()
    gpus = [gpu for gpu in preferences.devices if gpu.type == device]
    if not gpus:
        raise RuntimeError(f"No {device} GPU available")
    for gpu in preferences.devices:
        gpu.use = gpu.type == device
    scene.cycles.device = "GPU"
scene.cycles.samples = int(samples)
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.015
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.diffuse_bounces = 4
scene.render.resolution_x = int(width)
scene.render.resolution_y = int(height)
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 92
scene.render.filepath = output
scene.world = bpy.data.worlds.new("Blackout")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
floors = [obj for obj in scene.objects if obj.type == "MESH" and obj.name.startswith("Плита")]
if floors:
    bounds = [obj.matrix_world @ Vector(corner) for obj in floors for corner in obj.bound_box]
    x_min, x_max = min(p.x for p in bounds), max(p.x for p in bounds)
    y_min, y_max = min(p.y for p in bounds), max(p.y for p in bounds)
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x_min+x_max)/2, (y_min+y_max)/2, 1.5))
    haze = bpy.context.object
    haze.name = "Rig Grid haze"
    haze.dimensions = (x_max-x_min, y_max-y_min, 3.0)
    fog = bpy.data.materials.new("Stage haze")
    fog.use_nodes = True
    nodes = fog.node_tree.nodes
    nodes.clear()
    output_node = nodes.new("ShaderNodeOutputMaterial")
    scatter = nodes.new("ShaderNodeVolumeScatter")
    scatter.inputs["Density"].default_value = 0.035
    scatter.inputs["Anisotropy"].default_value = 0.25
    fog.node_tree.links.new(scatter.outputs["Volume"], output_node.inputs["Volume"])
    haze.data.materials.append(fog)
bpy.ops.render.render(write_still=True)
