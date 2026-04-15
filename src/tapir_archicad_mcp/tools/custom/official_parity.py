import logging

from pydantic import ValidationError
from multiconn_archicad.basic_types import Port
from multiconn_archicad.models.official.commands import (
    ExecuteAddOnCommandParameters,
    ExecuteAddOnCommandResult,
    GetProductInfoResult,
    IsAliveResult,
)

from tapir_archicad_mcp.context import multi_conn_instance
from tapir_archicad_mcp.tools.tool_registry import register_tool_for_dispatch

log = logging.getLogger()


def _get_active_header(port: int):
    multi_conn = multi_conn_instance.get()
    target_port = Port(port)
    if target_port not in multi_conn.active:
        raise ValueError(f"Port {port} is not an active Archicad connection.")
    return multi_conn.active[target_port]


def get_product_info(port: int) -> GetProductInfoResult:
    """
    Accesses the version information from the running Archicad.
    """
    header = _get_active_header(port)
    try:
        result_dict = header.core.post_command("API.GetProductInfo")
        return GetProductInfoResult.model_validate(result_dict)
    except ValidationError as e:
        log.error("Validation error for GetProductInfo result: %s", e)
        raise ValueError(f"Received an invalid response from the Archicad API: {e}")


def is_alive(port: int) -> IsAliveResult:
    """
    Checks if the Archicad connection is alive.
    """
    header = _get_active_header(port)
    try:
        result_dict = header.core.post_command("API.IsAlive")
        return IsAliveResult.model_validate(result_dict)
    except ValidationError as e:
        log.error("Validation error for IsAlive result: %s", e)
        raise ValueError(f"Received an invalid response from the Archicad API: {e}")


def execute_add_on_command(port: int, params: ExecuteAddOnCommandParameters) -> ExecuteAddOnCommandResult:
    """
    Executes a command registered in an Add-On via the official Archicad JSON API.
    """
    header = _get_active_header(port)
    try:
        result_dict = header.core.post_command(
            "API.ExecuteAddOnCommand",
            params.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return ExecuteAddOnCommandResult.model_validate(result_dict)
    except ValidationError as e:
        log.error("Validation error for ExecuteAddOnCommand result: %s", e)
        raise ValueError(f"Received an invalid response from the Archicad API: {e}")


register_tool_for_dispatch(
    get_product_info,
    name="basic_get_product_info",
    title="GetProductInfo",
    description="Accesses the version information from the running Archicad.",
    result_model=GetProductInfoResult,
)

register_tool_for_dispatch(
    is_alive,
    name="basic_is_alive",
    title="IsAlive",
    description="Checks if the Archicad connection is alive.",
    result_model=IsAliveResult,
)

register_tool_for_dispatch(
    execute_add_on_command,
    name="dev_execute_add_on_command",
    title="ExecuteAddOnCommand",
    description="Executes a command registered in an Add-On via the official Archicad JSON API.",
    params_model=ExecuteAddOnCommandParameters,
    result_model=ExecuteAddOnCommandResult,
)
