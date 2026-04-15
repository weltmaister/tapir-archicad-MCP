from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tapir_archicad_mcp.tools.custom import tapir_parity  # noqa: F401
from tapir_archicad_mcp.tools.tool_registry import TOOL_DISCOVERY_CATALOG, get_tool_entry


EXPECTED_TOOLS = {
    "app_get_archicad_location",
    "app_quit_archicad",
    "app_change_window",
    "project_get_project_info",
    "project_close_project",
    "project_save_project",
    "project_set_geo_location",
    "project_ifc_file_operation",
    "project_print_view",
    "navigator_fit_in_window",
    "dev_generate_documentation",
    "project_get_design_options",
    "project_get_design_option_sets",
    "project_get_design_option_combinations",
    "elements_get_element_preview_image",
    "favorites_get_favorite_preview_image",
    "elements_get_room_image",
    "elements_set_element_notification_client",
    "elements_remove_element_notification_client",
    "view_set3_d_cut_planes",
}


class TapirParityTests(unittest.TestCase):
    def test_all_missing_parity_tools_are_registered(self) -> None:
        for tool_name in EXPECTED_TOOLS:
            with self.subTest(tool=tool_name):
                entry = get_tool_entry(tool_name)
                self.assertIsNotNone(entry)

    def test_project_get_project_info_is_discoverable(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "project_get_project_info"), None)
        self.assertIsNotNone(tool)
        self.assertEqual(tool["title"], "GetProjectInfo")
        self.assertEqual(tool["input_schema"]["required"], ["port"])

    def test_app_change_window_exposes_window_type_parameter(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "app_change_window"), None)
        self.assertIsNotNone(tool)
        params_properties = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("windowType", params_properties)

    def test_view_set_3d_cut_planes_exposes_cut_planes_parameter(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "view_set3_d_cut_planes"), None)
        self.assertIsNotNone(tool)
        params_properties = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("cutPlanes", params_properties)


if __name__ == "__main__":
    unittest.main()
