# from camera.pipelines.allCam import ALL_CAM_PIPELINE
# from camera.pipelines.SpatialDepth import BASIC_DEPTH_PIPELINE
import importlib
import json
from pathlib import Path

custom_pipeline_config = {}
AVAILABLE_PIPELINES={}
CUSTOM_CONFIG_DIR = Path("config")

local_config = CUSTOM_CONFIG_DIR / "custom_pipelines.json"
default_config = CUSTOM_CONFIG_DIR / "custom_pipelines.default.json"

CUSTOM_PIPELINE_DIR = "config/"
config_path = local_config if local_config.exists() else default_config

print(f"Loading pipelines configuration found at: {config_path}")

with open(config_path) as f:
    custom_pipeline_config = json.load(f)

def load_depthai_pipeline(import_path):
    module_path, object_name = import_path.rsplit(".", 1)

    module = importlib.import_module(module_path)
    return getattr(module, object_name)




for key, import_path in custom_pipeline_config.items():
    try:
        pipeline = load_depthai_pipeline(import_path)
        AVAILABLE_PIPELINES[pipeline.name] = pipeline
        print(f"Pipline loaded: {pipeline.name}")
    except Exception as e:
        print(f"Failed to load pipeline {key}: {import_path}")
        print(e)

# AVAILABLE_PIPELINES = {
#     ALL_CAM_PIPELINE.name: ALL_CAM_PIPELINE,
#     BASIC_DEPTH_PIPELINE.name: BASIC_DEPTH_PIPELINE
# }