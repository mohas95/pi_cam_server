import depthai as dai
import cv2
from camera.pipeline_definition import PipelineDefinition
import numpy as np


colorMap = cv2.applyColorMap(np.arange(256, dtype=np.uint8), cv2.COLORMAP_JET)
colorMap[0] = [0, 0, 0]  # to make zero-disparity pixels black


def build_spatial_pipeline(pipeline, device, FPS = 25):

    monoLeft = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
    monoRight = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)
    stereo = pipeline.create(dai.node.StereoDepth)

    monoLeftOut = monoLeft.requestFullResolutionOutput()
    monoRightOut = monoRight.requestFullResolutionOutput()
    monoLeftOut.link(stereo.left)
    monoRightOut.link(stereo.right)

    stereo.setRectification(True)
    stereo.setExtendedDisparity(True)
    stereo.setLeftRightCheck(True)

    disparityQueue = stereo.disparity.createOutputQueue()

    return {"disparityQueue":disparityQueue}

def color_map_transform(output_queues,maxDisparity = 1):

    output_frames={}
    data_out={}

    disparityQueue =output_queues["disparityQueue"]

    disparity = disparityQueue.tryGet()

    if disparity is None:
        return None
    
    npDisparity = disparity.getFrame()
    
    maxDisparity = max(maxDisparity, np.max(npDisparity))
    colorizedDisparity = cv2.applyColorMap(((npDisparity / maxDisparity) * 255).astype(np.uint8), colorMap)

    output_frames["disparity"] = colorizedDisparity

    if not output_frames and not data_out:
        return None

    return {
        "img_out": output_frames,
        "data": data_out,
    }

def output_meta(output_queues):
     
    img_streams=["disparity"]
    data_streams = []

    return {"img_streams":img_streams, "data_streams":data_streams}

BASIC_DEPTH_PIPELINE = PipelineDefinition(
    name="basic depth pipeline",
    description="basic depth stream",
    build_fn=build_spatial_pipeline,
    runtime_transform_fn=color_map_transform,
    output_meta_fn=output_meta,
    default_build_params={
        "FPS":20
    },
    default_transform_params={
        "maxDisparity":1
    }
)