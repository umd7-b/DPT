"""Validate raw-mask diagnostics and bit-word specification, never image LBP."""
from collections import Counter
import hashlib
import unittest

import cv2
import numpy as np

import validate_roi_all as audit
from verify_full_validation import segment_intersections
from shared.report_v2 import read_json,read_csv


class RawGeometryTests(unittest.TestCase):
    def test_integer_centres_include_boundary_and_float_vertices_are_not_rounded(self):
        square=np.array([[1.,1.],[4.,1.],[4.,4.],[1.,4.]])
        self.assertEqual(int(audit.raw_mask(square,6,6).sum()),16)
        fractional=np.array([[1.1,1.1],[3.9,1.1],[3.9,3.9],[1.1,3.9]])
        self.assertEqual(int(audit.raw_mask(fractional,6,6).sum()),4)

    def test_overlapping_masks_are_not_assigned_to_a_priority_owner(self):
        a=audit.raw_mask(np.array([[1.,1.],[4.,1.],[4.,4.],[1.,4.]]),6,6)
        b=audit.raw_mask(np.array([[3.,1.],[5.,1.],[5.,4.],[3.,4.]]),6,6)
        self.assertEqual(int((a&b).sum()),8)
        self.assertEqual((int(a.sum()),int(b.sum())),(16,12))

    def test_outside_polygon_is_clipped_at_evaluation_not_vertex_clamped(self):
        p=np.array([[-2.,-2.],[2.,-2.],[2.,2.],[-2.,2.]])
        self.assertEqual(int(audit.raw_mask(p,6,6).sum()),9)

    def test_independent_crossing_solver(self):
        p=np.array([[0.,0.],[4.,4.],[0.,4.],[4.,0.]])
        crossings=segment_intersections(p)
        self.assertEqual(len(crossings),1)
        self.assertEqual(crossings[0]['intersection_xy'],[2.,2.])

    def test_support_is_exact_21_pixel_bilinear_stencil(self):
        footprint=audit.support_footprint()
        self.assertEqual(len(footprint),21)
        self.assertIn((2,-2),footprint)
        self.assertNotIn((1,0),footprint)
        mask=np.ones((6,6),np.uint8)
        self.assertEqual(int(audit.support_centres(mask).sum()),4)


class FrozenSpecTests(unittest.TestCase):
    def test_geometry_and_a_indices_unchanged_but_overlap_policy_explicit(self):
        c=read_json(audit.OUT/'contract_v0_2.json');old=read_json(audit.PROPOSAL)
        self.assertEqual(c['polygons'],old['polygons'])
        self.assertEqual(c['indices68_unchanged'],old['indices68_unchanged'])
        self.assertEqual(c['status'],'PROVISIONAL')
        self.assertFalse(c['priority_subtraction_applied'])
        self.assertNotIn('overlap_priority',c)
        expected=c.pop('content_sha256')
        self.assertEqual(audit.canonical_hash(c),expected)

    def test_59_codebook_has_58_distinct_uniform_bins_and_198_others(self):
        rows=read_csv(audit.OUT/'nri_uniform_59_codebook.csv')
        by_code={int(r['raw_code']):r for r in rows}
        uniform=[r for r in rows if int(r['circular_transitions'])<=2]
        self.assertEqual(len(uniform),58)
        self.assertEqual({int(r['nri_uniform_bin']) for r in uniform},set(range(58)))
        self.assertEqual(sum(int(r['nri_uniform_bin'])==58 for r in rows),198)
        self.assertEqual(int(by_code[0]['nri_uniform_bin']),0)
        self.assertEqual(int(by_code[255]['nri_uniform_bin']),57)
        self.assertNotEqual(by_code[1]['nri_uniform_bin'],by_code[2]['nri_uniform_bin'])
        self.assertEqual(int(by_code[129]['nri_uniform_bin']),10)

    def test_lbp_spec_has_required_pdf_math_without_claiming_extraction(self):
        spec=read_json(audit.OUT/'lbp_implementation_spec.json');p=spec['pdf_requirements']
        self.assertEqual((p['P'],p['R'],p['bins'],p['regions'],p['dimension']),(8,2,59,4,236))
        self.assertTrue(p['distance'].startswith('0.5*'))
        self.assertFalse(spec['extractor_implemented'])
        self.assertFalse(spec['lbp_codes_computed_on_images'])
        self.assertEqual(spec['conventions']['min_eligible_centres'],64)
        coefficients=spec['conventions']['grayscale_coefficients_bgr']
        self.assertEqual(sum(coefficients),spec['conventions']['grayscale_denominator'])
        for rgb,expected in [([255,0,0],29),([0,255,0],150),([0,0,255],76),([255,255,255],255)]:
            # Scalar specification fixtures, not image feature extraction.
            actual=(sum(c*v for c,v in zip(coefficients,rgb))+8192)//16384
            self.assertEqual(actual,expected)


class FullDatasetEvidenceTests(unittest.TestCase):
    def test_complete_population_and_actual_invalid_cases_are_retained(self):
        rows=read_csv(audit.OUT/'metrics.csv')
        self.assertEqual(len(rows),5752)
        self.assertEqual(Counter(r['region'] for r in rows),{r:1438 for r in audit.REGIONS})
        bad=[r for r in rows if r['geometry_valid']=='False']
        self.assertEqual({r['image_id'] for r in bad},{'hf_merged_00069','hf_merged_00198','hf_merged_00267','hf_merged_00463'})
        self.assertTrue(all(r['region']=='forehead_brow' for r in bad))

    def test_case_masks_keep_overlap_and_match_recorded_hash(self):
        rows={(r['image_id'],r['region']):r for r in read_csv(audit.OUT/'metrics.csv')}
        cases=read_json(audit.OUT/'case_selection.json')['cases']
        for case in cases:
            masks=[]
            for region in audit.REGIONS:
                image=cv2.imread(str(audit.OUT/'contact_sheets'/case['image_id']/(region+'_raw_mask.png')),0)
                mask=(image!=0).astype(np.uint8)
                self.assertEqual(hashlib.sha256(mask.tobytes()).hexdigest(),rows[(case['image_id'],region)]['raw_mask_sha256'])
                masks.append(mask)
            self.assertTrue((np.sum(masks,axis=0)>=2).any())

    def test_trial_plan_balanced_and_preserves_expected_failure_cases(self):
        t=read_json(audit.OUT/'trial100_manifest.json')
        self.assertEqual(Counter(r['source'].lower() for r in t['images']),dict(cfd=50,hf=50))
        self.assertEqual(sum(not r['technical_roi_support_ready'] for r in t['images']),4)
        self.assertFalse(t['trial_executed'])
        self.assertFalse(t['extractor_implemented'])


if __name__=='__main__':
    unittest.main()
