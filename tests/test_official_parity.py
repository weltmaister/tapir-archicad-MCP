from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tapir_archicad_mcp.tools.custom import official_parity  # noqa: F401
from tapir_archicad_mcp.tools.tool_registry import TOOL_DISCOVERY_CATALOG, get_tool_entry


class OfficialParityTests(unittest.TestCase):
    def test_basic_tools_are_registered(self) -> None:
        self.assertIsNotNone(get_tool_entry("basic_get_product_info"))
        self.assertIsNotNone(get_tool_entry("basic_is_alive"))

    def test_execute_add_on_command_is_registered(self) -> None:
        entry = get_tool_entry("dev_execute_add_on_command")
        self.assertIsNotNone(entry.params_model)

    def test_basic_get_product_info_is_discoverable(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "basic_get_product_info"), None)
        self.assertIsNotNone(tool)
        self.assertEqual(tool["title"], "GetProductInfo")
        self.assertEqual(tool["input_schema"]["required"], ["port"])

    def test_execute_add_on_command_exposes_add_on_command_id(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "dev_execute_add_on_command"), None)
        self.assertIsNotNone(tool)
        params = tool["input_schema"]["properties"]["params"]["properties"]
        self.assertIn("addOnCommandId", params)


if __name__ == "__main__":
    unittest.main()
