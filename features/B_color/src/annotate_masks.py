"""OpenCV manual skin/hair editor. Start blank; confirmation requires human keys."""
import argparse
from pathlib import Path
from shared.paths import PROJECT_ROOT

import cv2
import numpy as np

from features.B_color.src.mask_labels import (Annotation, DATASET, LABELS, ROOT, WORK, binary_mask,
                         image_names, overlay, safe_destination, tile, write_image)


class Editor:
    SCALE = 2
    HEADER = 95
    WINDOW = 'Manual skin/hair labels'

    def __init__(self, names, dataset, labels, annotator, hair_predictions):
        self.names, self.dataset, self.labels = names, dataset, labels
        self.annotator, self.hair_predictions = annotator, hair_predictions
        self.index, self.region, self.radius = 0, 'skin', 4
        self.stroke, self.last, self.pending = None, None, None
        self.show_predictions = False
        self.message = 'Draw from original. S saves DRAFT. C then Y confirms active region.'
        self.load()

    def load(self):
        self.annotation = Annotation(self.dataset / 'images' / self.names[self.index], self.labels)
        self.stroke, self.last, self.pending = None, None, None

    def canvas_point(self, x, y):
        h, w = self.annotation.image.shape[:2]
        x, y = x // self.SCALE, (y - self.HEADER) // self.SCALE
        return (x, y) if 0 <= x < w and 0 <= y < h else None

    def mouse(self, event, x, y, flags, param=None):
        point = self.canvas_point(x, y)
        if event in (cv2.EVENT_LBUTTONDOWN, cv2.EVENT_RBUTTONDOWN) and point is not None:
            self.pending = None
            self.stroke = event == cv2.EVENT_RBUTTONDOWN
            self.last = point
            self.annotation.paint(self.region, point, point, self.radius, self.stroke)
        elif event == cv2.EVENT_MOUSEMOVE and self.stroke is not None:
            if point is not None:
                self.annotation.paint(self.region, self.last or point, point, self.radius, self.stroke, False)
            self.last = point
        elif event in (cv2.EVENT_LBUTTONUP, cv2.EVENT_RBUTTONUP):
            self.stroke, self.last = None, None

    def render(self):
        a = self.annotation
        drawing = overlay(overlay(a.image, a.masks['skin'], (0, 220, 0)), a.masks['hair'], (255, 80, 20))
        reference = a.image.copy()
        title = 'Original (independent annotation)'
        if self.show_predictions:
            title = 'PREDICTIONS ONLY - never imported'
            for region, path in (
                ('skin', self.dataset / 'skin_masks' / f'{a.image_path.stem}_skin.png'),
                ('hair', self.hair_predictions / f'{a.image_path.stem}_hair_mask.png')):
                if path.exists():
                    try:
                        mask = binary_mask(path, a.image.shape[:2])
                        reference = overlay(reference, mask, (0,220,0) if region == 'skin' else (255,80,20))
                    except ValueError:
                        self.message = f'Invalid {region} prediction ignored. Human canvas is unchanged.'
        left = cv2.resize(drawing, None, fx=self.SCALE, fy=self.SCALE, interpolation=cv2.INTER_NEAREST)
        right = cv2.resize(reference, (left.shape[1],left.shape[0]), interpolation=cv2.INTER_NEAREST)
        frame = cv2.copyMakeBorder(np.hstack([left,right]), self.HEADER, 60, 0, 0, cv2.BORDER_CONSTANT, value=(30,30,30))
        states = ' '.join(f'{r}:{"CONFIRMED" if a.valid_region(r) else "DRAFT"}' for r in a.masks)
        lines = [f'{self.index+1}/{len(self.names)} {a.image_path.name} | active={self.region} brush={self.radius} {states}',
                 '1 skin | 2 hair | LMB paint | RMB erase | [ ] brush | U undo | X clear',
                 'S save | C confirm + Y | E confirm EMPTY + Y | N/B next/back (autosave draft) | Q quit (autosave)',
                 'P toggle prediction reference (OFF initially). No prediction import. ' + title]
        for i, line in enumerate(lines):
            cv2.putText(frame,line,(8,18+i*22),cv2.FONT_HERSHEY_SIMPLEX,.44,(240,240,240),1)
        cv2.putText(frame,self.message[:135],(8,frame.shape[0]-30),cv2.FONT_HERSHEY_SIMPLEX,.44,(60,230,255),1)
        return frame

    def key(self, key):
        # Shortcut labels are shown uppercase; accept Caps Lock/Shift as well.
        if ord('A') <= key <= ord('Z'):
            key += ord('a') - ord('A')
        a = self.annotation
        if self.pending:
            if key == ord('y'):
                try:
                    a.confirm(self.region, self.annotator, empty_confirmed=self.pending == 'empty')
                    a.save(self.annotator)
                    self.message = f'{self.region} explicitly confirmed and saved by {self.annotator}'
                except ValueError as error:
                    self.message = str(error)
                self.pending = None
                return True
            self.pending = None
            self.message = 'Confirmation cancelled.'
        if key in (ord('1'),ord('2')):
            self.region = 'skin' if key == ord('1') else 'hair'
        elif key == ord('u'): a.undo()
        elif key == ord('x'): a.clear(self.region)
        elif key == ord('['): self.radius = max(1,self.radius-1)
        elif key == ord(']'): self.radius = min(40,self.radius+1)
        elif key == ord('p'): self.show_predictions = not self.show_predictions
        elif key == ord('s'):
            a.save(self.annotator)
            self.message = 'Saved. Draft regions are excluded from evaluation.'
        elif key in (ord('c'),ord('e')):
            empty = key == ord('e')
            if empty and np.any(a.masks[self.region]):
                self.message = 'EMPTY confirmation requires an empty mask. X clears (undo supported).'
            elif not empty and not np.any(a.masks[self.region]):
                self.message = 'Empty mask: draw first, or E then Y only if region is truly absent.'
            else:
                self.pending = 'empty' if empty else 'normal'
                self.message = f'HUMAN REVIEW: {self.region} {"ABSENT" if empty else "complete and correct"}? Y confirms; other key cancels.'
        elif key in (ord('n'),ord('b'),ord('q'),27):
            if a.dirty: a.save(self.annotator)
            if key in (ord('q'),27): return False
            self.index = (self.index + (1 if key == ord('n') else -1)) % len(self.names)
            self.load()
            self.message = 'Opened next image. Previous changes saved without adding confirmation.'
        return True

    def run(self, smoke_test=False, preview_dir=WORK / 'editor_smoke'):
        cv2.namedWindow(self.WINDOW, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.WINDOW, self.mouse)
        try:
            if smoke_test:
                for index in range(len(self.names)):
                    self.index = index
                    self.load()
                    frame = self.render()
                    write_image(preview_dir / f'{self.annotation.image_path.stem}_editor.png', frame)
                    cv2.imshow(self.WINDOW, frame)
                    cv2.waitKey(700)
                # No painting, saving, confirmation, or label files in smoke mode.
                return
            while True:
                cv2.imshow(self.WINDOW,self.render())
                key = cv2.waitKey(20)
                if key >= 0 and not self.key(key & 0xff): break
                if cv2.getWindowProperty(self.WINDOW,cv2.WND_PROP_VISIBLE) < 1:
                    if self.annotation.dirty: self.annotation.save(self.annotator)
                    break
        finally:
            cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,default=DATASET)
    parser.add_argument('--manifest',type=Path,default=WORK / 'panel40.csv')
    parser.add_argument('--image',nargs='+')
    parser.add_argument('--labels',type=Path,default=LABELS)
    parser.add_argument('--hair-pred-dir',type=Path,default=WORK / 'predictions/hair')
    parser.add_argument('--annotator',default='')
    parser.add_argument('--smoke-test',action='store_true')
    args = parser.parse_args()
    safe_destination(args.labels,args.dataset,args.hair_pred_dir)
    if not args.smoke_test and not args.annotator.strip(): parser.error('--annotator is required for manual work')
    names = args.image or image_names(args.manifest)
    if not names or any(Path(n).name != n or '/' in n or '\\' in n for n in names): parser.error('Image basenames required')
    Editor(names,args.dataset,args.labels,args.annotator,args.hair_pred_dir).run(args.smoke_test)


if __name__ == '__main__':
    main()
