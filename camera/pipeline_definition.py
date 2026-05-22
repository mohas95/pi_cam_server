from dataclasses import dataclass, field
from typing import Callable


@dataclass
class PipelineDefinition:
    name: str
    build_fn: Callable
    output_streams: list[str]
    description: str = ""
    default_params: dict = field(default_factory=dict)

    def build(self, pipeline, device, **overrides):
        params = {**self.default_params, **overrides}
        return self.build_fn(pipeline, device, **params)