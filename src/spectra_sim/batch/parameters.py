"""Parameter expansion helpers for batch synthesis."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass, replace
from itertools import product
from typing import Any

from spectra_sim.exceptions import ValidationError
from spectra_sim.models import GasComponent, SynthesisConfig


def expand_parameter_grid(batch_config: Mapping[str, Any]) -> tuple[SynthesisConfig, ...]:
    """Expand a batch config into concrete synthesis configs.

    The supported config shape is intentionally small and explicit:

    {
        "base_config": SynthesisConfig(...),
        "grid": {
            "environment.pressure": [0.8, 1.0],
            "variable_gases.CH4.concentration": [0.0, 2.0],
            "noise.seed": [1, 2],
        },
    }
    """
    base_config = batch_config.get("base_config")
    if not isinstance(base_config, SynthesisConfig):
        raise ValidationError("batch_config.base_config must be a SynthesisConfig")

    grid = batch_config.get("grid", {})
    if not isinstance(grid, Mapping):
        raise ValidationError("batch_config.grid must be a mapping")
    if not grid:
        return (base_config,)

    paths = tuple(str(path) for path in grid.keys())
    values = tuple(_as_value_tuple(path, grid[path]) for path in paths)

    configs = []
    for combination in product(*values):
        overrides = dict(zip(paths, combination, strict=True))
        configs.append(apply_parameter_overrides(base_config, overrides))
    return tuple(configs)


def apply_parameter_overrides(
    config: SynthesisConfig,
    overrides: Mapping[str, Any],
) -> SynthesisConfig:
    """Apply path-based overrides to one synthesis config."""
    updated = config
    for path, value in overrides.items():
        updated = _set_config_path(updated, path, value)
    return updated


def _as_value_tuple(path: str, values: Any) -> tuple[Any, ...]:
    if isinstance(values, str) or not isinstance(values, Sequence):
        raise ValidationError(f"grid value for {path} must be a non-empty sequence")
    value_tuple = tuple(values)
    if not value_tuple:
        raise ValidationError(f"grid value for {path} must not be empty")
    return value_tuple


def _set_config_path(config: SynthesisConfig, path: str, value: Any) -> SynthesisConfig:
    parts = path.split(".")
    if len(parts) < 2:
        raise ValidationError(f"invalid parameter path: {path}")

    root = parts[0]
    if root in {"environment", "spectral_axis", "noise", "baseline", "output"}:
        current = getattr(config, root)
        replacement = _replace_nested_value(current, parts[1:], value)
        return replace(config, **{root: replacement})

    if root in {"resident_gases", "variable_gases"}:
        if len(parts) != 3:
            raise ValidationError(f"gas parameter path must be {root}.<gas_name>.<field>")
        gases = getattr(config, root)
        replacement = _replace_gas_value(gases, gas_name=parts[1], field_name=parts[2], value=value)
        return replace(config, **{root: replacement})

    raise ValidationError(f"unsupported parameter path root: {root}")


def _replace_nested_value(target: Any, parts: list[str], value: Any) -> Any:
    if not parts:
        return value

    if isinstance(target, Mapping):
        updated = dict(target)
        if len(parts) != 1:
            raise ValidationError("mapping parameter paths support one key after parameters")
        updated[parts[0]] = value
        return updated

    if not is_dataclass(target):
        raise ValidationError(f"cannot apply nested override to {type(target).__name__}")

    field_name = parts[0]
    if not hasattr(target, field_name):
        raise ValidationError(f"{type(target).__name__} has no field {field_name}")

    if len(parts) == 1:
        return replace(target, **{field_name: value})

    child = getattr(target, field_name)
    return replace(target, **{field_name: _replace_nested_value(child, parts[1:], value)})


def _replace_gas_value(
    gases: tuple[GasComponent, ...],
    gas_name: str,
    field_name: str,
    value: Any,
) -> tuple[GasComponent, ...]:
    updated_gases = []
    found = False
    for gas in gases:
        if gas.name == gas_name:
            found = True
            if not hasattr(gas, field_name):
                raise ValidationError(f"GasComponent has no field {field_name}")
            updated_gases.append(replace(gas, **{field_name: value}))
        else:
            updated_gases.append(gas)

    if not found:
        raise ValidationError(f"gas {gas_name} is not present in the base config")
    return tuple(updated_gases)
