import base64
import json
import os
from pathlib import Path
import subprocess
import struct
import tempfile

import runpod


def handler(job):
    try:
        payload = job["input"]
        width = int(payload["width"])
        height = int(payload["height"])
        samples = int(payload["samples"])
        scene = base64.b64decode(payload["scene"], validate=True)
    except (KeyError, TypeError, ValueError):
        return {"error": "Invalid render input"}
    if not (256 <= width <= 1920 and 256 <= height <= 1920 and 1 <= samples <= 512):
        return {"error": "Invalid render dimensions or samples"}

    if not 20 <= len(scene) <= 6_750_000 or scene[:4] != b"glTF":
        return {"error": "Invalid GLB scene"}
    version, length, json_length = struct.unpack_from("<III", scene, 4)
    if version != 2 or length != len(scene) or scene[16:20] != b"JSON" or json_length > length-20:
        return {"error": "Invalid GLB header"}
    try:
        document = json.loads(scene[20:20+json_length])
        if any("uri" in item for key in ("buffers", "images") for item in document.get(key, [])):
            return {"error": "GLB must contain all buffers and images"}
    except (ValueError, TypeError, AttributeError):
        return {"error": "Invalid GLB document"}

    with tempfile.TemporaryDirectory(prefix="rig-render-") as work:
        input_file = Path(work) / "scene.glb"
        output_file = Path(work) / "frame.jpg"
        input_file.write_bytes(scene)
        command = [
            os.environ.get("BLENDER_BIN", "/opt/blender/blender"),
            "--background", "--factory-startup", "--disable-autoexec",
            "--python-exit-code", "1", "--python", str(Path(__file__).with_name("render.py")),
            "--", str(input_file), str(output_file), str(width), str(height), str(samples), "OPTIX",
        ]
        try:
            subprocess.run(command, check=True, timeout=1000)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return {"error": "Cycles GPU render failed. Check worker logs."}
        return {"jpeg": base64.b64encode(output_file.read_bytes()).decode("ascii")}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
