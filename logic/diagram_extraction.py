import os
import torch
import torchvision
import numpy as np
from PIL import Image
from pdf2image import convert_from_bytes
from huggingface_hub import snapshot_download
from doclayout_yolo import YOLOv10
from logic.visualization import visualize_bbox
from typing import List, Tuple


def _load_model():
    # Download weights if not already present
    model_dir = snapshot_download(
        'juliozhao/DocLayout-YOLO-DocStructBench',
        local_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'DocLayout-YOLO-DocStructBench'))
    )
    model_path = os.path.join(model_dir, 'doclayout_yolo_docstructbench_imgsz1024.pt')
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = YOLOv10(model_path)
    return model, device

# Initialize model once
_model, _device = _load_model()

# Mapping of class IDs to names
ID_TO_NAMES = {
    0: 'title',
    1: 'plain text',
    2: 'abandon',
    3: 'figure',
    4: 'figure_caption',
    5: 'table',
    6: 'table_caption',
    7: 'table_footnote',
    8: 'isolate_formula',
    9: 'formula_caption'
}

def extract_diagrams_from_pdf(file_path: str, conf_threshold: float = 0.25, iou_threshold: float = 0.45) -> Tuple[List, List[List]]:
    """
    Extract diagram images with detected bounding boxes from a PDF file.

    Args:
        file_path: Path to the PDF file.
        conf_threshold: Confidence threshold for object detection.
        iou_threshold: IOU threshold for non-maximum suppression.

    Returns:
        Tuple containing:
            - List of PIL Image objects with visualized bounding boxes.
            - List of lists of PIL Image snippets for detected figures by page.
    """
    results = []
    figure_snippets = []  # per-page list of figure crops
    with open(file_path, 'rb') as f:
        pages = convert_from_bytes(f.read())
    for page in pages:
        det_res = _model.predict(
            page,
            imgsz=1024,
            conf=conf_threshold,
            device=_device,
        )[0]
        boxes = det_res.__dict__['boxes'].xyxy
        classes = det_res.__dict__['boxes'].cls
        scores = det_res.__dict__['boxes'].conf

        # Apply non-maximum suppression
        indices = torchvision.ops.nms(
            boxes=torch.Tensor(boxes),
            scores=torch.Tensor(scores),
            iou_threshold=iou_threshold
        )
        b, s, c = boxes[indices], scores[indices], classes[indices]
        # Ensure correct shape
        if b.ndim == 1:
            b = np.expand_dims(b, 0)
            s = np.expand_dims(s, 0)
            c = np.expand_dims(c, 0)

        vis = visualize_bbox(page, b, c, s, ID_TO_NAMES)
        results.append(vis)
        # Extract and merge figure snippets for this page
        fig_indices = [i for i, cls in enumerate(c) if int(cls) == 3]
        fig_boxes = [b[i] for i in fig_indices]
        n = len(fig_boxes)
        if n > 0:
            # Union-find to group overlapping vertical spans
            parents = list(range(n))
            def find(i):
                if parents[i] != i:
                    parents[i] = find(parents[i])
                return parents[i]
            def union(i, j):
                pi, pj = find(i), find(j)
                if pi != pj:
                    parents[pj] = pi
            # Group overlapping boxes
            for i1 in range(n):
                y1_i, y2_i = fig_boxes[i1][1], fig_boxes[i1][3]
                for j1 in range(i1 + 1, n):
                    y1_j, y2_j = fig_boxes[j1][1], fig_boxes[j1][3]
                    if y1_i < y2_j and y1_j < y2_i:
                        union(i1, j1)
            from collections import defaultdict
            groups = defaultdict(list)
            for idx in range(n):
                root = find(idx)
                groups[root].append(idx)
            # Build merged crops sorted by top coordinate
            merged = []
            for grp in groups.values():
                xs1 = [fig_boxes[i][0] for i in grp]
                ys1 = [fig_boxes[i][1] for i in grp]
                xs2 = [fig_boxes[i][2] for i in grp]
                ys2 = [fig_boxes[i][3] for i in grp]
                x1_ = min(xs1); y1_ = min(ys1)
                x2_ = max(xs2); y2_ = max(ys2)
                crop = page.crop((int(x1_), int(y1_), int(x2_), int(y2_)))
                merged.append((y1_, crop))
            merged.sort(key=lambda x: x[0])
            # Keep only the merged crop images for this page
            page_figs = [crop for _, crop in merged]
        else:
            page_figs = []
        figure_snippets.append(page_figs)
    return results, figure_snippets
