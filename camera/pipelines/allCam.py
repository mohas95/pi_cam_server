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

def default_imgframe_transform(output_queues, stream_name=None):

    output_frames = {}
    data_out={}

    for name, queue in output_queues.items():
        try:
            msg = queue.tryGet()
            if msg is None:
                continue

            frame = msg.getCvFrame()

            output_frames[name] = frame

        except Exception as e:
            print(f"[DepthAI] queue {name} error:",e)


    if not output_frames and not data_out:
        return None
    
    return {
        "img_out": output_frames,
        "data": data_out,
    }


def all_cam_output_meta(output_queues):

    img_streams =list(output_queues.keys()) or []
    data_streams = []

    if output_queues is None:
        return None

    return {"img_streams":img_streams, "data_streams":data_streams}




ALL_CAM_PIPELINE = PipelineDefinition(
    name="all cam modules pipeline",
    description="single RGB camera stream",
    build_fn=build_all_cam_pipeline,
    output_meta_fn=all_cam_output_meta,
    runtime_transform_fn=default_imgframe_transform,
    default_build_params={
        "size":(1280,800),
        "fps":20
    },
    default_transform_params={}
)