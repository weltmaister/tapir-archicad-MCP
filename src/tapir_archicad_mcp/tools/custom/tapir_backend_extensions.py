import logging

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from multiconn_archicad.basic_types import Port

from tapir_archicad_mcp.context import multi_conn_instance
from tapir_archicad_mcp.tools.tool_registry import register_tool_for_dispatch
from tapir_archicad_mcp.tools.custom.tapir_element_models import (
    AssociativeDimensionData,
    AssociativeDimensionOnSectionData,
    BeamData,
    BeamWithDetails,
    ColumnWithDetails,
    DetailData,
    DoorData,
    DoorWithDetails,
    DrawingData,
    LayoutData,
    MorphData,
    MorphWithDetails,
    OpeningData,
    RoofData,
    RoofWithDetails,
    SlabWithDetails,
    SubsetData,
    WallData,
    WallThicknessDimensionData,
    WallWithDetails,
    WindowData,
    WindowWithDetails,
    WorksheetData,
)

log = logging.getLogger()


class ArbitraryTapirResult(BaseModel):
    model_config = ConfigDict(extra="allow")


class CreateWallsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wallsData: list[WallData] = Field(min_length=1, description="List of walls to create.")


class ModifyWallsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wallsWithDetails: list[WallWithDetails] = Field(min_length=1, description="List of walls to modify.")


class CreateBeamsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beamsData: list[BeamData] = Field(min_length=1, description="List of beams to create.")


class ModifyBeamsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beamsWithDetails: list[BeamWithDetails] = Field(min_length=1, description="List of beams to modify.")


class CreateWindowsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    windowsData: list[WindowData] = Field(min_length=1, description="List of windows to create.")


class ModifyWindowsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    windowsWithDetails: list[WindowWithDetails] = Field(min_length=1, description="List of windows to modify.")


class CreateDoorsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doorsData: list[DoorData] = Field(min_length=1, description="List of doors to create.")


class ModifyDoorsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doorsWithDetails: list[DoorWithDetails] = Field(min_length=1, description="List of doors to modify.")


class CreateOpeningsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    openingsData: list[OpeningData] = Field(min_length=1, description="List of openings to create.")


class CreateMorphsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    morphsData: list[MorphData] = Field(min_length=1, description="List of morph elements to create.")


class CreateRoofsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roofsData: list[RoofData] = Field(min_length=1, description="List of multi-plane roofs to create.")


class CreateAssociativeDimensionsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimensionsData: list[AssociativeDimensionData] = Field(min_length=1, description="List of associative dimensions to create.")


class CreateAssociativeDimensionsOnSectionParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimensionsData: list[AssociativeDimensionOnSectionData] = Field(
        min_length=1, description="List of section dimensions to create."
    )


class CreateWallThicknessDimensionsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimensionsData: list[WallThicknessDimensionData] = Field(
        min_length=1, description="List of wall thickness dimensions to create."
    )


class CreateDetailsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detailsData: list[DetailData] = Field(min_length=1, description="List of detail databases to create.")


class CreateWorksheetsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worksheetsData: list[WorksheetData] = Field(min_length=1, description="List of worksheet databases to create.")


class CreateLayoutsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layoutsData: list[LayoutData] = Field(min_length=1, description="List of layouts (with master layouts) to create.")


class CreateSubsetsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subsetsData: list[SubsetData] = Field(min_length=1, description="List of layout book subsets to create.")


class CreateDrawingsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drawingsData: list[DrawingData] = Field(min_length=1, description="List of drawing elements to place on a layout.")


class ModifySlabsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slabsWithDetails: list[SlabWithDetails] = Field(min_length=1, description="List of slabs to modify.")


class ModifyColumnsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columnsWithDetails: list[ColumnWithDetails] = Field(min_length=1, description="List of columns to modify.")


class ModifyMorphsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    morphsWithDetails: list[MorphWithDetails] = Field(min_length=1, description="List of morph elements to modify.")


class ModifyRoofsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roofsWithDetails: list[RoofWithDetails] = Field(min_length=1, description="List of roofs to modify.")


