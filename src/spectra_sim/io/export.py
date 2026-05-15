"""Dataset export helpers."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

import numpy as np

from spectra_sim.exceptions import ExportError
from spectra_sim.models import OutputConfig, OutputFormat, SpectrumRecord


def export_spectra(records: Sequence[SpectrumRecord], output_config: OutputConfig) -> Path:
    """Export spectra to the configured on-disk dataset format."""
    record_tuple = tuple(records)
    if not record_tuple:
        raise ExportError("cannot export an empty spectrum dataset")

    output_dir = Path(output_config.output_dir or "data/exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_config.output_format is OutputFormat.CSV:
        return export_spectra_to_csv(record_tuple, output_dir)
    if output_config.output_format is OutputFormat.NPZ:
        return export_spectra_to_npz(record_tuple, output_dir / "spectra_dataset.npz")
    if output_config.output_format is OutputFormat.HDF5:
        return export_spectra_to_hdf5(record_tuple, output_dir / "spectra_dataset.h5")
    if output_config.output_format is OutputFormat.PARQUET:
        return export_spectra_to_parquet(record_tuple, output_dir)

    raise ExportError(f"unsupported export format: {output_config.output_format}")


def export_spectra_to_csv(records: Sequence[SpectrumRecord], output_dir: Path) -> Path:
    """Write one long-form spectra table plus labels and metadata CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_spectra_csv(records, output_dir / "spectra.csv")
    _write_labels_csv(records, output_dir / "labels.csv")
    _write_metadata_csv(records, output_dir / "metadata.csv")
    return output_dir


