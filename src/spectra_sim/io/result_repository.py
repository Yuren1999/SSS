"""Persistent synthesized result repository."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np

from spectra_sim.exceptions import ExportError
from spectra_sim.io.export import export_spectra_to_npz
from spectra_sim.models import SavedResultDataset, SpectrumLabels, SpectrumRecord

CATALOG_FILE_NAME = "dataset.json"
RECORDS_FILE_NAME = "records.npz"


class LocalResultRepository:
    """Store and load synthesized result datasets under a local directory."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_records(self, records: tuple[SpectrumRecord, ...], name: str | None = None) -> SavedResultDataset:
        if not records:
            raise ExportError("cannot persist an empty result dataset")

        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        dataset_id = f"result-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
        dataset_name = name or dataset_id
        dataset_dir = self.root_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=False)

        export_spectra_to_npz(records, dataset_dir / RECORDS_FILE_NAME)
        metadata = {
            "dataset_id": dataset_id,
            "name": dataset_name,
            "record_count": len(records),
            "storage_path": str(dataset_dir),
            "created_at": created_at,
            "sample_ids": [record.sample_id for record in records],
        }
        (dataset_dir / CATALOG_FILE_NAME).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self._dataset_from_metadata(metadata)

    def list_datasets(self) -> tuple[SavedResultDataset, ...]:
        datasets = []
        for catalog_path in self.root_dir.glob(f"*/{CATALOG_FILE_NAME}"):
            try:
                metadata = json.loads(catalog_path.read_text(encoding="utf-8"))
                datasets.append(self._dataset_from_metadata(metadata))
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
        return tuple(sorted(datasets, key=lambda dataset: dataset.created_at, reverse=True))

    def load_records(self, dataset_id: str) -> tuple[SpectrumRecord, ...]:
        records_path = self.root_dir / dataset_id / RECORDS_FILE_NAME
        if not records_path.exists():
            raise ExportError(f"result dataset does not exist: {dataset_id}")

        with np.load(records_path, allow_pickle=False) as dataset:
            sample_ids = dataset["sample_id"].tolist()
            labels_json = dataset["labels_json"].tolist()
            metadata_json = dataset["metadata_json"].tolist()
            records = []
            for index, sample_id in enumerate(sample_ids):
                labels = _labels_from_json(labels_json[index])
                metadata = json.loads(metadata_json[index])
                records.append(
                    SpectrumRecord(
                        sample_id=str(sample_id),
                        wavenumber=dataset["wavenumber"][index].tolist(),
                        clean_absorbance=dataset["clean_absorbance"][index].tolist(),
                        baseline=dataset["baseline"][index].tolist(),
                        noise=dataset["noise"][index].tolist(),
                        final_absorbance=dataset["final_absorbance"][index].tolist(),
                        transmittance=dataset["transmittance"][index].tolist(),
                        labels=labels,
                        metadata=metadata,
                    )
                )
        return tuple(records)

    def _dataset_from_metadata(self, metadata: dict[str, object]) -> SavedResultDataset:
        return SavedResultDataset(
            dataset_id=str(metadata["dataset_id"]),
            name=str(metadata["name"]),
            record_count=int(metadata["record_count"]),
            storage_path=Path(str(metadata["storage_path"])),
            created_at=str(metadata["created_at"]),
        )


def _labels_from_json(value: str) -> SpectrumLabels:
    data = json.loads(value)
    return SpectrumLabels(
        resident_concentrations=data.get("resident_concentrations", {}),
        variable_presence=data.get("variable_presence", {}),
        variable_concentrations=data.get("variable_concentrations", {}),
    )
