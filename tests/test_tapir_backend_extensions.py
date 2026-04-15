from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tapir_archicad_mcp.tools.custom import tapir_backend_extensions  # noqa: F401
from tapir_archicad_mcp.tools.tool_registry import TOOL_DISCOVERY_CATALOG, get_tool_entry


EXPECTED_TOOLS = {
    "elements_create_walls",
    "elements_modify_walls",
    "elements_create_beams",
    "elements_modify_beams",
    "elements_create_windows",
    "elements_modify_windows",
    "elements_create_doors",
    "elements_modify_doors",
    "elements_create_openings",
    "elements_create_morphs",
    "elements_create_roofs",
    "elements_create_associative_dimensions",
    "elements_create_associative_dimensions_on_section",
    "elements_create_wall_thickness_dimensions",
    "elements_modify_slabs",
    "elements_modify_columns",
    "elements_modify_morphs",
    "elements_modify_roofs",
    "navigator_create_details",
    "navigator_create_worksheets",
    "layout_create_layouts",
    "layout_create_subsets",
    "layout_create_drawings",
}


class TapirBackendExtensionsTests(unittest.TestCase):
    def test_all_backend_extension_tools_are_registered(self) -> None:
        for tool_name in EXPECTED_TOOLS:
            with self.subTest(tool=tool_name):
                self.assertIsNotNone(get_tool_entry(tool_name))

    def test_elements_create_walls_requires_walls_data(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "elements_create_walls"), None)
        self.assertIsNotNone(tool)
        params_properties = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("wallsData", params_properties)
        self.assertEqual(tool["input_schema"]["properties"]["params"]["required"], ["wallsData"])

    def test_layout_create_drawings_requires_drawings_data(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "layout_create_drawings"), None)
        self.assertIsNotNone(tool)
        params_properties = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("drawingsData", params_properties)
        self.assertEqual(tool["input_schema"]["properties"]["params"]["required"], ["drawingsData"])

    def test_elements_modify_windows_requires_windows_with_details(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "elements_modify_windows"), None)
        self.assertIsNotNone(tool)
        params_properties = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("windowsWithDetails", params_properties)
        self.assertEqual(tool["input_schema"]["properties"]["params"]["required"], ["windowsWithDetails"])

    def test_elements_create_morphs_requires_morphs_data(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "elements_create_morphs"), None)
        self.assertIsNotNone(tool)
        params_properties = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("morphsData", params_properties)
        self.assertEqual(tool["input_schema"]["properties"]["params"]["required"], ["morphsData"])

    def test_elements_create_roofs_requires_roofs_data(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "elements_create_roofs"), None)
        self.assertIsNotNone(tool)
        params_properties = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("roofsData", params_properties)
        self.assertEqual(tool["input_schema"]["properties"]["params"]["required"], ["roofsData"])

    def test_elements_create_associative_dimensions_requires_dimensions_data(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "elements_create_associative_dimensions"), None)
        self.assertIsNotNone(tool)
        params_properties = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("dimensionsData", params_properties)
        self.assertEqual(tool["input_schema"]["properties"]["params"]["required"], ["dimensionsData"])

    def test_elements_create_associative_dimensions_on_section_requires_dimensions_data(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "elements_create_associative_dimensions_on_section"), None)
        self.assertIsNotNone(tool)
        params_properties = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("dimensionsData", params_properties)
        self.assertEqual(tool["input_schema"]["properties"]["params"]["required"], ["dimensionsData"])

    def test_elements_modify_slabs_requires_slabs_with_details(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "elements_modify_slabs"), None)
        self.assertIsNotNone(tool)
        params_properties = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("slabsWithDetails", params_properties)
        self.assertEqual(tool["input_schema"]["properties"]["params"]["required"], ["slabsWithDetails"])

    def test_elements_modify_roofs_requires_roofs_with_details(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "elements_modify_roofs"), None)
        self.assertIsNotNone(tool)
        params_properties = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("roofsWithDetails", params_properties)
        self.assertEqual(tool["input_schema"]["properties"]["params"]["required"], ["roofsWithDetails"])


if __name__ == "__main__":
    unittest.main()
