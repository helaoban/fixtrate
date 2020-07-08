import argparse
from .gen_types import generate


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "spec_path",
        type=str,
        nargs=1
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str
    )
    return parser.parse_args()


def run():
    args = get_args()
    generate(args.spec_path[0], args.output)
