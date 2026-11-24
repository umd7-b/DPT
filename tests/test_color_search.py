import unittest
import numpy as np
from features.B_color.src.search_color import top5

class ColorSearchTests(unittest.TestCase):
    def test_self_is_excluded_and_euclidean_order_correct(self):
        x=np.zeros((7,144));x[:,0]=[0,5,1,2,3,4,6]
        names=['q.png','b.png','c.png','d.png','e.png','f.png','g.png']
        result=top5(x,names,'q.png')
        self.assertEqual([r['image_name'] for r in result],['c.png','d.png','e.png','f.png','b.png'])
        self.assertEqual([r['distance'] for r in result],[1,2,3,4,5])

    def test_ties_are_stable_and_missing_queries_not_replaced(self):
        x=np.zeros((7,144));names=['q.png','z.png','a.png','b.png','d.png','c.png','e.png']
        self.assertEqual(top5(x,names,'q.png')[0]['image_name'],'a.png')
        with self.assertRaises(ValueError):top5(x,names,'missing.png')
        x[1,0]=np.nan
        with self.assertRaises(ValueError):top5(x,names,'q.png')

if __name__=='__main__':unittest.main()
