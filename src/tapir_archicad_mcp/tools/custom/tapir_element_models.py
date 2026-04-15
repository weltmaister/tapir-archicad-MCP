"""
Typed Pydantic models for Tapir element creation and modification commands.

Derived from: tapir-archicad-automation/docs/archicad-addon/command_definitions.js
Common base types are reused from multiconn_archicad.models.tapir.types.
"""

from typing import List, Literal
from pydantic import BaseModel, ConfigDict, Field
from multiconn_archicad.models.tapir.types import (
    AttributeId,
    Coordinate2D,
    Coordinate3D,
    DatabaseId,
    Dimensions3D,
    ElementId,
    Hole2D,
    NavigatorItemId,
    PolyArc,
)


# ---------------------------------------------------------------------------
# Walls
# ---------------------------------------------------------------------------

class WallData(BaseModel):
    """Parameters for creating a single wall element."""
    model_config = ConfigDict(extra="forbid")

    begCoordinate: Coordinate2D = Field(description="Start point of the wall in the floor plan.")
    endCoordinate: Coordinate2D = Field(description="End point of the wall in the floor plan.")
    zCoordinate: float = Field(description="Bottom elevation of the wall in project units (meters).")
    height: float = Field(gt=0, description="Wall height in project units (meters). Must be greater than 0.")
    thickness: float = Field(gt=0, description="Wall thickness in project units (meters). Must be greater than 0.")
    offset: float | None = Field(None, description="Offset of the wall axis from the reference line in project units.")
    structureType: Literal["Basic", "Composite", "Profile"] | None = Field(
        None,
        description=(
            "Structure type of the wall. "
            "'Basic' = single building material, "
            "'Composite' = layered composite, "
            "'Profile' = custom cross-section profile."
        ),
    )
    buildingMaterialId: AttributeId | None = Field(
        None, description="Attribute ID of the building material (used when structureType is 'Basic')."
    )
    compositeId: AttributeId | None = Field(
        None, description="Attribute ID of the composite structure (used when structureType is 'Composite')."
    )
    profileId: AttributeId | None = Field(
        None, description="Attribute ID of the profile (used when structureType is 'Profile')."
    )


class WallWithDetails(BaseModel):
    """Parameters for modifying a single existing wall element. All fields except elementId are optional."""
    model_config = ConfigDict(extra="forbid")

    elementId: ElementId = Field(description="ID of the wall element to modify.")
    begCoordinate: Coordinate2D | None = Field(None, description="New start point of the wall.")
    endCoordinate: Coordinate2D | None = Field(None, description="New end point of the wall.")
    height: float | None = Field(None, gt=0, description="New wall height in project units.")
    thickness: float | None = Field(None, gt=0, description="New wall thickness in project units.")
    bottomOffset: float | None = Field(None, description="Vertical offset of the wall bottom from the floor level.")
    offset: float | None = Field(None, description="Offset of the wall axis from the reference line.")
    structureType: Literal["Basic", "Composite", "Profile"] | None = Field(None, description="New structure type.")
    buildingMaterialId: AttributeId | None = Field(None, description="New building material attribute ID.")
    compositeId: AttributeId | None = Field(None, description="New composite structure attribute ID.")
    profileId: AttributeId | None = Field(None, description="New profile attribute ID.")


# ---------------------------------------------------------------------------
# Beams
# ---------------------------------------------------------------------------

class BeamData(BaseModel):
    """Parameters for creating a single beam element."""
    model_config = ConfigDict(extra="forbid")

    begCoordinate: Coordinate2D = Field(description="Start point of the beam in the floor plan.")
    endCoordinate: Coordinate2D = Field(description="End point of the beam in the floor plan.")
    zCoordinate: float = Field(description="Elevation of the beam reference line in project units (meters).")
    offset: float | None = Field(None, description="Vertical offset of the beam from the reference line.")
    slantAngle: float | None = Field(None, description="Slant angle of the beam in radians.")
    arcAngle: float | None = Field(None, description="Arc angle of the beam in radians.")
    verticalCurveHeight: float | None = Field(None, description="Height of vertical curve of the beam.")