def export_spectra_to_npz(records: Sequence[SpectrumRecord], output_path: Path) -> Path:
    """Write spectra arrays and JSON-encoded labels/metadata to a compressed NPZ."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {
        "sample_id": np.array([record.sample_id for record in records]),
        "wavenumber": _stack_component(records, "wavenumber"),
        "clean_absorbance": _stack_component(records, "clean_absorbance"),
        "baseline": _stack_component(records, "baseline"),
        "noise": _stack_component(records, "noise"),
        "final_absorbance": _stack_component(records, "final_absorbance"),
        "transmittance": _stack_component(records, "transmittance"),
        "labels_json": np.array([_labels_json(record) for record in records]),
        "metadata_json": np.array([json.dumps(dict(record.metadata), sort_keys=True) for record in records]),
    }
    np.savez_compressed(output_path, **arrays)
    return output_path


def export_spectra_to_hdf5(records: Sequence[SpectrumRecord], output_path: Path) -> Path:
    """Write spectra arrays and JSON metadata to an HDF5 file."""
    try:
        import h5py
    except ModuleNotFoundError as exc:
        raise ExportError("HDF5 export requires h5py. Install project dependencies first.") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    string_dtype = h5py.string_dtype(encoding="utf-8")
    with h5py.File(output_path, "w") as handle:
        handle.create_dataset("sample_id", data=[record.sample_id for record in records], dtype=string_dtype)
        handle.create_dataset("wavenumber", data=_stack_component(records, "wavenumber"))
        handle.create_dataset("clean_absorbance", data=_stack_component(records, "clean_absorbance"))
        handle.create_dataset("baseline", data=_stack_component(records, "baseline"))
        handle.create_dataset("noise", data=_stack_component(records, "noise"))
        handle.create_dataset("final_absorbance", data=_stack_component(records, "final_absorbance"))
        handle.create_dataset("transmittance", data=_stack_component(records, "transmittance"))
        handle.create_dataset("labels_json", data=[_labels_json(record) for record in records], dtype=string_dtype)
        handle.create_dataset(
            "metadata_json",
            data=[json.dumps(dict(record.metadata), sort_keys=True) for record in records],
            dtype=string_dtype,
        )
    return output_path


def export_spectra_to_parquet(records: Sequence[SpectrumRecord], output_dir: Path) -> Path:
    """Write long-form spectra, labels and metadata as Parquet tables."""
    try:
        import pandas as pd
        import pyarrow  # noqa: F401
    except ModuleNotFoundError as exc:
        raise ExportError("Parquet export requires pandas and pyarrow. Install project dependencies first.") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(_spectra_rows(records)).to_parquet(output_dir / "spectra.parquet", index=False)
    pd.DataFrame(_label_rows(records)).to_parquet(output_dir / "labels.parquet", index=False)
    pd.DataFrame(_metadata_rows(records)).to_parquet(output_dir / "metadata.parquet", index=False)
    return output_dir


def _write_spectra_csv(records: Sequence[SpectrumRecord], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sample_id",
                "point_index",
                "wavenumber",
                "clean_absorbance",
                "baseline",
                "noise",
                "final_absorbance",
                "transmittance",
            ],
        )
        writer.writeheader()
        writer.writerows(_spectra_rows(records))


def _write_labels_csv(records: Sequence[SpectrumRecord], output_path: Path) -> None:
    resident_names = _sorted_union(record.labels.resident_concentrations for record in records)
    presence_names = _sorted_union(record.labels.variable_presence for record in records)
    variable_names = _sorted_union(record.labels.variable_concentrations for record in records)
    fieldnames = (
        ["sample_id"]
        + [f"resident.{name}" for name in resident_names]
        + [f"presence.{name}" for name in presence_names]
        + [f"variable.{name}" for name in variable_names]
    )

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(_label_rows(records))


def _write_metadata_csv(records: Sequence[SpectrumRecord], output_path: Path) -> None:
    metadata_names = _sorted_union(record.metadata for record in records)
    fieldnames = ["sample_id"] + metadata_names
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(_metadata_rows(records))


def _spectra_rows(records: Sequence[SpectrumRecord]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in records:
        final_absorbance = record.final_absorbance or record.clean_absorbance
        transmittance = record.transmittance
        for point_index, wavenumber in enumerate(record.wavenumber):
            rows.append(
                {
                    "sample_id": record.sample_id,
                    "point_index": point_index,
                    "wavenumber": wavenumber,
                    "clean_absorbance": record.clean_absorbance[point_index],
                    "baseline": _component_value(record.baseline, point_index),
                    "noise": _component_value(record.noise, point_index),
                    "final_absorbance": final_absorbance[point_index],
                    "transmittance": _component_value(transmittance, point_index),
                }
            )
    return rows


def _label_rows(records: Sequence[SpectrumRecord]) -> list[dict[str, object]]:
    resident_names = _sorted_union(record.labels.resident_concentrations for record in records)
    presence_names = _sorted_union(record.labels.variable_presence for record in records)
    variable_names = _sorted_union(record.labels.variable_concentrations for record in records)
    rows: list[dict[str, object]] = []
    for record in records:
        row: dict[str, object] = {"sample_id": record.sample_id}
        row.update(
            {f"resident.{name}": record.labels.resident_concentrations.get(name, "") for name in resident_names}
        )
        row.update({f"presence.{name}": record.labels.variable_presence.get(name, "") for name in presence_names})
        row.update({f"variable.{name}": record.labels.variable_concentrations.get(name, "") for name in variable_names})
        rows.append(row)
    return rows


def _metadata_rows(records: Sequence[SpectrumRecord]) -> list[dict[str, object]]:
    metadata_names = _sorted_union(record.metadata for record in records)
    rows: list[dict[str, object]] = []
    for record in records:
        row: dict[str, object] = {"sample_id": record.sample_id}
        row.update({name: record.metadata.get(name, "") for name in metadata_names})
        rows.append(row)
    return rows


def _stack_component(records: Sequence[SpectrumRecord], field_name: str) -> np.ndarray:
    arrays = [_component_array(record, field_name) for record in records]
    first_shape = arrays[0].shape
    if any(array.shape != first_shape for array in arrays):
        raise ExportError(f"{field_name} arrays must share the same shape for NPZ export")
    return np.stack(arrays, axis=0)


def _component_array(record: SpectrumRecord, field_name: str) -> np.ndarray:
    values = getattr(record, field_name)
    if values:
        return np.asarray(values, dtype=float)
    if field_name in {"baseline", "noise"}:
        return np.zeros(len(record.wavenumber), dtype=float)
    if field_name == "final_absorbance":
        return np.asarray(record.clean_absorbance, dtype=float)
    if field_name == "transmittance":
        return np.exp(-np.asarray(record.clean_absorbance, dtype=float))
    return np.asarray(values, dtype=float)


def _component_value(values: Sequence[float], point_index: int) -> float | str:
    if not values:
        return ""
    return values[point_index]


def _labels_json(record: SpectrumRecord) -> str:
    return json.dumps(
        {
            "resident_concentrations": dict(record.labels.resident_concentrations),
            "variable_presence": dict(record.labels.variable_presence),
            "variable_concentrations": dict(record.labels.variable_concentrations),
        },
        sort_keys=True,
    )


def _sorted_union(mappings: Iterable[Mapping[str, object]]) -> list[str]:
    keys: set[str] = set()
    for mapping in mappings:
        keys.update(str(key) for key in mapping.keys())
    return sorted(keys)
