import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'cad_backend'))
from blank_candidates import envelope_candidate


class BlankCandidates(unittest.TestCase):
    def test_material_volume_and_removal(self):
        result = envelope_candidate([20, 100, 10], 15000)
        self.assertEqual(result['dimensionsMm'], [100, 20, 10])
        self.assertEqual(result['volumeMm3'], 20000)
        self.assertEqual(result['removedVolumeMm3'], 5000)
        self.assertEqual(result['utilization'], .75)
        self.assertTrue(result['requiresReview'])
        self.assertEqual(result['confidence'], 'envelope-only')

    def test_incompatible_volume_is_rejected(self):
        self.assertIsNone(envelope_candidate([10, 10, 10], 1100))

    def test_invalid_dimensions_are_rejected(self):
        for dims in ([10, 0, 10], [-1, 10, 10], [math.nan, 1, 1],
                     [math.inf, 1, 1], [True, 10, 10], [10, 10], None):
            with self.subTest(dims=dims):
                self.assertIsNone(envelope_candidate(dims, 100))

    def test_overflow_and_underflow_are_rejected(self):
        self.assertIsNone(envelope_candidate([1e200, 1e200, 1e200], 1))
        self.assertIsNone(envelope_candidate([1e-200, 1e-200, 1e-200], 1))

    def test_invalid_finished_volume_is_rejected(self):
        for volume in (0, -1, math.inf, math.nan, True, None):
            with self.subTest(volume=volume):
                self.assertIsNone(envelope_candidate([10, 10, 10], volume))


if __name__ == '__main__':
    unittest.main()