class BeamWithDetails(BaseModel):
    """Parameters for modifying a single existing beam element."""
    model_config = ConfigDict(extra="forbid")

    elementId: ElementId = Field(description="ID of the beam element to modify.")
    begCoordinate: Coordinate2D | None = Field(None, description="New start point of the beam.")
    endCoordinate: Coordinate2D | None = Field(None, description="New end point of the beam.")
    level: float | None = Field(None, description="New elevation of the beam reference line.")
    offset: float | None = Field(None, description="New vertical offset from the reference line.")
    slantAngle: float | None = Field(None, description="New slant angle in radians.")
    arcAngle: float | None = Field(None, description="New arc angle in radians.")
    verticalCurveHeight: float | None = Field(None, description="New vertical curve height.")


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

class WindowData(BaseModel):
    """Parameters for creating a single window element inside a host wall."""
    model_config = ConfigDict(extra="forbid")

    ownerWallId: ElementId = Field(description="ID of the host wall element that will contain the window.")
    centerOffset: float = Field(
        ge=0,
        description="Horizontal distance from the start of the wall to the center of the window, in project units.",
    )
    sillHeight: float | None = Field(None, description="Height of the window sill from the wall bottom in project units.")
    width: float | None = Field(None, gt=0, description="Width of the window in project units.")
    height: float | None = Field(None, gt=0, description="Height of the window opening in project units.")


class WindowWithDetails(BaseModel):
    """Parameters for modifying a single existing window element."""
    model_config = ConfigDict(extra="forbid")

    elementId: ElementId = Field(description="ID of the window element to modify.")
    width: float | None = Field(None, gt=0, description="New width of the window.")
    height: float | None = Field(None, gt=0, description="New height of the window opening.")
    sillHeight: float | None = Field(None, description="New sill height from the wall bottom.")
    centerOffset: float | None = Field(None, ge=0, description="New horizontal center offset from wall start.")


# ---------------------------------------------------------------------------
# Doors
# ---------------------------------------------------------------------------

class DoorData(BaseModel):
    """Parameters for creating a single door element inside a host wall."""
    model_config = ConfigDict(extra="forbid")

    ownerWallId: ElementId = Field(description="ID of the host wall element that will contain the door.")
    centerOffset: float = Field(
        ge=0,
        description="Horizontal distance from the start of the wall to the center of the door, in project units.",
    )
    sillHeight: float | None = Field(None, description="Height of the door sill from the wall bottom (usually 0).")
    width: float | None = Field(None, gt=0, description="Width of the door in project units.")
    height: float | None = Field(None, gt=0, description="Height of the door opening in project units.")


class DoorWithDetails(BaseModel):
    """Parameters for modifying a single existing door element."""
    model_config = ConfigDict(extra="forbid")

    elementId: ElementId = Field(description="ID of the door element to modify.")
    width: float | None = Field(None, gt=0, description="New width of the door.")
    height: float | None = Field(None, gt=0, description="New height of the door opening.")
    sillHeight: float | None = Field(None, description="New sill height from the wall bottom.")
    centerOffset: float | None = Field(None, ge=0, description="New horizontal center offset from wall start.")


# ---------------------------------------------------------------------------
# Openings
# ---------------------------------------------------------------------------

class OpeningData(BaseModel):
    """Parameters for creating a single opening element in a host element (wall, beam, column, etc.)."""
    model_config = ConfigDict(extra="forbid")

    ownerElementId: ElementId = Field(description="ID of the host element (wall, beam, or column) to cut the opening into.")
    basePoint: Coordinate3D = Field(description="3D insertion point of the opening in project units.")
    width: float | None = Field(None, gt=0, description="Width of the opening in project units.")
    height: float | None = Field(None, gt=0, description="Height of the opening in project units.")


# ---------------------------------------------------------------------------
# Morphs
# ---------------------------------------------------------------------------

