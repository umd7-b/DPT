"""Load the experimental trial gallery by identity; no rankings or fusion."""
from pathlib import Path
import json
import numpy as np

from .lbp236 import Context, Extractor, validate_vector


class TrialGallery:
    def __init__(self, directory, context=None):
        self.directory = Path(directory)
        self.context = Context() if context is None else context
        self.lock = json.loads((self.directory / 'contract_lock.json').read_text(encoding='utf-8'))
        self.context.require_lock(self.lock)
        manifest = json.loads((self.directory / 'manifest.json').read_text(encoding='utf-8'))
        self.context.require_lock(manifest)
        self.vectors = np.load(self.directory / 'gallery_vectors.npy', allow_pickle=False)
        self.rows = {}
        seen = set()
        for image in manifest['images']:
            identity, row = image['image_id'], image['feature_row_index']
            self.context.require_lock(image)
            if identity in seen:
                raise ValueError('Duplicate image_id in gallery')
            seen.add(identity)
            if image['status'] == 'valid_C1':
                if type(row) is not int or row in self.rows.values():
                    raise ValueError('Invalid/duplicate feature row')
                self.rows[identity] = row
            elif image['status'] != 'missing_C1' or row is not None:
                raise ValueError('Missing image has a vector row or unknown status')
        if set(self.rows.values()) != set(range(len(self.vectors))) or self.vectors.shape != (len(self.rows), 236):
            raise ValueError('Gallery row mapping/shape mismatch')
        for vector in self.vectors:
            validate_vector(vector)
        self.vectors.flags.writeable = False

    def vector(self, image_id):
        # KeyError for missing_C1; never substitute a zero vector.
        return self.vectors[self.rows[image_id]].copy()

    def extract_query(self, bgr, landmarks478, image_id='query', source='external'):
        """Caller supplies aligned BGR and pixel landmarks with provenance.

        This adapter performs no detection/alignment, fitting or parameter changes.
        """
        return Extractor(self.context).extract(bgr, landmarks478, image_id, source, gallery_lock=self.lock)
