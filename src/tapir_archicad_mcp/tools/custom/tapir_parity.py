import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from multiconn_archicad.basic_types import Port
from multiconn_archicad.models.tapir.commands import (
    GenerateDocumentationParameters,
    GetArchicadLocationResult,
    GetProjectInfoResult,
)
from multiconn_archicad.models.tapir.types import (
    ColorRGB,
    DatabaseId,
    ElementId,
    ElementIdArrayItem,
    WindowType,
)

from tapir_archicad_mcp.context import multi_conn_instance
from tapir_archicad_mcp.tools.tool_registry import register_tool_for_dispatch

log = logging.getLogger()


class ArbitraryTapirResult(BaseModel):
    model_config = ConfigDict(extra="allow")


class ChangeWindowParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    windowType: WindowType
    databaseId: DatabaseId | None = None


class FitInWindowParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    elements: list[ElementIdArrayItem] | None = Field(
        default=None,
        description="Optional list of elements to fit in the active window.",
    )


class ElementPreviewImageParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    elementId: ElementId
    imageType: Literal["2D", "Section", "3D"] | None = None
    format: Literal["png", "jpg"] | None = None
    width: int | None = None
    height: int | None = None


class FavoritePreviewImageParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    favorite: str = Field(min_length=1)
    imageType: Literal["2D", "Section", "3D"] | None = None
    format: Literal["png", "jpg"] | None = None
    width: int | None = None
    height: int | None = None


class PreviewImageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    previewImage: str


class RoomImageParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zoneId: ElementId
    format: Literal["png", "jpg"] | None = None
    width: int | None = None
    height: int | None = None
    offset: float | None = None
    scale: float | None = None
    backgroundColor: ColorRGB | None = None


class RoomImageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roomImage: str


class IFCFileOperationParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["save", "merge", "open"]
    ifcFilePath: str = Field(min_length=1)
    fileType: Literal["ifc", "ifcxml", "ifczip", "ifcxmlzip"] | None = None


class PrintViewParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grid: bool | None = None
    fixText: bool | None = None
    scale: int | None = None
    printArea: Literal["currentView", "entireDrawing", "marquee"] | None = None


class NotificationClientParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str | None = None
    port: int


class SetElementNotificationClientParameters(NotificationClientParameters):
    model_config = ConfigDict(extra="forbid")

    notifyOnNewElement: bool | None = None
    notifyOnModificationOfAnElement: bool | None = None
    notifyOnReservationChanges: bool | None = None