class MorphData(BaseModel):
    """Parameters for creating a simple box-shaped morph element."""
    model_config = ConfigDict(extra="forbid")

    basePoint: Coordinate3D = Field(description="3D bottom-left-front corner of the morph bounding box in project units.")
    size: Dimensions3D = Field(description="Width (x), depth (y), and height (z) of the morph in project units.")
    buildingMaterialId: AttributeId | None = Field(None, description="Attribute ID of the building material for the morph.")


class MorphWithDetails(BaseModel):
    """Parameters for modifying a single existing morph element."""
    model_config = ConfigDict(extra="forbid")

    elementId: ElementId = Field(description="ID of the morph element to modify.")
    translation: Coordinate3D | None = Field(None, description="3D translation vector to move the morph.")
    rotationDegreesZ: float | None = Field(None, description="Rotation around the Z axis in degrees.")
    buildingMaterialId: AttributeId | None = Field(None, description="New building material attribute ID.")


# ---------------------------------------------------------------------------
# Roofs
# ---------------------------------------------------------------------------

class RoofLevel(BaseModel):
    """A single height/angle level definition for a multi-plane roof."""
    model_config = ConfigDict(extra="forbid")

    levelHeight: float = Field(description="Height of this roof level above the base level in project units.")
    levelAngle: float = Field(gt=0, description="Pitch angle of this roof plane in radians. Must be greater than 0.")


class RoofData(BaseModel):
    """Parameters for creating a multi-plane roof element."""
    model_config = ConfigDict(extra="forbid")

    level: float = Field(description="Base elevation of the roof in project units (meters).")
    polygonCoordinates: List[Coordinate2D] = Field(
        min_length=3, description="Footprint polygon of the roof (minimum 3 points) in floor plan coordinates."
    )
    thickness: float | None = Field(None, gt=0, description="Thickness of the roof in project units.")
    polygonArcs: List[PolyArc] | None = Field(None, description="Arc segments of the footprint polygon.")
    holes: List[Hole2D] | None = Field(None, description="Holes (skylights, openings) in the roof polygon.")
    eavesOverhang: float | None = Field(None, description="Eaves overhang distance beyond the footprint polygon in project units.")
    levels: List[RoofLevel] | None = Field(
        None,
        min_length=1,
        max_length=16,
        description="Up to 16 roof pitch levels, each with a height and angle. Controls multi-plane roof geometry.",
    )
    structureType: Literal["Basic", "Composite"] | None = Field(
        None,
        description="Structure type: 'Basic' = single building material, 'Composite' = layered composite.",
    )
    buildingMaterialId: AttributeId | None = Field(None, description="Building material attribute ID (for 'Basic' structure).")
    compositeId: AttributeId | None = Field(None, description="Composite structure attribute ID (for 'Composite' structure).")


class RoofWithDetails(BaseModel):
    """Parameters for modifying a single existing multi-plane roof element."""
    model_config = ConfigDict(extra="forbid")

    elementId: ElementId = Field(description="ID of the roof element to modify.")
    level: float | None = Field(None, description="New base elevation of the roof.")
    thickness: float | None = Field(None, gt=0, description="New roof thickness.")
    eavesOverhang: float | None = Field(None, description="New eaves overhang distance.")
    levels: List[RoofLevel] | None = Field(None, min_length=1, max_length=16, description="New pitch level definitions.")
    structureType: Literal["Basic", "Composite"] | None = Field(None, description="New structure type.")
    buildingMaterialId: AttributeId | None = Field(None, description="New building material attribute ID.")
    compositeId: AttributeId | None = Field(None, description="New composite structure attribute ID.")
    polygonOutline: List[Coordinate2D] | None = Field(None, min_length=3, description="New footprint polygon.")
    polygonArcs: List[PolyArc] | None = Field(None, description="New arc segments of the footprint polygon.")
    holes: List[Hole2D] | None = Field(None, description="New holes in the roof polygon.")


# ---------------------------------------------------------------------------
# Slabs
# ---------------------------------------------------------------------------

