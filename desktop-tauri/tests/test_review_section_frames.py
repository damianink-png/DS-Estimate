import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'cad_backend'))
from stock_recognition import _classify_section

def edges(points):
 return [([a,b],False,None) for a,b in zip(points,points[1:]+points[:1])]

class SectionFrames(unittest.TestCase):
 def test_split_inner_long_edges_preserve_rhs(self):
  outer=[(-60,-40),(60,-40),(60,40),(-60,40)]
  inner=[(-54,-34),(0,-34),(54,-34),(54,34),(0,34),(-54,34)]
  result=_classify_section(edges(outer)+edges(inner),.002)
  self.assertEqual(result['kind'],'rectangular-hollow')
  self.assertAlmostEqual(result['wallMm'],6)
  self.assertAlmostEqual(result['sectionAreaMm2'],2256)
 def test_unequal_walls_remain_rejected(self):
  outer=[(-60,-40),(60,-40),(60,40),(-60,40)]
  inner=[(-54,-30),(0,-30),(54,-30),(54,30),(0,30),(-54,30)]
  self.assertIsNone(_classify_section(edges(outer)+edges(inner),.002))

if __name__=='__main__':unittest.main()
