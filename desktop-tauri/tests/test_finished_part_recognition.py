"""Independent regression for conservative finished-part family classification.

Pure-Python tests run before costly OCCT installation; original STEP geometry
is subsequently checked in public_stock_axis_regression.py (compiled engine).
"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'cad_backend'))
from finished_part_recognition import recognize_finished_geometry


def surfaces(planes=(),cylinders=(),others=0):
    return {'source':'original STEP B-Rep face adaptors',
            'planes':list(planes),'cylinders':list(cylinders),
            'planeFaceCount':len(planes),'cylinderFaceCount':len(cylinders),
            'coneFaceCount':0,'otherFaceCount':others}


def plane(area,normal,offset):
    return {'normal':list(normal),'areaMm2':area,'signedOffsetMm':offset}


def cylinder(radius,axis):
    return {'radiusMm':radius,'axis':list(axis),'axisPointMm':[0,0,0]}


class FinishedPartFamilyTest(unittest.TestCase):
    def test_short_irregular_plate_with_through_bore(self):
        # The original Earthpress 25/26 type: thickness is neither a long
        # extrusion axis nor discoverable by comparing five end sections.
        area=4311.732365;thickness=20
        faces=[plane(area,(0,1,0),-10),
               plane(area,(0,-1,0),-10),
               plane(1264.9,(1,0,0),-68),
               plane(980,(0,0,1),900)]
        stock={'kind':'unknown','finishedBrepSurfaceEvidence':
               surfaces(faces,[cylinder(15.5,(0,-1,0))])}
        r=recognize_finished_geometry(stock,area*thickness)
        self.assertEqual(r['family'],'constant-thickness-plate-body',r)
        self.assertAlmostEqual(r['measurements']['thicknessMm'],20)
        self.assertFalse(r['blankCertified'])
        self.assertFalse(r['processCertified'])
        self.assertFalse(r['cutTimeCertified'])

    def test_rotated_plate_and_false_multilayer_guard(self):
        area=3605.232365
        n=(2**-.5,2**-.5,0)
        faces=[plane(area,n,-10),plane(area,tuple(-x for x in n),-10),
               plane(900,(-n[1],n[0],0),80)]
        c=cylinder(15.5,n)
        stock={'kind':'unknown','finishedBrepSurfaceEvidence':surfaces(faces,[c])}
        self.assertEqual(recognize_finished_geometry(stock,area*20)['family'],
                         'constant-thickness-plate-body')
        # A second non-perpendicular wall is evidence of a more complex solid.
        invalid=surfaces(faces+[plane(1100,n,2)],[c])
        self.assertEqual(recognize_finished_geometry(
                         {'kind':'unknown','finishedBrepSurfaceEvidence':invalid},
                         area*20)['status'],'unknown')
        # A matching pair without a matching original volume is not enough.
        self.assertEqual(recognize_finished_geometry(stock,area*25)['status'],
                         'unknown')

    def test_small_end_features_on_nearly_cylindrical_body(self):
        r=20;L=128;volume=160796.0
        p=[plane(1134.1,(0,1,0),-64),plane(1134.1,(0,1,0),64)]
        stock={'kind':'unknown','finishedBrepSurfaceEvidence':
               surfaces(p,[cylinder(r,(0,1,0))],others=2)}
        result=recognize_finished_geometry(stock,volume)
        self.assertEqual(result['family'],'near-round-cylindrical-body',result)
        self.assertAlmostEqual(result['measurements']['cylindricalDiameterMm'],40)
        self.assertAlmostEqual(result['measurements']['axialLengthMm'],128)
        # Real circular bore -> two analytic cylinders, hence NOT solid round bar.
        stock['finishedBrepSurfaceEvidence']=surfaces(
            p,[cylinder(r,(0,1,0)),cylinder(8,(0,1,0))],others=2)
        self.assertEqual(recognize_finished_geometry(stock,volume)['status'],'unknown')

    def test_existing_local_section_evidence_does_not_certify_stock(self):
        stock={'kind':'unknown',
               'finishedBrepSurfaceEvidence':surfaces(
                   [plane(100,(0,1,0),0)],[]),
               'coreSectionCandidate':{
                   'kind':'round-tube','diameterMm':40,'wallMm':3,
                   'lengthMm':369.37,'confidence':'geometric-core-only',
                   'axisEvidence':'B-Rep cylinder/edge axis'}}
        result=recognize_finished_geometry(stock,191581)
        self.assertEqual(result['family'],'core-section-body-with-secondary-features')
        self.assertEqual(result['measurements']['verifiedCoreKind'],'round-tube')
        self.assertFalse(result['blankCertified'])
        stock['rawStockCandidate']={'kind':'channel','widthMm':80,'heightMm':45,
                                     'confidence':'raw-stock-candidate'}
        result=recognize_finished_geometry(stock,191581)
        self.assertEqual(result['family'],'extrusion-body-with-secondary-features')
        self.assertEqual(result['measurements']['verifiedCoreKind'],'channel')

    def test_missing_unverified_evidence_is_not_promoted(self):
        self.assertEqual(recognize_finished_geometry(
            {'kind':'unknown'},100)['status'],'unknown')
        self.assertEqual(recognize_finished_geometry(
            {'kind':'unknown','finishedBrepSurfaceEvidence':{
                'source':'user supplied name','planes':[]}},100)['status'],'unknown')


    def test_existing_aag_evidence_is_diagnostic_only(self):
        stock={'kind':'unknown','finishedBrepSurfaceEvidence':surfaces([],[])}
        graph={'status':'measured','nonManifoldEdges':0,
               'featurePatterns':{'status':'measured','truncated':False,
                                  'counts':{'through-cylindrical-opening':2,
                                            'unverified-operation':7}}}
        result=recognize_finished_geometry(stock,100,graph)
        self.assertEqual(result['status'],'unknown')
        self.assertEqual(result['verifiedSecondaryFeatures'],
                         [{'kind':'through-cylindrical-opening','count':2}])
        self.assertNotIn('cutTimeCertified',result)
        graph['featurePatterns']['truncated']=True
        self.assertNotIn('verifiedSecondaryFeatures',
                         recognize_finished_geometry(stock,100,graph))
        graph['featurePatterns']['truncated']=False
        graph['nonManifoldEdges']=1
        self.assertNotIn('verifiedSecondaryFeatures',
                         recognize_finished_geometry(stock,100,graph))


if __name__=='__main__':
    unittest.main()