class SlabData(BaseModel):
    """Parameters for creating a single slab element."""
    model_config = ConfigDict(extra="forbid")

    level: float = Field(description="Z coordinate of the slab reference line in project units (meters).")
    polygonCoordinates: List[Coordinate2D] = Field(
        min_length=3, description="Outline polygon of the slab (minimum 3 points) in floor plan coordinates."
    )
    thickness: float | None = Field(None, gt=0, description="Slab thickness in project units. Uses project default when omitted.")
    polygonArcs: List[PolyArc] | None = Field(None, description="Arc segments of the outline polygon.")
    holes: List[Hole2D] | None = Field(None, description="Holes (openings) cut into the slab polygon.")


class SlabWithDetails(BaseModel):
    """Parameters for modifying a single existing slab element."""
    model_config = ConfigDict(extra="forbid")

    elementId: ElementId = Field(description="ID of the slab element to modify.")
    zCoordinate: float | None = Field(None, description="New bottom elevation of the slab.")
    thickness: float | None = Field(None, gt=0, description="New thickness of the slab in project units.")
    structureType: Literal["Basic", "Composite"] | None = Field(
        None,
        description="Structure type: 'Basic' = single building material, 'Composite' = layered composite.",
    )
    buildingMaterialId: AttributeId | None = Field(None, description="New building material attribute ID.")
    compositeId: AttributeId | None = Field(None, description="New composite structure attribute ID.")
    polygonOutline: List[Coordinate2D] | None = Field(None, min_length=3, description="New outline polygon of the slab.")
    polygonArcs: List[PolyArc] | None = Field(None, description="New arc segments of the outline polygon.")
    holes: List[Hole2D] | None = Field(None, description="New holes in the slab polygon.")


# ---------------------------------------------------------------------------
# Columns (modify only)
# ---------------------------------------------------------------------------

class ColumnWithDetails(BaseModel):
    """Parameters for modifying a single existing column element."""
    model_config = ConfigDict(extra="forbid")

    elementId: ElementId = Field(description="ID of the column element to modify.")
    origin: Coordinate2D | None = Field(None, description="New floor plan position of the column axis.")
    zCoordinate: float | None = Field(None, description="New bottom elevation of the column.")
    height: float | None = Field(None, gt=0, description="New height of the column in project units.")
    bottomOffset: float | None = Field(None, description="New vertical offset of the column base from the floor level.")
    axisRotationAngle: float | None = Field(None, description="New rotation angle around the column axis in radians.")


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

class WitnessPoint(BaseModel):
    """A single reference point on an element for associative dimension creation."""
    model_config = ConfigDict(extra="forbid")

    elementId: ElementId = Field(description="ID of the element to attach the dimension witness point to.")
    line: bool | None = Field(None, description="Whether this witness point is on a line (edge) rather than a node.")
    inIndex: int | None = Field(None, description="Index of the edge or node within the element geometry.")
    special: int | None = Field(None, description="Special node flag (internal Tapir use).")
    nodeType: int | None = Field(None, description="Node type identifier (internal Tapir use).")
    nodeStatus: int | None = Field(None, description="Node status flags (internal Tapir use).")
    nodeId: float | None = Field(None, ge=0, description="Node ID (internal Tapir use).")


class AssociativeDimensionData(BaseModel):
    """Parameters for creating a single associative linear dimension."""
    model_config = ConfigDict(extra="forbid")

    referencePoint: Coordinate2D = Field(description="Base point for the dimension line placement in the floor plan.")
    direction: Coordinate2D = Field(description="Direction vector of the dimension line (e.g. {x:1, y:0} for horizontal).")
    witnessPoints: List[WitnessPoint] = Field(
        min_length=2,
        description="At least 2 element reference points to dimension between.",
    )
    floorIndex: float | None = Field(None, description="Floor index to place the dimension on. Defaults to current floor.")


class DimensionSectionPreset(str):
    """Valid preset values for CreateAssociativeDimensionsOnSection."""
    pass


