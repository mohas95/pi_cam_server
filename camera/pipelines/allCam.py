import depthai as dai
from camera.pipeline_definition import PipelineDefinition


def build_all_cam_pipeline(pipeline, device, size, fps):

    sockets = device.getConnectedCameras()
    output_queues={}
    for socket in sockets:
        cam = pipeline.create(dai.node.Camera).build(socket)

        # output_queues[str(socket)] = cam.requestFullResolutionOutput().createOutputQueue()
        output_queues[str(socket)] = cam.requestOutput(size, type=dai.ImgFrame.Type.NV12, 
                              resizeMode=dai.ImgResizeMode.CROP, 
                              enableUndistortion=True,
                              fps=fps).createOutputQueue()
    

    # cam = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
    # output = cam.requestOutput(size, type=dai.ImgFrame.Type.NV12, 
    #                           resizeMode=dai.ImgResizeMode.CROP, 
    #                           enableUndistortion=True,
    #                           fps=fps).createOutputQueue()
    
    # return {"CAM_A_rgb":output}
    return output_queues


ALL_CAM_PIPELINE = PipelineDefinition(
    name="all cam modules pipeline",
    description="single RGB camera stream",
    build_fn=build_all_cam_pipeline,
    default_params={
        "size":(1280,800),
        "fps":20
    }
)