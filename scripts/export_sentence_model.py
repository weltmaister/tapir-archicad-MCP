from __future__ import annotations

import argparse
from pathlib import Path

from sentence_transformers import SentenceTransformer


MODEL_NAME = "all-MiniLM-L6-v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the semantic search sentence-transformer model into a self-contained folder."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Target directory where the model should be saved.",
    )
    parser.add_argument(
        "--model-name",
        default=MODEL_NAME,
        help="Sentence-transformer model name to export.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    model = SentenceTransformer(args.model_name)
    model.save(str(output_dir))
    print(f"Exported sentence-transformer model '{args.model_name}' to {output_dir}")


if __name__ == "__main__":
    main()