def _execute_tapir_command(
    port: int,
    command: str,
    params: BaseModel,
    result_model: type[BaseModel] = ArbitraryTapirResult,
) -> BaseModel:
    multi_conn = multi_conn_instance.get()
    target_port = Port(port)
    if target_port not in multi_conn.active:
        raise ValueError(f"Port {port} is not an active Archicad connection.")
    conn_header = multi_conn.active[target_port]
    payload = params.model_dump(mode="json", exclude_none=True)
    try:
        result_dict = conn_header.core.post_tapir_command(command=command, parameters=payload)
        return result_model.model_validate(result_dict)
    except ValidationError as e:
        log.error("Validation error for %s result: %s", command, e)
        raise ValueError(f"Received an invalid response from the Archicad API: {e}")
    except Exception as e:
        log.error("Error executing %s on port %s: %s", command, port, e)
        raise


def _make_tool(*, command: str, params_model: type[BaseModel]):
    def tool(port: int, params: params_model):
        return _execute_tapir_command(port, command, params=params, result_model=ArbitraryTapirResult)

    tool.__name__ = command.lower()
    tool.__doc__ = f"Dispatches the Tapir '{command}' command."
    return tool


_REGISTRATIONS = [
    ("elements_create_walls", "CreateWalls", "Creates new wall elements.", CreateWallsParameters),
    ("elements_modify_walls", "ModifyWalls", "Modifies existing wall elements.", ModifyWallsParameters),
    ("elements_create_beams", "CreateBeams", "Creates new beam elements.", CreateBeamsParameters),
    ("elements_modify_beams", "ModifyBeams", "Modifies existing beam elements.", ModifyBeamsParameters),
    ("elements_create_windows", "CreateWindows", "Creates new window elements hosted in walls.", CreateWindowsParameters),
    ("elements_modify_windows", "ModifyWindows", "Modifies existing window elements.", ModifyWindowsParameters),
    ("elements_create_doors", "CreateDoors", "Creates new door elements hosted in walls.", CreateDoorsParameters),
    ("elements_modify_doors", "ModifyDoors", "Modifies existing door elements.", ModifyDoorsParameters),
    ("elements_create_openings", "CreateOpenings", "Creates new opening elements.", CreateOpeningsParameters),
    ("elements_create_morphs", "CreateMorphs", "Creates simple morph elements.", CreateMorphsParameters),
    ("elements_create_roofs", "CreateRoofs", "Creates multi-plane roof elements.", CreateRoofsParameters),
    ("elements_create_associative_dimensions", "CreateAssociativeDimensions", "Creates associative linear dimensions from explicit witness point references.", CreateAssociativeDimensionsParameters),
    ("elements_create_associative_dimensions_on_section", "CreateAssociativeDimensionsOnSection", "Creates associative linear dimensions on section elements using common presets.", CreateAssociativeDimensionsOnSectionParameters),
    ("elements_create_wall_thickness_dimensions", "CreateWallThicknessDimensions", "Creates associative wall thickness dimensions.", CreateWallThicknessDimensionsParameters),
    ("elements_modify_slabs", "ModifySlabs", "Modifies existing slab elements.", ModifySlabsParameters),
    ("elements_modify_columns", "ModifyColumns", "Modifies existing column elements.", ModifyColumnsParameters),
    ("elements_modify_morphs", "ModifyMorphs", "Modifies existing morph elements.", ModifyMorphsParameters),
    ("elements_modify_roofs", "ModifyRoofs", "Modifies existing multi-plane roof elements.", ModifyRoofsParameters),
    ("navigator_create_details", "CreateDetails", "Creates independent detail databases.", CreateDetailsParameters),
    ("navigator_create_worksheets", "CreateWorksheets", "Creates independent worksheet databases.", CreateWorksheetsParameters),
    ("layout_create_layouts", "CreateLayouts", "Creates master-layout and layout pairs.", CreateLayoutsParameters),
    ("layout_create_subsets", "CreateSubsets", "Creates layout subsets.", CreateSubsetsParameters),
    ("layout_create_drawings", "CreateDrawings", "Creates drawing elements on the specified or active layout from navigator items.", CreateDrawingsParameters),
]


for tool_name, command, description, params_model in _REGISTRATIONS:
    register_tool_for_dispatch(
        _make_tool(command=command, params_model=params_model),
        name=tool_name,
        title=command,
        description=description,
        params_model=params_model,
        result_model=ArbitraryTapirResult,
    )
