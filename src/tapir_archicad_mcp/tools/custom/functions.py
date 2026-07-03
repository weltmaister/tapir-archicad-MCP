import logging
import time
from typing import Optional, Any, Dict
from pydantic import BaseModel, ValidationError

from mcp.types import ToolAnnotations

from tapir_archicad_mcp.app import mcp
from tapir_archicad_mcp.audit import write_audit_entry
from tapir_archicad_mcp.context import multi_conn_instance
from tapir_archicad_mcp.idempotency import IdempotencyStore
from tapir_archicad_mcp.tools.custom.models import (
    ReadyInstance,
    UnavailableInstance,
    DiscoveryResult,
    ProjectType,
    CommandSchema,
    CommandOverview,
)
from tapir_archicad_mcp.tools.tool_registry import get_tool_entry, TOOL_DISCOVERY_CATALOG
from tapir_archicad_mcp.tools.validation import validate_result

from multiconn_archicad.conn_header import ConnHeader
from multiconn_archicad.basic_types import (
    TeamworkProjectID,
    SoloProjectID,
    ProductInfo,
    TapirInfo,
    APIResponseError,
)
from multiconn_archicad.errors import AddOnCommandUnavailable

log = logging.getLogger()

_idempotency_store: Optional[IdempotencyStore] = None


def _get_idempotency_store() -> IdempotencyStore:
    """Lazily opens the store so importing this module has no side effects."""
    global _idempotency_store
    if _idempotency_store is None:
        _idempotency_store = IdempotencyStore()
    return _idempotency_store


