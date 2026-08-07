import os
import json
from typing import Dict, Optional
from backend.models.clearance import ClearanceReport

try:
    from google.cloud import firestore
except ImportError:
    firestore = None


class ClearanceStorage:
    """
    Persistent storage layer using Firestore in Cloud Run,
    backed by local JSON persistence for standalone execution.
    """

    def __init__(self):
        self.db = None
        self.local_file = os.path.join(os.path.dirname(__file__), "..", "data_store.json")
        self.cache: Dict[str, ClearanceReport] = {}

        if firestore is not None and os.getenv("GOOGLE_CLOUD_PROJECT"):
            try:
                self.db = firestore.Client()
            except Exception:
                self.db = None

        self._load_local_store()

    def _load_local_store(self):
        if os.path.exists(self.local_file):
            try:
                with open(self.local_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for script_id, raw in data.items():
                        self.cache[script_id] = ClearanceReport.model_validate(raw)
            except Exception:
                pass

    def _save_local_store(self):
        try:
            os.makedirs(os.path.dirname(self.local_file), exist_ok=True)
            serializable = {k: v.model_dump() for k, v in self.cache.items()}
            with open(self.local_file, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
        except Exception:
            pass

    def save_report(self, report: ClearanceReport):
        self.cache[report.script_id] = report
        self._save_local_store()

        if self.db:
            try:
                doc_ref = self.db.collection("clearance_reports").document(report.script_id)
                doc_ref.set(report.model_dump())
            except Exception:
                pass

    def get_report(self, script_id: str) -> Optional[ClearanceReport]:
        if script_id in self.cache:
            return self.cache[script_id]

        if self.db:
            try:
                doc_ref = self.db.collection("clearance_reports").document(script_id)
                doc = doc_ref.get()
                if doc.exists:
                    report = ClearanceReport.model_validate(doc.to_dict())
                    self.cache[script_id] = report
                    return report
            except Exception:
                pass

        return None

    def get_all_reports(self) -> Dict[str, ClearanceReport]:
        return self.cache


storage = ClearanceStorage()
