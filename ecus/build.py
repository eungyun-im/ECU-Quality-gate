"""Build configuration: a version and the defects planted in it.

Both builds run the same source. A seeded defect is a switch that the ECU code
checks at the exact place where the faulty behavior belongs.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_BUILD = ROOT / "builds" / "v1.0.0.yaml"


@dataclass(frozen=True)
class Build:
    version: str
    seeded: frozenset = frozenset()

    def has(self, defect_id):
        return defect_id in self.seeded

    @property
    def version_bytes(self):
        return [int(part) for part in self.version.split(".")[:3]]


def load_build(path=REFERENCE_BUILD):
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    seeded = frozenset(d["id"] for d in raw.get("seeded_defects") or [])
    return Build(version=str(raw["version"]), seeded=seeded)
