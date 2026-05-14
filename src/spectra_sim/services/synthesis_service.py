"""Concrete synthesis service implementation."""

from __future__ import annotations

import numpy as np

from spectra_sim.exceptions import SynthesisError
from spectra_sim.models import (
    BaselineType,
    GasComponent,
    NoiseType,
    SynthesisConfig,
    SpectrumLabels,
    SpectrumRecord,
)
from spectra_sim.services.interfaces import LineDatabaseService
from spectra_sim.synthesis.absorbance import synthesize_single_gas_absorbance
from spectra_sim.synthesis.grid import build_wavenumber_grid
from spectra_sim.synthesis.mixture import synthesize_mixture_absorbance


class LocalSynthesisService:
    """Synthesis service that reads line data only from the local database."""

    def __init__(self, line_database: LineDatabaseService) -> None:
        self._line_database = line_database

    def preview(self, config: SynthesisConfig) -> SpectrumRecord:
        present_components = self._present_components(config)
        has_perturbation = (
            config.noise.noise_type is not NoiseType.NONE
            or config.baseline.baseline_type is not BaselineType.NONE
        )
        if len(present_components) == 1 and not has_perturbation:
            return self.synthesize_single(config)
        return self.synthesize_mixture(config)

    def synthesize_single(self, config: SynthesisConfig) -> SpectrumRecord:
        component = self._single_component(config)
        wavenumber = build_wavenumber_grid(config.spectral_axis)

        line_table = self._line_database.search_lines(component.name, config.spectral_axis.wavenumber_range)
        result = synthesize_single_gas_absorbance(
            wavenumber=wavenumber,
            records=tuple(line_table.records),
            component=component,
            environment=config.environment,
            nu_step=config.spectral_axis.nu_step,
        )

        labels = self._labels_for_component(config, component)
        return SpectrumRecord(
            sample_id=f"single-{component.name}",
            wavenumber=result.wavenumber.tolist(),
            clean_absorbance=result.absorbance.tolist(),
            final_absorbance=result.absorbance.tolist(),
            transmittance=result.transmittance.tolist(),
            labels=labels,
            metadata={
                "gas_name": component.name,
                "line_count": len(line_table.records),
                "synthesis_mode": "single",
            },
        )

    def synthesize_mixture(self, config: SynthesisConfig) -> SpectrumRecord:
        components = self._present_components(config)
        if not components:
            raise SynthesisError("Mixture synthesis requires at least one present gas component")

        wavenumber = build_wavenumber_grid(config.spectral_axis)
        component_absorbances = []
        line_count = 0

        for component in components:
            if component.concentration == 0:
                component_absorbances.append(np.zeros_like(wavenumber, dtype=float))
                continue

            line_table = self._line_database.search_lines(component.name, config.spectral_axis.wavenumber_range)
            line_count += len(line_table.records)
            result = synthesize_single_gas_absorbance(
                wavenumber=wavenumber,
                records=tuple(line_table.records),
                component=component,
                environment=config.environment,
                nu_step=config.spectral_axis.nu_step,
            )
            component_absorbances.append(result.absorbance)

        result = synthesize_mixture_absorbance(
            wavenumber=wavenumber,
            component_absorbances=component_absorbances,
            baseline_config=config.baseline,
            noise_config=config.noise,
        )

        gas_names = ",".join(component.name for component in components)
        return SpectrumRecord(
            sample_id=f"mixture-{gas_names}",
            wavenumber=result.wavenumber.tolist(),
            clean_absorbance=result.clean_absorbance.tolist(),
            baseline=result.baseline.tolist(),
            noise=result.noise.tolist(),
            final_absorbance=result.final_absorbance.tolist(),
            transmittance=result.transmittance.tolist(),
            labels=self._labels_for_config(config),
            metadata={
                "gas_count": len(components),
                "gas_names": gas_names,
                "line_count": line_count,
                "synthesis_mode": "mixture",
            },
        )

    def _present_components(self, config: SynthesisConfig) -> tuple[GasComponent, ...]:
        return tuple(gas for gas in (*config.resident_gases, *config.variable_gases) if gas.presence)

    def _single_component(self, config: SynthesisConfig) -> GasComponent:
        components = self._present_components(config)
        if len(components) != 1:
            raise SynthesisError("Single-gas synthesis requires exactly one present gas component")
        return components[0]

    def _labels_for_component(self, config: SynthesisConfig, component: GasComponent) -> SpectrumLabels:
        if component in config.resident_gases:
            return SpectrumLabels(resident_concentrations={component.name: component.concentration})
        return SpectrumLabels(
            variable_presence={component.name: 1 if component.presence else 0},
            variable_concentrations={component.name: component.concentration if component.presence else 0.0},
        )

    def _labels_for_config(self, config: SynthesisConfig) -> SpectrumLabels:
        return SpectrumLabels(
            resident_concentrations={
                gas.name: gas.concentration if gas.presence else 0.0
                for gas in config.resident_gases
            },
            variable_presence={
                gas.name: 1 if gas.presence else 0
                for gas in config.variable_gases
            },
            variable_concentrations={
                gas.name: gas.concentration if gas.presence else 0.0
                for gas in config.variable_gases
            },
        )
