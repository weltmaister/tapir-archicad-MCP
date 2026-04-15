from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tapir_archicad_mcp.tools.custom import tapir_extensions  # noqa: F401
from tapir_archicad_mcp.tools.tool_registry import TOOL_DISCOVERY_CATALOG, get_tool_entry


class TapirExtensionsTests(unittest.TestCase):
    def test_elements_create_labels_is_registered(self) -> None:
        entry = get_tool_entry("elements_create_labels")
        self.assertIsNotNone(entry.params_model)

    def test_elements_create_labels_is_discoverable(self) -> None:
        tool = next((item for item in TOOL_DISCOVERY_CATALOG if item["name"] == "elements_create_labels"), None)
        self.assertIsNotNone(tool)
        self.assertEqual(tool["title"], "CreateLabels")
        self.assertIn("labelsData", tool["input_schema"]["properties"]["params"]["properties"])


if __name__ == "__main__":
    unittest.main()
