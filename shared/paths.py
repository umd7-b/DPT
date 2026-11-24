"""Project-owned paths; the external dataset stays in its original location."""
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = Path(r"D:\TuNam4\dataset_HF_CFD_final")
MODEL_PATH = PROJECT_ROOT / "models/face_landmarker.task"
