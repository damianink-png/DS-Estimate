"""Fast source-only regression for structural section patterns (no OCCT needed)."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cad_backend.stock_patterns import orthogonal_section_kind
from cad_backend.stock_recognition import _classify_section, recognize_stock
from unittest.mock import patch


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

    def test_mirrored_and_reversed_channel(self):
        base = self.profiles()['channel']
        for vertices in ([(40-x,y) for x,y in base],
                         list(reversed(base)),
                         [(y,x) for x,y in base]):
            self.assertEqual(orthogonal_section_kind(close(vertices), .002)['kind'], 'channel')

    def test_invalid_coordinates_are_unknown(self):
        base = self.profiles()['angle']
        for invalid in (float('nan'), float('inf'), -float('inf')):
            points = list(base)
            points[1] = (invalid, 0)
            self.assertIsNone(orthogonal_section_kind(close(points), .002))
        self.assertIsNone(orthogonal_section_kind(close(base), 0))

    def test_offcenter_hollow_is_unknown(self):
        def square(x0, y0, side):
            points=[(x0,y0),(x0+side,y0),(x0+side,y0+side),
                    (x0,y0+side),(x0,y0)]
            return [(points[i:i+2], False, None) for i in range(4)]
        good = _classify_section(square(0,0,80)+square(2,2,76), .002)
        self.assertEqual(good['kind'], 'square-hollow')
        # 0.5 mm offset is only 0.6% of the 80 mm outer dimension,
        # but is 25% of a 2 mm wall: do not certify SHS.
        bad = _classify_section(square(0,0,80)+square(2.5,2,76), .002)
        self.assertIsNone(bad)

    def test_five_samples_reject_near_end_section_change(self):
        def rect(w, h):
            pts=[(0,0),(w,0),(w,h),(0,h),(0,0)]
            return [(pts[i:i+2],False,None) for i in range(4)]
        calls=[]
        def sample(shape,bounds,axis,fraction):
            calls.append(fraction)
            return rect(40,20 if fraction < .2 else 40)
        with patch('cad_backend.stock_recognition._section_edges',side_effect=sample):
            result=recognize_stock(None,(0,0,0,40,40,1000))
        self.assertEqual(result['kind'],'unknown')
        self.assertIn('changes',result['reason'])
        self.assertEqual(calls,[.10,.25,.50,.75,.90])

    def test_five_samples_constant_section(self):
        def rect():
            pts=[(0,0),(40,0),(40,40),(0,40),(0,0)]
            return [(pts[i:i+2],False,None) for i in range(4)]
        with patch('cad_backend.stock_recognition._section_edges',return_value=rect()) as mocked:
            result=recognize_stock(None,(0,0,0,40,40,1000))
        self.assertEqual(result['kind'],'square-bar')
        self.assertEqual(mocked.call_count,5)
        self.assertEqual(result['lengthMm'],1000)

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
