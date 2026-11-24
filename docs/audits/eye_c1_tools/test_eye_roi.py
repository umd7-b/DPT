"""Tests of saved-landmark eye metadata and proposal geometry, never LBP/HOG."""
from contextlib import closing
import json
import math
import sqlite3
import unittest

import numpy as np
import prepare_eye_roi as task


class EyeArithmeticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups,_=task.source_groups()

    def test_known_six_point_means(self):
        p=np.ones((478,2),np.float32)
        p[self.groups['LEFT_EYE']]=[[32,90],[34,94],[36,98],[38,102],[40,106],[42,110]]
        p[self.groups['RIGHT_EYE']]=[[132,90],[134,94],[136,98],[138,102],[140,106],[142,110]]
        self.assertEqual(task.measure_eyes(p,256,256,self.groups),(37.,100.,137.,100.))

    def test_invalid_input_is_not_guessed(self):
        for p in [np.zeros((478,2),np.float32),np.ones((478,2),np.float32),
                  np.full((478,2),np.nan,np.float32),np.ones((477,2),np.float32)]:
            with self.assertRaises(ValueError):
                task.measure_eyes(p,256,256,self.groups)
        p=np.ones((478,2),np.float32)
        p[self.groups['LEFT_EYE']]=[-5,100]
        p[self.groups['RIGHT_EYE']]=[100,100]
        with self.assertRaisesRegex(ValueError,'outside'):
            task.measure_eyes(p,256,256,self.groups)

    def test_float32_method_is_not_silently_replaced_by_float64(self):
        with np.load(task.ARCHIVE,allow_pickle=False) as archive:
            p=archive['points'][0]
        values=task.measure_eyes(p,256,256,self.groups)
        self.assertEqual(values[:2],(88.1707992553711,102.11358642578125))
        self.assertNotEqual(values[:2],(88.17080307006836,102.11359151204427))


class ProposalGeometryTests(unittest.TestCase):
    def test_source_mapping_is_preserved_and_auxiliary_points_are_separate(self):
        groups,indices=task.source_groups(); spec=task.contract(indices)
        self.assertEqual(indices[30],1)
        self.assertEqual(indices[33],4)
        self.assertEqual(spec['provisional_order'],task.REGIONS)
        self.assertEqual([len(v) for v in spec['polygons'].values()],[25,12,12,12])
        self.assertEqual(spec['status'],'PROPOSAL_UNVERIFIED_NOT_FOR_FEATURE_EXTRACTION')

    def test_proper_and_collinear_self_intersections_rejected(self):
        self.assertTrue(task.self_intersects(np.array([[0.,0.],[4.,4.],[0.,4.],[4.,0.]])))
        self.assertTrue(task.self_intersects(np.array([[0.,0.],[4.,0.],[4.,4.],[2.,0.],[0.,4.]])))
        self.assertFalse(task.self_intersects(np.array([[0.,0.],[4.,0.],[4.,4.],[0.,4.]])))

    def test_overlap_is_resolved_by_fixed_priority(self):
        square=np.array([[1.,1.],[4.,1.],[4.,4.],[1.,4.]])
        polygons={k:square.copy() for k in task.REGIONS}
        masks,diagnostics,overlap=task.preview_masks(polygons,6,6)
        self.assertGreater(overlap,0)
        self.assertEqual(int(masks['forehead_brow'].sum()),16)
        self.assertIsNone(masks['nose_mouth'])
        self.assertEqual(diagnostics['nose_mouth'],'empty_after_overlap')

    def test_missing_or_outside_polygon_is_not_filled(self):
        polygons={k:np.array([[9.,9.],[12.,9.],[12.,12.],[9.,12.]]) for k in task.REGIONS}
        masks,diagnostics,_=task.preview_masks(polygons,6,6)
        self.assertTrue(all(v is None for v in masks.values()))
        self.assertTrue(all(v=='empty_region' for v in diagnostics.values()))


class EyeSqlIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names,cls.points,cls.images,cls.log,cls.proof=task.load_archive()

    def test_full_1438_roundtrip_and_provenance(self):
        groups,_=task.source_groups()
        with closing(task.db.connect(task.NEW_DB)) as c:
            rows=c.execute('SELECT * FROM EyeMetadataAuditV1 ORDER BY archive_row_index').fetchall()
            self.assertEqual(len(rows),1438)
            self.assertEqual(c.execute('SELECT count(*) FROM EyeCoordinates').fetchone()[0],1441)
            for row in rows:
                i=row['archive_row_index']
                expected=task.measure_eyes(self.points[i],256,256,groups)
                self.assertEqual(tuple(row[k] for k in ('left_x','left_y','right_x','right_y')),expected)
                self.assertEqual(row['source_landmark_hash'],task.db.sha_bytes(self.points[i].tobytes()))
                self.assertEqual(row['measurement_role'],'audit_remeasurement')
                self.assertEqual(row['coordinate_system'],task.COORDINATE_SYSTEM)
                self.assertEqual(row['image_id'],self.images[self.names[i]]['image_id'])

    def test_database_constraints_on_in_memory_copy(self):
        with closing(task.db.connect(task.NEW_DB)) as source,closing(sqlite3.connect(':memory:')) as c:
            source.backup(c); c.execute('PRAGMA foreign_keys=ON')
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute('INSERT INTO EyeCoordinateSources SELECT * FROM EyeCoordinateSources LIMIT 1')
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE EyeCoordinateSources SET source_landmark_hash='bad'")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE EyeCoordinateSources SET measurement_role='original_preprocessing'")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE EyeCoordinateSources SET image_id='unknown'")

    def test_old_and_new_gallery_queries_equal_without_media_pipe(self):
        with closing(task.db.connect()) as old,closing(task.db.connect(task.NEW_DB)) as new:
            for key in ['cfd_final_00001','cfd_final_00088','cfd_final_00144','hf_merged_00209']:
                before=task.db.search(old,key,persist=False)
                after=task.db.search(new,key,persist=False)
                self.assertEqual(before['runs'],after['runs'])
                self.assertEqual(before['excluded_self_ids'],after['excluded_self_ids'])


if __name__=='__main__':
    unittest.main()
