"""Fast conservative lookup of potential rigidly identical OCCT solids.

Indexing by volume and surface area (rotation-invariant) is only a filter.
It NEVER proves identical geometry. Matching must still call IsPartner or an
independent exact rigid B-Rep verifier. Neighbor buckets avoid rounding-edge
false negatives. Standard library only: exercises CI without pythonocc.
"""
from collections import defaultdict
import math


class ShapeCandidateIndex:
    def __init__(self, scale=100000):
        self.scale = scale
        self.buckets = defaultdict(list)
        self.measures = {}

    def _bucket(self, volume, area):
        if not (math.isfinite(volume) and volume > 0 and math.isfinite(area) and area > 0):
            raise ValueError("Volume/area must be positive finite")
        return (round(math.log(volume) * self.scale), round(math.log(area) * self.scale))

    def insert(self, index, volume, area):
        if index in self.measures:
            raise ValueError("Group indexed twice")
        key = self._bucket(volume, area)
        self.measures[index] = (float(volume), float(area))
        self.buckets[key].append(index)

    def candidates(self, volume, area, relative_tolerance=1e-6):
        x, y = self._bucket(volume, area)
        matching = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for idx in self.buckets.get((x + dx, y + dy), ()):
                    old_v, old_a = self.measures[idx]
                    if (abs(volume - old_v) <= max(1e-7, max(volume, old_v)*relative_tolerance)
                        and abs(area - old_a) <= max(1e-7, max(area, old_a)*relative_tolerance)):
                        matching.append(idx)
        # Deterministic independent of hash insertion order.
        return sorted(matching)