class CutPlane(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pa: float
    pb: float
    pc: float
    pd: float


class Set3DCutPlanesParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cutPlanes: list[CutPlane] = Field(min_length=1)


class ProjectLocationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    longitude: float | None = None
    latitude: float | None = None
    altitude: float | None = None
    north: float | None = None


class SurveyPointPositionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eastings: float | None = None
    northings: float | None = None
    elevation: float | None = None


class GeoReferencingParametersPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crsName: str | None = None
    description: str | None = None
    geodeticDatum: str | None = None
    verticalDatum: str | None = None
    mapProjection: str | None = None
    mapZone: str | None = None


class SurveyPointPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: SurveyPointPositionPayload | None = None
    geoReferencingParameters: GeoReferencingParametersPayload | None = None


class SetGeoLocationParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    projectLocation: ProjectLocationPayload | None = None
    surveyPoint: SurveyPointPayload | None = None


class DesignOptionReference(BaseModel):
    model_config = ConfigDict(extra="allow")


class DesignOptionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    designOptionId: DesignOptionReference
    name: str
    id: str
    ownerSetName: str


class GetDesignOptionsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    designOptions: list[DesignOptionData]


class DesignOptionSetData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    designOptionSetId: DesignOptionReference
    name: str
    designOptions: list[DesignOptionReference]


class GetDesignOptionSetsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    designOptionSets: list[DesignOptionSetData]


class DesignOptionCombinationData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    designOptionCombinationId: DesignOptionReference
    name: str
    activeDesignOptions: list[DesignOptionReference] | None = None


class GetDesignOptionCombinationsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    designOptionCombinations: list[DesignOptionCombinationData]


def _execute_tapir_command(
    port: int,
    command: str,
    params: BaseModel | None = None,
    result_model: type[BaseModel] = ArbitraryTapirResult,
) -> BaseModel:
    multi_conn = multi_conn_instance.get()
    target_port = Port(port)
    if target_port not in multi_conn.active:
        raise ValueError(f"Port {port} is not an active Archicad connection.")
    conn_header = multi_conn.active[target_port]
    payload = params.model_dump(mode="json", exclude_none=True) if params else {}
    try:
        result_dict = conn_header.core.post_tapir_command(command=command, parameters=payload)
        return result_model.model_validate(result_dict)
    except ValidationError as e:
        log.error("Validation error for %s result: %s", command, e)
        raise ValueError(f"Received an invalid response from the Archicad API: {e}")
    except Exception as e:
        log.error("Error executing %s on port %s: %s", command, port, e)
        raise


def _make_tool(
    *,
    command: str,
    params_model: type[BaseModel] | None = None,
    result_model: type[BaseModel] = ArbitraryTapirResult,
):
    if params_model is None:
        def tool(port: int):
            return _execute_tapir_command(port, command, result_model=result_model)
    else:
        def tool(port: int, params: params_model):
            return _execute_tapir_command(port, command, params=params, result_model=result_model)

    tool.__name__ = command.lower()
    tool.__doc__ = f"Dispatches the Tapir '{command}' command."
    return tool


_REGISTRATIONS = [
    ("app_get_archicad_location", "GetArchicadLocation", "Retrieves the location of the running Archicad executable.", None, GetArchicadLocationResult),
    ("app_quit_archicad", "QuitArchicad", "Performs a quit operation on the running Archicad instance.", None, ArbitraryTapirResult),
    ("app_change_window", "ChangeWindow", "Changes the current active Archicad window.", ChangeWindowParameters, ArbitraryTapirResult),
    ("project_get_project_info", "GetProjectInfo", "Retrieves information about the currently loaded project.", None, GetProjectInfoResult),
    ("project_close_project", "CloseProject", "Closes the currently opened project.", None, ArbitraryTapirResult),
    ("project_save_project", "SaveProject", "Saves the currently opened project.", None, ArbitraryTapirResult),
    ("project_set_geo_location", "SetGeoLocation", "Sets the project geolocation details.", SetGeoLocationParameters, ArbitraryTapirResult),
    ("project_ifc_file_operation", "IFCFileOperation", "Executes an IFC file operation.", IFCFileOperationParameters, ArbitraryTapirResult),
    ("project_print_view", "PrintView", "Prints from the current view.", PrintViewParameters, ArbitraryTapirResult),
    ("navigator_fit_in_window", "FitInWindow", "Zooms to the given elements or fits everything in the window.", FitInWindowParameters, ArbitraryTapirResult),
    ("dev_generate_documentation", "GenerateDocumentation", "Generates Tapir documentation files.", GenerateDocumentationParameters, ArbitraryTapirResult),
    ("project_get_design_options", "GetDesignOptions", "Retrieves information about existing design options.", None, GetDesignOptionsResult),
    ("project_get_design_option_sets", "GetDesignOptionSets", "Retrieves information about existing design option sets.", None, GetDesignOptionSetsResult),
    ("project_get_design_option_combinations", "GetDesignOptionCombinations", "Retrieves information about existing design option combinations.", None, GetDesignOptionCombinationsResult),
    ("elements_get_element_preview_image", "GetElementPreviewImage", "Returns the preview image of the given element.", ElementPreviewImageParameters, PreviewImageResult),
    ("favorites_get_favorite_preview_image", "GetFavoritePreviewImage", "Returns the preview image of the given favorite.", FavoritePreviewImageParameters, PreviewImageResult),
    ("elements_get_room_image", "GetRoomImage", "Returns the room image of the given zone.", RoomImageParameters, RoomImageResult),
    ("elements_set_element_notification_client", "SetElementNotificationClient", "Registers an element notification client.", SetElementNotificationClientParameters, ArbitraryTapirResult),
    ("elements_remove_element_notification_client", "RemoveElementNotificationClient", "Removes an element notification client.", NotificationClientParameters, ArbitraryTapirResult),
    ("view_set3_d_cut_planes", "Set3DCutPlanes", "Sets the 3D cut planes for the active view.", Set3DCutPlanesParameters, ArbitraryTapirResult),
]


for tool_name, command, description, params_model, result_model in _REGISTRATIONS:
    register_tool_for_dispatch(
        _make_tool(command=command, params_model=params_model, result_model=result_model),
        name=tool_name,
        title=command,
        description=description,
        params_model=params_model,
        result_model=result_model,
    )