class AssociativeDimensionOnSectionData(BaseModel):
    """Parameters for creating a single associative dimension on a section element."""
    model_config = ConfigDict(extra="forbid")

    sectionElementId: ElementId = Field(description="ID of the section/elevation view element to dimension.")
    referencePoint: Coordinate2D = Field(description="Base point for the dimension line placement.")
    preset: Literal[
        "WallCompositeFaces",
        "WallSkinBorders",
        "SlabCompositeFaces",
        "SlabSkinBorders",
        "BeamOrColumnRefLineEndPoints",
        "BeamOrColumnBoundingBoxCorners",
        "DoorWindowWallHoleCorners",
        "DoorWindowModelHotspots",
    ] = Field(
        description=(
            "Dimensioning preset to apply. "
            "'WallCompositeFaces'/'WallSkinBorders' = wall layer boundaries, "
            "'SlabCompositeFaces'/'SlabSkinBorders' = slab layer boundaries, "
            "'BeamOrColumnRefLineEndPoints'/'BeamOrColumnBoundingBoxCorners' = beam/column extent, "
            "'DoorWindowWallHoleCorners'/'DoorWindowModelHotspots' = opening geometry."
        )
    )
    direction: Coordinate2D | None = Field(None, description="Direction vector of the dimension line.")
    skinBorderIndices: List[int] | None = Field(
        None, min_length=1, description="Specific layer border indices for WallSkinBorders/SlabSkinBorders presets."
    )
    beginPlane: bool | None = Field(None, description="Include the starting boundary plane in the dimension.")
    totalSizePlane: bool | None = Field(None, description="Include total size dimension plane.")
    placeOnTop: bool | None = Field(None, description="Place dimension above the element instead of below.")


class WallThicknessDimensionData(BaseModel):
    """Parameters for creating a single wall thickness dimension."""
    model_config = ConfigDict(extra="forbid")

    wallId: ElementId = Field(description="ID of the wall element to add a thickness dimension to.")
    referencePoint: Coordinate2D = Field(description="Point on the dimension line in floor plan coordinates.")
    direction: Coordinate2D = Field(description="Direction vector perpendicular to the wall face.")


# ---------------------------------------------------------------------------
# Navigator / Layout
# ---------------------------------------------------------------------------

class DetailData(BaseModel):
    """Parameters for creating a single independent detail database."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Name of the detail view.")
    referenceId: str = Field(min_length=1, description="Reference ID (marker ID) displayed in the detail marker.")


class WorksheetData(BaseModel):
    """Parameters for creating a single independent worksheet database."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Name of the worksheet.")
    referenceId: str = Field(min_length=1, description="Reference ID displayed in the worksheet marker.")


class LayoutData(BaseModel):
    """Parameters for creating a single layout together with its master layout."""
    model_config = ConfigDict(extra="forbid")

    masterLayoutName: str = Field(min_length=1, description="Name of the master layout (template) to create or reuse.")
    layoutName: str = Field(min_length=1, description="Name of the layout sheet to create.")


class SubsetData(BaseModel):
    """Parameters for creating a single layout book subset (folder)."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Name of the subset.")
    parentNavigatorItemId: NavigatorItemId | None = Field(
        None, description="Navigator item ID of the parent subset. Omit to create at root level."
    )
    ownPrefix: str | None = Field(None, description="Custom prefix string for numbering layouts within this subset.")
    customNumber: str | None = Field(None, description="Custom number string for the subset.")


class DrawingData(BaseModel):
    """Parameters for creating a single drawing element on a layout from a navigator item."""
    model_config = ConfigDict(extra="forbid")

    navigatorItemId: NavigatorItemId = Field(
        description="Navigator item ID of the view (floor plan, section, etc.) to place as a drawing."
    )
    name: str = Field(min_length=1, description="Name of the drawing element on the layout.")
    position: Coordinate2D = Field(description="Position of the drawing on the layout sheet in layout units.")
    layoutDatabaseId: DatabaseId | None = Field(
        None, description="Database ID of the target layout. Omit to place on the currently active layout."
    )
    scale: float | None = Field(None, gt=0, description="Drawing scale (e.g. 0.005 for 1:200). Defaults to the view's own scale.")
