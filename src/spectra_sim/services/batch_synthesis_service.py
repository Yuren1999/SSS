"""Concrete batch synthesis service implementation."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping
from uuid import uuid4

from spectra_sim.batch import expand_parameter_grid
from spectra_sim.exceptions import BatchError
from spectra_sim.models import BatchSampleFailure, BatchTaskResult, SpectrumRecord, TaskStatus
from spectra_sim.services.interfaces import SynthesisService


class LocalBatchSynthesisService:
    """In-memory serial batch runner for first-version dataset generation."""

    def __init__(self, synthesis_service: SynthesisService) -> None:
        self._synthesis_service = synthesis_service
        self._results: dict[str, BatchTaskResult] = {}

    def expand_parameters(self, batch_config: Mapping[str, Any]):
        return expand_parameter_grid(batch_config)

    def run_batch(self, batch_config: Mapping[str, Any]) -> str:
        task_id = str(batch_config.get("task_id") or f"batch-{uuid4().hex[:12]}")
        configs = self.expand_parameters(batch_config)
        records: list[SpectrumRecord] = []
        failures: list[BatchSampleFailure] = []

        for index, config in enumerate(configs):
            try:
                record = self._synthesis_service.preview(config)
                records.append(self._tag_record(record, task_id=task_id, sample_index=index))
            except Exception as exc:  # noqa: BLE001 - batch tasks must retain per-sample failures.
                failures.append(BatchSampleFailure(sample_index=index, message=str(exc)))

        status = TaskStatus.SUCCEEDED if not failures else TaskStatus.FAILED
        message = f"{len(records)} samples succeeded, {len(failures)} samples failed"
        self._results[task_id] = BatchTaskResult(
            task_id=task_id,
            status=status,
            records=tuple(records),
            failures=tuple(failures),
            message=message,
        )
        return task_id

    def pause_task(self, task_id: str) -> None:
        self._require_task(task_id)

    def resume_task(self, task_id: str) -> None:
        self._require_task(task_id)

    def get_task_result(self, task_id: str) -> BatchTaskResult:
        return self._require_task(task_id)

    def _require_task(self, task_id: str) -> BatchTaskResult:
        try:
            return self._results[task_id]
        except KeyError as exc:
            raise BatchError(f"unknown batch task id: {task_id}") from exc

    def _tag_record(self, record: SpectrumRecord, task_id: str, sample_index: int) -> SpectrumRecord:
        metadata = dict(record.metadata)
        metadata.update({"batch_task_id": task_id, "sample_index": sample_index})
        return replace(
            record,
            sample_id=f"{task_id}-{sample_index:06d}",
            metadata=metadata,
        )
