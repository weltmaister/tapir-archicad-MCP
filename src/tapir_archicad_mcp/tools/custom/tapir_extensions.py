import logging

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from multiconn_archicad.basic_types import Port
from multiconn_archicad.models.tapir.types import Coordinate2D, ElementId, ElementIdArrayItem

from tapir_archicad_mcp.context import multi_conn_instance
from tapir_archicad_mcp.tools.tool_registry import register_tool_for_dispatch

log = logging.getLogger()


class LabelDatum(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parentElementId: ElementId | None = Field(
        default=None,
        description="The parent element if the label is an associative label.",
    )
    text: str | None = Field(
        default=None,
        description="The text content if the label is a text label.",
    )
    begCoordinate: Coordinate2D | None = Field(
        default=None,
        description="The begin coordinate of the leader line. Required when no parentElementId is provided.",
    )
    floorInd: float | None = Field(
        default=None,
        description="Optional floor index override; by default the current floor or the floor of the parent element is used.",
    )


class CreateLabelsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    labelsData: list[LabelDatum] = Field(description="Array of data to create Labels.", min_length=1)


class CreateLabelsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    elements: list[ElementIdArrayItem] = Field(description="A list of elements.")


def create_labels(port: int, params: CreateLabelsParameters) -> CreateLabelsResult:
    """
    Creates Label elements based on the given parameters.
    """
    multi_conn = multi_conn_instance.get()
    target_port = Port(port)
    if target_port not in multi_conn.active:
        raise ValueError(f"Port {port} is not an active Archicad connection.")
    conn_header = multi_conn.active[target_port]
    try:
        result_dict = conn_header.core.post_tapir_command(
            command="CreateLabels",
            parameters=params.model_dump(mode="json"),
        )
        return CreateLabelsResult.model_validate(result_dict)
    except ValidationError as e:
        log.error(f"Validation error for CreateLabels result: {e}")
        raise ValueError(f"Received an invalid response from the Archicad API: {e}")
    except Exception as e:
        log.error(f"Error executing CreateLabels on port {port}: {e}")
        raise e


register_tool_for_dispatch(
    create_labels,
    name="elements_create_labels",
    title="CreateLabels",
    description="Creates Label elements based on the given parameters.",
    params_model=CreateLabelsParameters,
    result_model=CreateLabelsResult,
)
