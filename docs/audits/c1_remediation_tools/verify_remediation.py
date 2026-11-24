"""Independent tabular/segment checks and geometry tests, no feature calls."""
from collections import Counter, defaultdict
import io
import json
import sys
import unittest

import cv2
import numpy as np

import audit_remediation as audit


class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = audit.read_json(audit.OUT / 'candidate_contract_v0_4.json')
        cls.base = audit.read_json(audit.OLD / 'contract_v0_2.json')
        cls.anomalies = audit.read_json(audit.OUT / 'four_cases_intersections.json')

    def test_content_hash_and_parent_pin(self):
        c = dict(self.candidate); stored = c.pop('content_sha256')
        self.assertEqual(audit.canonical(c), stored)
        self.assertEqual(c['source_contract']['content_sha256'], audit.ROI_PIN)
        self.assertEqual(c['source_contract']['file_sha256'], audit.digest(audit.OLD / 'contract_v0_2.json'))

    def test_not_active_and_unverified_anatomy(self):
        self.assertFalse(self.candidate['active'])
        self.assertEqual(self.candidate['status'], 'PROVISIONAL')
        self.assertEqual(self.candidate['anatomy_status'], 'ANATOMY_PROVISIONAL')
        self.assertEqual(self.candidate['region_order'], audit.REGIONS)

    def test_upper_oval_and_three_other_regions_unchanged(self):
        self.assertEqual(self.candidate['polygons']['forehead_brow'][:15], self.base['polygons']['forehead_brow'][:15])
        for region in audit.REGIONS[1:]:
            self.assertEqual(self.candidate['polygons'][region], self.base['polygons'][region])
        self.assertEqual(self.candidate['indices68_unchanged'], self.base['indices68_unchanged'])

    def test_lower_chain_native_membership_and_no_offset(self):
        chain = self.candidate['polygons']['forehead_brow'][15:]
        self.assertEqual([r['mediapipe_index'] for r in chain], audit.LOWER)
        self.assertTrue(all(r['offset_u_ipd'] == r['offset_v_ipd'] == 0 for r in chain))
        native = audit.read_json(audit.ROOT / 'docs/audits/pre_c_evidence/native_mediapipe_topology.json')['edges']
        edges = {frozenset(edge) for name, group in native.items() if 'EYEBROW' in name for edge in group}
        for half in (audit.LOWER[:5], audit.LOWER[5:]):
            for a, b in zip(half, half[1:]): self.assertIn(frozenset((a, b)), edges)

    def test_four_crossings_are_interior_not_closing_edges(self):
        self.assertEqual({r['image_id'] for r in self.anomalies}, set(audit.NEGATIVE))
        for case in self.anomalies:
            crossings = case['variants']['v0_2']['crossings']
            self.assertEqual(len(crossings), 1)
            self.assertFalse(crossings[0]['involves_polygon_closure_edge'])
            self.assertTrue(all(0 < t < 1 for t in crossings[0]['segment_parameters']))
            self.assertLess(crossings[0]['independent_linear_solve_residual'], 1e-10)

    def test_HF198_shift_crosses_temporal_boundary(self):
        case = next(r for r in self.anomalies if r['image_id'] == 'hf_merged_00198')
        side = case['temporal_offset_side_test']
        self.assertGreater(side['signed_cross_unshifted'], 0)
        self.assertLess(side['signed_cross_shifted'], 0)
        crossing = case['variants']['v0_3']['crossings'][0]
        np.testing.assert_allclose(crossing['intersection_xy'], [62.568903832804914, 81.21493142290605], rtol=0, atol=1e-11)
        self.assertFalse(case['variants']['candidate_v0_4']['self_intersection'])

    def test_segment_fixture_and_polygon_closure(self):
        vertices = np.array([[0., 0.], [4., 4.], [0., 4.], [4., 0.]])
        result = audit.segment_intersections(vertices)
        self.assertEqual(len(result), 1)
        np.testing.assert_array_equal(result[0]['intersection_xy'], [2., 2.])
        self.assertTrue(audit.frozen.previous.self_intersects(vertices))
        self.assertFalse(audit.frozen.previous.self_intersects(np.array([[0., 0.], [4., 0.], [4., 4.], [0., 4.]])))

    def test_raw_raster_boundary_and_support_21_no_ownership(self):
        vertices = np.array([[10., 10.], [30., 10.], [30., 30.], [10., 30.]])
        mask = audit.frozen.raw_mask(vertices)
        self.assertEqual(int(mask.sum()), 441)
        self.assertEqual(int(audit.frozen.support_centres(mask).sum()), 289)
        self.assertEqual(len(audit.frozen.support_footprint()), 21)
        shared = mask.copy()
        self.assertEqual(int((mask & shared).sum()), 441)
        self.assertFalse(self.candidate['priority_subtraction_applied'])