@mcp.tool(
    name="discovery_list_active_archicads",
    title="List Active Archicad Instances",
    description=(
        "Scans for and lists running Archicad instances. "
        "Returns 'active' (ready to receive commands with their target 'port') "
        "and 'unavailable' (instances that are unresponsive or missing the Tapir Add-On)."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
def list_active_archicads() -> DiscoveryResult:
    log.info("Executing list_active_archicads tool...")
    try:
        multi_conn = multi_conn_instance.get()
    except LookupError:
        log.error("CRITICAL: multi_conn_instance context variable not set. Lifespan manager may have failed.")
        raise RuntimeError("Server configuration error: could not access MultiConn instance.")

    multi_conn.refresh.all_ports()
    multi_conn.connect.all()

    active_instances: list[ReadyInstance] = []
    unavailable_instances: list[UnavailableInstance] = []

    for port, header in multi_conn.open_port_headers.items():
        if not isinstance(header.product_info, ProductInfo):
            unavailable_instances.append(_build_unresponsive_instance(header.product_info))
        elif not isinstance(header.tapir_info, TapirInfo) or not header.tapir_info.is_installed or not header.tapir_info.version:
            unavailable_instances.append(_build_missing_tapir_instance())
        else:
            active_instances.append(_build_ready_instance(int(port), header))

    log.info(f"Discovery complete: {len(active_instances)} ready, {len(unavailable_instances)} unavailable.")
    return DiscoveryResult(
        activeInstances=active_instances,
        unavailableInstances=unavailable_instances,
    )


def _build_unresponsive_instance(error: APIResponseError) -> UnavailableInstance:
    """Builds diagnostic info for an unresponsive Archicad instance."""
    return UnavailableInstance(
        reason="unresponsive",
        message=(
            f"Archicad API error: '{error.message}'. "
            "If the error message is actionable, please prompt the user to resolve it."
        )
    )


def _build_missing_tapir_instance() -> UnavailableInstance:
    """Builds diagnostic info and installation instructions when Tapir is not installed."""
    return UnavailableInstance(
        reason="missing_tapir",
        message=(
            "Archicad was detected, but the Tapir Add-On is not installed. "
            "The Tapir Add-On is required for AI automation. "
            "Please prompt the user to download and install it from: "
            "https://github.com/ENZYME-APD/tapir-archicad-automation"
        )
    )


def _build_ready_instance(port: int, header: ConnHeader) -> ReadyInstance:
    """Builds a ready-to-use Archicad instance metadata model."""
    project_id = header.archicad_id
    project_type: ProjectType = "untitled"
    project_path: Optional[str] = None

    if isinstance(project_id, TeamworkProjectID):
        project_type = "teamwork"
        project_path = f"teamwork://{project_id.serverAddress}/{project_id.projectPath}"
    elif isinstance(project_id, SoloProjectID):
        project_type = "solo"
        project_path = project_id.projectPath

    tapir: TapirInfo = header.tapir_info

    return ReadyInstance(
        port=port,
        projectName=getattr(project_id, "projectName", "Untitled"),
        projectType=project_type,
        archicadVersion=str(header.product_info.version),
        tapirVersion=tapir.version,
        projectPath=project_path,
        warning=_get_tapir_version_warning(tapir),
    )


def _get_tapir_version_warning(tapir: TapirInfo) -> Optional[str]:
    """Generates a diagnostic warning if the installed Tapir version differs from supported."""
    if tapir.is_older:
        return (
            f"Installed Tapir version ({tapir.version}) is older than supported ({tapir.requiredVersion}). "
            "Most commands will work, but newer commands or parameters may fail. "
            "If you encounter command errors, prompt the user to upgrade Tapir."
        )
    if tapir.is_newer:
        return (
            f"Installed Tapir version ({tapir.version}) is newer than supported ({tapir.requiredVersion}). "
            "Operations should proceed normally."
        )
    return None


@mcp.tool(
    name="archicad_list_commands",
    title="List Available Archicad Commands",
    description=(
        "Returns a comprehensive list of all available Archicad API commands and brief descriptions. "
        "STEP 1: Use this tool FIRST to search for the right command name for your task. "
        "Do NOT guess or hallucinate command names. "
        "STEP 2: Once you find the relevant command name, you MUST use the 'archicad_get_command_schema' "
        "tool to learn its exact required arguments."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def archicad_list_commands() -> list[CommandOverview]:
    log.info("Executing archicad_list_commands tool...")
    return [
        CommandOverview(
            name=tool["name"],
            description=tool["description"],
        )
        for tool in TOOL_DISCOVERY_CATALOG
    ]


@mcp.tool(
    name="archicad_get_command_schema",
    title="Get Archicad Command Schema",
    description=(
        "Retrieves the exact JSON schema (required arguments) for a specific Archicad command. "
        "Provide the exact 'command_name' obtained from 'archicad_list_commands'. "
        "CRITICAL: You MUST call this tool before executing 'archicad_call_tool' to ensure you provide "
        "the correct parameters. Do NOT guess or hallucinate parameters based on the command name."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def archicad_get_command_schema(command_name: str) -> CommandSchema:
    log.info(f"Executing archicad_get_command_schema for: {command_name}")
    for tool in TOOL_DISCOVERY_CATALOG:
        if tool["name"] == command_name:
            return CommandSchema(
                name=tool["name"],
                input_schema=tool["input_schema"],
            )

    raise ValueError(
        f"Command '{command_name}' not found. Please use 'archicad_list_commands' "
        f"to verify the exact spelling of the command name."
    )


@mcp.tool(
    name="archicad_call_tool",
    title="Execute Archicad API Command",
    description=(
        "Executes a specific Archicad API command by its 'name'. "
        "CRITICAL WORKFLOW: You MUST use 'archicad_get_command_schema' first to understand the exact "
        "JSON structure required for the 'arguments' parameter. "
        "The 'arguments' dictionary MUST contain a 'port' number (obtained from 'discovery_list_active_archicads'). "
        "If a tool's response includes a 'next_page_token', call this same tool again with the same parameters "
        "and add a 'page_token' key to the 'arguments' dictionary. "
        "For commands that create or modify elements, add a unique 'idempotency_key' string to 'arguments' to make the call safe to retry: "
        "repeating the call with the same key and arguments returns the first response instead of executing again."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
def archicad_call_tool(name: str, arguments: dict) -> dict:
    log.info(f"Executing archicad_call_tool for tool: {name}")
    started = time.perf_counter()
    idempotency_key = arguments.pop('idempotency_key', None)
    replayed = False

    try:
        response = _fetch_replayed_response(name, arguments, idempotency_key)
        replayed = response is not None
        if response is None:
            response = _execute_tool_call(name, arguments)
            if idempotency_key:
                _get_idempotency_store().store(name, idempotency_key, {"name": name, **arguments}, response)
    except Exception as e:
        write_audit_entry(
            tool=name,
            port=arguments.get('port'),
            success=False,
            durationMs=int((time.perf_counter() - started) * 1000),
            idempotencyKey=idempotency_key,
            error=str(e),
        )
        raise

    write_audit_entry(
        tool=name,
        port=arguments.get('port'),
        success=True,
        durationMs=int((time.perf_counter() - started) * 1000),
        idempotencyKey=idempotency_key,
        replayed=replayed,
    )
    return response


def _fetch_replayed_response(name: str, arguments: dict, idempotency_key: Optional[str]) -> Optional[dict]:
    """Returns the replayed response for a known idempotency_key, else None."""
    if not idempotency_key:
        return None
    cached = _get_idempotency_store().fetch(name, idempotency_key, {"name": name, **arguments})
    if cached is not None:
        log.info(f"Replaying stored response for '{name}' (idempotency_key={idempotency_key}).")
    return cached


def _execute_tool_call(name: str, arguments: dict) -> dict:
    if 'port' not in arguments:
        raise ValueError("The 'arguments' dictionary must contain the 'port' number.")

    port = arguments['port']
    tool_entry = get_tool_entry(name)
    target_func = tool_entry.callable
    params_model = tool_entry.params_model

    call_args: Dict[str, Any] = {'port': port}

    if params_model:
        # Check if the agent wrapped the params in a 'params' key or flattened them
        raw_params = arguments.get('params', arguments)
        try:
            params_instance = validate_result(params_model, raw_params)
            call_args['params'] = params_instance
        except ValidationError as e:
            log.error(f"Validation error for parameters of {name}: {e}")
            raise ValueError(f"Invalid parameters provided for tool '{name}'. Validation details: {e}")

    if 'page_token' in arguments:
        call_args['page_token'] = arguments['page_token']

    try:
        result = target_func(**call_args)

        if result is None:
            return {}

        if isinstance(result, BaseModel):
            return result.model_dump(mode='json', by_alias=True, exclude_none=True)

        return {"result": result}

    except AddOnCommandUnavailable as e:
        log.warning(f"AddOnCommandUnavailable for tool '{name}' on port {port}: {e}")
        raise ValueError(
            f"Command '{name}' is not available in the installed Tapir Add-On on port {port}. "
            f"This indicates that the Tapir Add-On is outdated. "
            f"Please prompt the user to upgrade Tapir from https://github.com/ENZYME-APD/tapir-archicad-automation. "
            f"(Details: {e.message})"
        ) from e
    except Exception as e:
        log.error(f"Error executing dispatched tool {name}: {e}")
        raise e