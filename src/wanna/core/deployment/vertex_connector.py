from typing import Generic, TypeVar

from wanna.core.deployment.models import GCPResource
from wanna.core.deployment.vertex_jobs import VertexJobsMixInVertex
from wanna.core.deployment.vertex_pipelines import VertexPipelinesMixInVertex

T = TypeVar("T", bound=GCPResource)


class VertexConnector(Generic[T], VertexPipelinesMixInVertex, VertexJobsMixInVertex):
    pass
