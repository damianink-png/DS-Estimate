"""Fast source-only regression for structural section patterns (no OCCT needed)."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cad_backend.stock_patterns import orthogonal_section_kind


def close(points):
    return points + [points[0]]


class StockPatternTests(unittest.TestCase):
    def profiles(self):
        return {
            'angle': [(0,0),(40,0),(40,5),(5,5),(5,40),(0,40)],
            'channel': [(0,0),(40,0),(40,5),(5,5),(5,35),(40,35),(40,40),(0,40)],
            'tee': [(0,0),(5,0),(5,25),(20,25),(20,30),(-15,30),(-15,25),(0,25)],
            'i-section': [(0,0),(40,0),(40,5),(23,5),(23,35),(40,35),(40,40),(0,40),(0,35),(17,35),(17,5),(0,5)],
        }

    def test_four_known_outlines(self):
        for expected, vertices in self.profiles().items():
            with self.subTest(expected=expected):
                section = orthogonal_section_kind(close(vertices), 0.002)
                self.assertIsNotNone(section)
                self.assertEqual(section['kind'], expected)
                self.assertGreater(section['sectionAreaMm2'], 0)

    def test_rotation_in_cross_section_plane(self):
        angle = math.radians(25)
        verts = self.profiles()['channel']
        rotated = [(x*math.cos(angle)-y*math.sin(angle),
                    x*math.sin(angle)+y*math.cos(angle)) for x,y in verts]
        self.assertEqual(orthogonal_section_kind(close(rotated), 0.002)['kind'], 'channel')

    def test_arbitrary_zigzag_does_not_get_standard_name(self):
        zigzag = [(0,0),(40,0),(40,5),(30,5),(30,10),(20,10),
                  (20,15),(10,15),(10,20),(0,20)]
        self.assertIsNone(orthogonal_section_kind(close(zigzag), 0.002))

    def test_rectangle_and_open_profile_are_not_structural_ones(self):
        self.assertIsNone(orthogonal_section_kind(close([(0,0),(10,0),(10,10),(0,10)]), 0.002))
        self.assertIsNone(orthogonal_section_kind([(0,0),(30,0),(30,5),(5,5)], 0.002))


def run_suite():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StockPatternTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise AssertionError('Raw-stock pattern regressions failed')


if __name__ == '__main__':
    run_suite()
