import depthai as dai
from camera.pipeline_definition import PipelineDefinition

def build_rgb_pipeline(pipeline, device, size, fps):
    cam = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
    output = cam.requestOutput(size, type=dai.ImgFrame.Type.NV12, 
                              resizeMode=dai.ImgResizeMode.CROP, 
                              enableUndistortion=True,
                              fps=fps).createOutputQueue()
    
    return {"CAM_A_rgb":output}


RGB_PIPELINE = PipelineDefinition(
    name="rgb pipeline",
    description="single RGB camera stream",
    build_fn=build_rgb_pipeline,
    output_streams=["CAM_A_rgb"],
    default_params={
        "size":(1280,800),
        "fps":20
    }
)