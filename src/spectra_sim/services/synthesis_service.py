"""Concrete synthesis service implementation."""

from __future__ import annotations

from spectra_sim.exceptions import SynthesisError
from spectra_sim.models import GasComponent, SynthesisConfig, SpectrumLabels, SpectrumRecord
from spectra_sim.services.interfaces import LineDatabaseService
from spectra_sim.synthesis.absorbance import synthesize_single_gas_absorbance
from spectra_sim.synthesis.grid import build_wavenumber_grid


class LocalSynthesisService:
    """Synthesis service that reads line data only from the local database."""

    def __init__(self, line_database: LineDatabaseService) -> None:
        self._line_database = line_database

    def preview(self, config: SynthesisConfig) -> SpectrumRecord:
        return self.synthesize_single(config)

    def synthesize_single(self, config: SynthesisConfig) -> SpectrumRecord:
        component = self._single_component(config)
        wavenumber = build_wavenumber_grid(config.spectral_axis)

        # 合成阶段只允许本地检索，不触发任何 HAPI 下载。
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
        raise SynthesisError("混合气体合成将在 P5 阶段实现")

    def _single_component(self, config: SynthesisConfig) -> GasComponent:
        components = tuple(gas for gas in (*config.resident_gases, *config.variable_gases) if gas.presence)
        if len(components) != 1:
            raise SynthesisError("单气体合成要求且仅要求一个存在的气体组分")
        return components[0]

    def _labels_for_component(self, config: SynthesisConfig, component: GasComponent) -> SpectrumLabels:
        if component in config.resident_gases:
            return SpectrumLabels(resident_concentrations={component.name: component.concentration})
        return SpectrumLabels(
            variable_presence={component.name: 1 if component.presence else 0},
            variable_concentrations={component.name: component.concentration if component.presence else 0.0},
        )

