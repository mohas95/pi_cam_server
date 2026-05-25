from dataclasses import dataclass, field
from typing import Callable


@dataclass
class PipelineDefinition:
    name: str
    build_fn: Callable
    runtime_transform_fn: Callable
    output_meta_fn: Callable | None=None
    description: str = ""
    default_build_params: dict = field(default_factory=dict)
    default_transform_params: dict = field(default_factory=dict)

    def build(self, pipeline, device, **overrides):
        params = {**self.default_build_params, **overrides}
        return self.build_fn(pipeline, device, **params)
    
    def transform(self, output_queues, **overrides):
        params = {**self.default_transform_params, **overrides}
        return self.runtime_transform_fn(output_queues,**params)
    
    def get_output_meta(self, output_queues):

        if self.output_meta_fn:
            return self.output_meta_fn(output_queues=output_queues)
        
        return {}