def main():
    if (audit.OUT / 'verification.json').exists():
        raise FileExistsError('Completed verification exists')
    summary = audit.read_json(audit.OUT / 'summary.json')
    metrics = audit.read_csv(audit.OUT / 'roi_metrics.csv')
    imetrics = audit.read_csv(audit.OUT / 'image_metrics.csv')
    overlaps = audit.read_csv(audit.OUT / 'overlap_metrics.csv')
    vertices = audit.read_csv(audit.OUT / 'candidate_vertices.csv')
    assert len(metrics) == 17256 and len(imetrics) == 4314 and len(overlaps) == 25884 and len(vertices) == 175436
    metric_map = {(r['variant'], r['image_id'], r['region']): r for r in metrics}
    image_map = {(r['variant'], r['image_id']): r for r in imetrics}
    assert len(metric_map) == len(metrics)
    for variant in ['v0_2', 'v0_3', 'candidate_v0_4']:
        rows = [r for r in metrics if r['variant'] == variant]
        assert Counter(r['region'] for r in rows) == {name: 1438 for name in audit.REGIONS}
        counts = summary['variants'][variant]
        assert sum(r['geometry_valid'] == 'True' for r in rows) == counts['valid_geometry']
        assert sum(r['self_intersection'] == 'True' for r in rows) == counts['self_intersections']
    overlap_sum = defaultdict(int)
    for row in overlaps:
        key = row['variant'], row['image_id']
        overlap_sum[key] += int(row['overlap_pixels'])
        assert row['ownership_subtraction'] == 'False'
    # Check union independently by inclusion/exclusion; membership is at most2.
    for (variant, identity), row in image_map.items():
        assert int(row['max_memberships']) <= 2
        raw_sum = sum(int(metric_map[(variant, identity, r)]['raw_mask_pixels']) for r in audit.REGIONS)
        assert raw_sum - overlap_sum[(variant, identity)] == int(row['raw_union_pixels'])
        assert overlap_sum[(variant, identity)] == int(row['overlap_unique_pixels'])
    for row in metrics:
        if row['region'] in audit.REGIONS[1:]:
            base = metric_map[('v0_2', row['image_id'], row['region'])]
            for field in ['raw_mask_sha256', 'raw_mask_pixels', 'eligible_centres', 'continuous_area_px2']:
                assert row[field] == base[field]
        if row['region'] == 'forehead_brow':
            assert 0 <= int(row['brow_proxy_covered_pixels']) <= int(row['brow_proxy_pixels'])
            assert abs(float(row['brow_proxy_coverage']) - int(row['brow_proxy_covered_pixels']) / int(row['brow_proxy_pixels'])) < 1e-15
    # Independently count proper crossings from CSV vertices for every forehead.
    grouped = defaultdict(list)
    for row in vertices:
        if row['region'] == 'forehead_brow':
            grouped[(row['variant'], row['image_id'])].append(row)
    proper_counts = Counter()
    for (variant, identity), items in grouped.items():
        items.sort(key=lambda r: int(r['vertex_order']))
        assert [int(r['vertex_order']) for r in items] == list(range(25))
        xy = np.array([(float(r['x']), float(r['y'])) for r in items])
        crossings = audit.segment_intersections(xy)
        if crossings: proper_counts[variant] += 1
        flag = metric_map[(variant, identity, 'forehead_brow')]['self_intersection'] == 'True'
        assert bool(crossings) == flag
    print('Independent crossing census:', dict(proper_counts), flush=True)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GeometryTests))
    text = output.getvalue()
    print(text, end='', flush=True)
    with (audit.OUT / 'tests.log').open('x', encoding='utf-8') as stream: stream.write(text)
    if not result.wasSuccessful():
        raise AssertionError('Geometry tests failed')
    baseline = audit.check_sources()
    selection = audit.read_json(audit.OUT / 'contact_sheet_selection.json')
    for image in selection['images']:
        rendered = cv2.imread(str(audit.ROOT / image['contact_sheet']))
        assert rendered is not None and rendered.shape == (1154, 2048, 3)
    assert not list(audit.OUT.rglob('*.npy')) and not list(audit.OUT.rglob('*.npz'))
    audit.write_json(audit.OUT / 'verification.json', dict(schema_id='C1_REMEDIATION_VERIFICATION_v0.4.0',
        status='PASS', tests=result.testsRun, failed=len(result.failures), errors=len(result.errors),
        compared_roi_rows=len(metrics), compared_image_rows=len(imetrics), pairwise_overlap_rows=len(overlaps),
        candidate_vertex_rows=len(vertices), independently_checked_forehead_polygons=len(grouped),
        proper_crossing_polygon_counts=dict(proper_counts), all_other_region_masks_bitwise_unchanged=True,
        protected_files=len(baseline), changed_or_missing_existing_files=[],
        geometric_status=summary['geometry_status'], anatomy_status='ANATOMY_PROVISIONAL',
        C1C2_vectors_created=0, feature_extractor_calls=0, retrieval_comparisons=0, candidate_activated=False))
    print('PASS; protected files unchanged:', len(baseline), flush=True)


if __name__ == '__main__':
    main()
