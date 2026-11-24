MANUAL LABELS ONLY

This directory intentionally contains no real image masks yet.
Use src/annotate_masks.py to draw and explicitly confirm skin/hair independently.
Each image is stored as <stem>/rev_<uuid>/{skin.png,hair.png,annotation.json}.
current.json selects the latest complete revision; older versions are retained.
Unconfirmed drafts are NOT ground truth. Predictions are never imported.
See outputs/mask_validation/README.txt for annotation policy and commands.
