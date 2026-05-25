from camera.pipelines.allCam import ALL_CAM_PIPELINE
from camera.pipelines.SpatialDepth import BASIC_DEPTH_PIPELINE

AVAILABLE_PIPELINES = {
    ALL_CAM_PIPELINE.name: ALL_CAM_PIPELINE,
    BASIC_DEPTH_PIPELINE.name: BASIC_DEPTH_PIPELINE
}