"""Fast source-only regression for structural section patterns (no OCCT needed)."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cad_backend.stock_patterns import orthogonal_section_kind, convex_polygon_section_kind
from cad_backend.stock_recognition import _classify_section, _recognize_axis_stock, recognize_stock
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

    def test_zee_and_top_hat_section_library_patterns(self):
        # Closed straight-edge cross-sections: strict topology, not catalogue
        # procurement. Check rotations/reflections without loosening tolerances.
        profiles={
            'zee':[(0,0),(20,0),(20,35),(30,35),(30,40),
                   (10,40),(10,5),(0,5)],
            'hat':[(0,0),(10,0),(10,30),(30,30),(30,0),
                   (40,0),(40,5),(35,5),(35,35),(5,35),(5,5),(0,5)],
        }
        for kind,vertices in profiles.items():
            for angle in (0,math.radians(31),math.radians(90)):
                for mirrored in (False,True):
                    points=[((-x if mirrored else x)*math.cos(angle)-y*math.sin(angle),
                             (-x if mirrored else x)*math.sin(angle)+y*math.cos(angle))
                            for x,y in vertices]
                    with self.subTest(kind=kind,angle=angle,mirrored=mirrored):
                        measured=orthogonal_section_kind(close(points),.002)
                        self.assertIsNotNone(measured)
                        self.assertEqual(measured['kind'],kind)
                        self.assertGreater(measured['sectionAreaMm2'],0)

    def test_corner_bevel_is_blank_candidate_not_certified_bar(self):
        # A lengthwise 5x5 corner chamfer does not make a 40x40 core an
        # arbitrary polygon bar. Nor does it prove saw/milling operation.
        points=close([(0,0),(40,0),(40,40),(5,40),(0,35)])
        edges=[(points[i:i+2],False,None) for i in range(len(points)-1)]
        geometry=_classify_section(edges,.002)
        self.assertEqual(geometry['kind'],'beveled-rectangle')
        self.assertAlmostEqual(geometry['blankSectionAreaMm2'],1600)
        with patch('cad_backend.stock_recognition._section_edges',return_value=edges), \
             patch('cad_backend.stock_recognition._measured_solid_volume',
                   return_value=geometry['sectionAreaMm2']*500):
            result=recognize_stock(None,(0,0,0,40,40,500))
        self.assertEqual(result['kind'],'unknown')
        self.assertEqual(result['rawStockCandidate']['kind'],'square-bar')
        self.assertEqual(result['rawStockCandidate']['confidence'],'geometric-blank-candidate')
        self.assertEqual(result['finishedSectionEvidence']['bevelCount'],1)

    def test_inner_diagonal_or_large_removed_corner_is_not_ignored(self):
        from cad_backend.stock_patterns import beveled_rectangle_section_kind
        invalid=[
            [(0,0),(40,0),(40,40),(20,35),(0,40)],
            [(0,0),(40,0),(40,40),(20,40),(0,20)],
        ]
        for vertices in invalid:
            with self.subTest(vertices=vertices):
                self.assertIsNone(beveled_rectangle_section_kind(close(vertices),.002))

    def test_rotated_rhs_sections_and_offset_hole(self):
        # Real OCCT sections may be rotated inside the cutting plane.
        # The outer and inner loops must have a common geometric centre,
        # and an eccentric hole must not be certified as RHS.
        angle = math.radians(37)
        c, s = math.cos(angle), math.sin(angle)

        def edges(w, h, offset=(0, 0)):
            ox, oy = offset
            vertices = [(-w/2+ox, -h/2+oy), (w/2+ox, -h/2+oy),
                        (w/2+ox, h/2+oy), (-w/2+ox, h/2+oy)]
            points = [(x*c-y*s, x*s+y*c) for x, y in vertices]
            return [([points[i], points[(i+1) % 4]], False, None)
                    for i in range(4)]

        good = _classify_section(edges(80, 40)+edges(74, 34), 0.002)
        self.assertIsNotNone(good)
        self.assertEqual(good['kind'], 'rectangular-hollow')
        self.assertAlmostEqual(good['wallMm'], 3, places=3)
        bad = _classify_section(edges(80, 40)+edges(74, 34, (0.5, 0)), 0.002)
        self.assertIsNone(bad)

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

    def test_independent_volume_rejects_hidden_pocket_between_samples(self):
        # All five sampled cross-sections look identical, but the B-Rep
        # volume reveals a slot between sampling planes.
        pts=[(0,0),(40,0),(40,40),(0,40),(0,0)]
        edges=[(pts[i:i+2],False,None) for i in range(4)]
        with patch('cad_backend.stock_recognition._section_edges',return_value=edges), \
             patch('cad_backend.stock_recognition._measured_solid_volume',return_value=1400000):
            result=recognize_stock(object(),(0,0,0,40,40,1000))
        self.assertEqual(result['kind'],'unknown')
        self.assertIn('volume',result['reason'])

    def test_independent_volume_evaluated_only_once_for_matching_sections(self):
        # Large assemblies must not re-run expensive OCCT B-Rep volume
        # once for candidate stock and again for the final volume gate.
        pts=[(0,0),(40,0),(40,40),(0,40),(0,0)]
        edges=[(pts[i:i+2],False,None) for i in range(4)]
        with patch('cad_backend.stock_recognition._section_edges',return_value=edges), \
             patch('cad_backend.stock_recognition._measured_solid_volume',return_value=1600000) as volume:
            result=recognize_stock(object(),(0,0,0,40,40,1000))
        self.assertEqual(result['kind'],'square-bar')
        volume.assert_called_once()

    def test_volume_failure_remains_unknown_not_free_stock(self):
        pts=[(0,0),(40,0),(40,40),(0,40),(0,0)]
        edges=[(pts[i:i+2],False,None) for i in range(4)]
        with patch('cad_backend.stock_recognition._section_edges',return_value=edges), \
             patch('cad_backend.stock_recognition._measured_solid_volume',side_effect=RuntimeError('OCCT unavailable')):
            result=recognize_stock(object(),(0,0,0,40,40,1000))
        self.assertEqual(result['kind'],'unknown')
        self.assertIn('Independent volume check unavailable',result['reason'])

    def test_changing_section_volume_failure_remains_explicit(self):
        def rect(w):
            pts=[(0,0),(w,0),(w,40),(0,40),(0,0)]
            return [(pts[i:i+2],False,None) for i in range(4)]
        def sample(shape,bounds,axis,fraction):
            return rect(35 if fraction < .2 else 40)
        with patch('cad_backend.stock_recognition._section_edges',side_effect=sample), \
             patch('cad_backend.stock_recognition._measured_solid_volume',side_effect=ValueError('bad volume')):
            result=recognize_stock(object(),(0,0,0,40,40,1000))
        self.assertEqual(result['kind'],'unknown')
        self.assertIn('Independent volume check unavailable',result['reason'])

    def test_independent_volume_accepts_prismatic_bar(self):
        pts=[(0,0),(40,0),(40,40),(0,40),(0,0)]
        edges=[(pts[i:i+2],False,None) for i in range(4)]
        with patch('cad_backend.stock_recognition._section_edges',return_value=edges), \
             patch('cad_backend.stock_recognition._measured_solid_volume',return_value=1600000):
            result=recognize_stock(object(),(0,0,0,40,40,1000))
        self.assertEqual(result['kind'],'square-bar')

    def test_long_thin_plate_with_removed_volume_keeps_plate_geometry(self):
        # Measured major B-Rep faces establish the sheet thickness; five
        # flat cross-sections alone wrongly suggest a raw flat bar when end
        # cuts remove volume. Do not infer purchased stock or cutting time.
        rect=[(0,0),(60,0),(60,10),(0,10),(0,0)]
        edges=[(rect[i:i+2],False,None) for i in range(4)]
        bounds=(0,0,0,60,10,565)
        with patch('cad_backend.stock_recognition._section_edges',return_value=edges), \
             patch('cad_backend.stock_recognition._measured_solid_volume',
                   return_value=320000):
            plate=_recognize_axis_stock(object(),bounds,{'kind':'plate-outline','thicknessMm':10})
            not_measured=_recognize_axis_stock(object(),bounds,None)
            wrong_thickness=_recognize_axis_stock(object(),bounds,{'kind':'plate-outline','thicknessMm':9})
        self.assertEqual(plate['kind'],'plate-candidate')
        self.assertEqual(plate['confidence'],'candidate')
        self.assertAlmostEqual(plate['thicknessMm'],10)
        self.assertAlmostEqual(plate['widthMm'],60)
        self.assertAlmostEqual(plate['lengthMm'],565)
        self.assertEqual(plate['rawStockCandidate']['kind'],'flat-section')
        self.assertNotIn('cutTimeH',plate)
        self.assertEqual(not_measured['kind'],'unknown')
        self.assertEqual(wrong_thickness['kind'],'unknown')

    def test_plate_candidate_requires_consistent_measured_thickness(self):
        bounds=(0,0,0,100,50,10)
        good={'kind':'plate-outline','thicknessMm':10}
        result=recognize_stock(None,bounds,plate_hint=good)
        self.assertEqual(result['kind'],'plate-candidate')
        self.assertEqual(result['confidence'],'candidate')
        for bad in (None, {}, {'kind':'plate-outline','thicknessMm':5},
                    {'kind':'plate-outline','thicknessMm':float('nan')},
                    {'kind':'plate-outline','thicknessMm':0},
                    {'kind':'plate-outline','thicknessMm':'10'}):
            with self.subTest(bad=bad):
                self.assertEqual(recognize_stock(None,bounds,plate_hint=bad)['kind'],'unknown')

    def test_boolean_is_not_a_measured_plate_thickness(self):
        # Python bool subclasses int: True == 1 must not certify a 1 mm plate.
        bounds=(0,0,0,100,50,1)
        self.assertEqual(
            recognize_stock(None,bounds,plate_hint={'kind':'plate-outline','thicknessMm':1})['kind'],
            'plate-candidate')
        for value in (True, False):
            self.assertEqual(
                recognize_stock(None,bounds,plate_hint={'kind':'plate-outline','thicknessMm':value})['kind'],
                'unknown')

    def test_sheared_parallelogram_not_certified_as_rectangular_stock(self):
        # 80 x 40 with a 0.35 mm skew: area and perimeter almost
        # identical to a rectangle. A bbox heuristic falsely certifies it.
        pts=[(0,0),(80,0),(80.35,40),(0.35,40),(0,0)]
        edges=[(pts[i:i+2],False,None) for i in range(4)]
        self.assertIsNone(_classify_section(edges,.002))
        # True rectangular geometry still works, including split edges.
        rect=[(0,0),(40,0),(80,0),(80,40),(0,40),(0,0)]
        edges=[(rect[i:i+2],False,None) for i in range(len(rect)-1)]
        self.assertEqual(_classify_section(edges,.002)['kind'],'rectangular-bar')

    def test_rectangle_and_open_profile_are_not_structural_ones(self):
        self.assertIsNone(orthogonal_section_kind(close([(0,0),(10,0),(10,10),(0,10)]), 0.002))
        self.assertIsNone(orthogonal_section_kind([(0,0),(30,0),(30,5),(5,5)], 0.002))


    def test_nonstandard_convex_section_never_gets_rectangle_label(self):
        # Exact cross section from Earthpress 5x5x50 ribs: four sides,
        # measured metal area 15 mm2 (rather than 25 mm2 from bounding box).
        points=[(0,0),(5,0),(3,3),(0,5),(0,0)]
        hint=convex_polygon_section_kind(points,.002)
        self.assertEqual(hint['kind'],'polygon-bar')
        self.assertAlmostEqual(hint['sectionAreaMm2'],15.0)
        edges=[(points[i:i+2],False,None) for i in range(len(points)-1)]
        self.assertEqual(_classify_section(edges,.002)['kind'],'polygon-bar')

    def test_polygonal_bar_requires_repeated_sections_and_independent_volume(self):
        points=[(0,0),(5,0),(3,3),(0,5),(0,0)]
        edges=[(points[i:i+2],False,None) for i in range(len(points)-1)]
        with patch('cad_backend.stock_recognition._section_edges',return_value=edges), \
             patch('cad_backend.stock_recognition._measured_solid_volume',return_value=750) as measure:
            result=recognize_stock(object(),(0,0,0,5,5,50))
        self.assertEqual(result['kind'],'polygon-bar')
        self.assertEqual(result['confidence'],'cross-section-consistent')
        measure.assert_called_once()
        self.assertAlmostEqual(result['sectionAreaMm2'],15)
        self.assertEqual(result['lengthMm'],50)
        with patch('cad_backend.stock_recognition._section_edges',return_value=edges), \
             patch('cad_backend.stock_recognition._measured_solid_volume',return_value=600):
            missing=recognize_stock(object(),(0,0,0,5,5,50))
        self.assertEqual(missing['kind'],'unknown')
        self.assertIn('volume',missing['reason'])

    def test_polygon_profile_rejects_concave_or_nearly_rectangle(self):
        concave=[(0,0),(6,0),(6,6),(3,3),(0,6),(0,0)]
        self.assertIsNone(convex_polygon_section_kind(concave,.002))
        near_rectangle=[(0,0),(80,0),(80.35,40),(0.35,40),(0,0)]
        self.assertIsNone(convex_polygon_section_kind(near_rectangle,.002))
        unclosed=[(0,0),(6,0),(6,6),(0,6)]
        self.assertIsNone(convex_polygon_section_kind(unclosed,.002))

    def test_oversized_finished_solid_preserves_core_but_never_claims_stock(self):
        # Real Earthpress bodies 10/11 contain coaxial 40/34 mm cylinder faces,
        # yet the final volume exceeds the straight pipe prism. Recognition of
        # this core must NOT turn a welded/machined item into a saw-only part.
        def ring(radius):
            xy=[(radius*math.cos(2*math.pi*i/64),
                 radius*math.sin(2*math.pi*i/64)) for i in range(65)]
            return (xy,True,radius)
        edges=[ring(20),ring(17)]
        with patch('cad_backend.stock_recognition._section_edges',return_value=edges), \
             patch('cad_backend.stock_recognition._measured_solid_volume',return_value=191581.48) as measure:
            result=recognize_stock(object(),(0,0,0,40,40,369.371))
        self.assertEqual(result['kind'],'unknown')
        self.assertNotIn('rawStockCandidate',result)
        core=result.get('coreSectionCandidate')
        self.assertIsNotNone(core)
        self.assertEqual(core['kind'],'round-tube')
        self.assertAlmostEqual(core['diameterMm'],40)
        self.assertAlmostEqual(core['wallMm'],3)
        self.assertEqual(core['confidence'],'geometric-core-only')
        self.assertGreater(core['finishedVolumeMm3'],core['sectionPrismVolumeMm3'])
        measure.assert_called_once()


def run_suite():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StockPatternTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise AssertionError('Raw-stock pattern regressions failed')


if __name__ == '__main__':
    run_suite()
