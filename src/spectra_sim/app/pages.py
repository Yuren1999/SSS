"""GUI pages for the main desktop window."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from spectra_sim.models import (
    DownloadMode,
    DownloadTaskInfo,
    DownloadTaskRequest,
    EnvironmentConfig,
    GasComponent,
    GasRole,
    GasSpec,
    OutputConfig,
    OutputFormat,
    SavedResultDataset,
    SpectralAxisConfig,
    SpectrumRecord,
    SynthesisConfig,
    WavenumberRange,
)
from spectra_sim.app.result_store import ResultStore
from spectra_sim.services import (
    BatchSynthesisService,
    ExportService,
    LineDatabaseService,
    LineDownloadService,
    ResultRepositoryService,
    SynthesisService,
)


class DownloadTaskWorker(QThread):
    """Run one download task away from the GUI thread."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, service: LineDownloadService, task_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._task_id = task_id

    def run(self) -> None:
        try:
            self.succeeded.emit(self._service.run_download_task(self._task_id))
        except Exception as exc:  # noqa: BLE001 - GUI must surface domain and adapter errors uniformly.
            self.failed.emit(str(exc))


class DownloadPage(QWidget):
    """Independent page for HITRAN/HAPI line downloads."""

    def __init__(
        self,
        download_service: LineDownloadService,
        database_service: LineDatabaseService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("downloadPage")
        self._download_service = download_service
        self._database_service = database_service
        self._worker: DownloadTaskWorker | None = None

        self._gas_name = QLineEdit("CO2", self)
        self._molecule_id = QSpinBox(self)
        self._molecule_id.setRange(1, 999)
        self._molecule_id.setValue(2)
        self._nu_min = _double_spin_box(1.0, 100000.0, 6000.0)
        self._nu_max = _double_spin_box(1.0, 100000.0, 6500.0)
        self._task_name = QLineEdit("CO2 6000-6500", self)
        self._mode = QComboBox(self)
        for mode in (DownloadMode.SKIP_COVERED, DownloadMode.ADD_MISSING):
            self._mode.addItem(mode.value, mode)

        self._task_table = QTableWidget(0, 6, self)
        self._task_table.setHorizontalHeaderLabels(["任务ID", "气体", "波数范围", "模式", "状态", "消息"])
        self._task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._task_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self._status = QTextEdit(self)
        self._status.setReadOnly(True)
        self._status.setFixedHeight(86)

        self._build_layout()
        self.refresh_tasks()

    def _build_layout(self) -> None:
        form = QFormLayout()
        form.addRow("气体名称", self._gas_name)
        form.addRow("HITRAN 分子编号", self._molecule_id)
        form.addRow("起始波数 cm^-1", self._nu_min)
        form.addRow("结束波数 cm^-1", self._nu_max)
        form.addRow("任务名称", self._task_name)
        form.addRow("下载模式", self._mode)

        create_button = QPushButton("创建下载任务", self)
        create_button.clicked.connect(self.create_task)
        run_button = QPushButton("运行选中任务", self)
        run_button.clicked.connect(self.run_selected_task)
        refresh_button = QPushButton("刷新任务列表", self)
        refresh_button.clicked.connect(self.refresh_tasks)

        button_layout = QHBoxLayout()
        button_layout.addWidget(create_button)
        button_layout.addWidget(run_button)
        button_layout.addWidget(refresh_button)
        button_layout.addStretch(1)

        group = QGroupBox("谱线下载", self)
        group_layout = QVBoxLayout(group)
        group_layout.addLayout(form)
        group_layout.addLayout(button_layout)

        layout = QVBoxLayout(self)
        layout.addWidget(group)
        layout.addWidget(self._task_table)
        layout.addWidget(QLabel("运行消息", self))
        layout.addWidget(self._status)

    def create_task(self) -> None:
        try:
            task = self._download_service.create_download_task(self._build_request())
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"创建失败：{exc}")
            return
        self._set_status(f"已创建下载任务：{task.task_id}")
        self.refresh_tasks()

    def run_selected_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            self._set_status("请先选择一个下载任务")
            return
        if self._worker is not None and self._worker.isRunning():
            self._set_status("已有下载任务正在运行")
            return

        self._set_status(f"正在运行下载任务：{task_id}")
        self._worker = DownloadTaskWorker(self._download_service, task_id, self)
        self._worker.succeeded.connect(self._handle_task_finished)
        self._worker.failed.connect(self._handle_task_failed)
        self._worker.start()

    def refresh_tasks(self) -> None:
        try:
            tasks = tuple(self._download_service.list_download_tasks())
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"读取任务失败：{exc}")
            tasks = ()
        self._fill_task_table(tasks)

    def _build_request(self) -> DownloadTaskRequest:
        return DownloadTaskRequest(
            gas=GasSpec(self._gas_name.text().strip(), self._molecule_id.value()),
            wavenumber_range=WavenumberRange(self._nu_min.value(), self._nu_max.value()),
            mode=self._mode.currentData(),
            task_name=self._task_name.text().strip(),
        )

    def _fill_task_table(self, tasks: Sequence[DownloadTaskInfo]) -> None:
        self._task_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            values = [
                task.task_id,
                task.request.gas.gas_name,
                f"{task.request.wavenumber_range.nu_min:g}-{task.request.wavenumber_range.nu_max:g}",
                task.request.mode.value,
                task.status.value,
                task.message,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, task.task_id)
                self._task_table.setItem(row, column, item)
        self._task_table.resizeColumnsToContents()

    def _selected_task_id(self) -> str | None:
        selected = self._task_table.selectionModel().selectedRows()
        if not selected:
            return None
        item = self._task_table.item(selected[0].row(), 0)
        return None if item is None else str(item.data(Qt.ItemDataRole.UserRole))

    def _handle_task_finished(self, task: DownloadTaskInfo) -> None:
        self._set_status(f"下载任务完成：{task.status.value}，{task.message}")
        self.refresh_tasks()

    def _handle_task_failed(self, message: str) -> None:
        self._set_status(f"下载任务失败：{message}")
        self.refresh_tasks()

    def _set_status(self, message: str) -> None:
        self._status.setPlainText(message)


class LocalDatabasePage(QWidget):
    """Read-only page for local line database coverage."""

    def __init__(self, database_service: LineDatabaseService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("localDatabasePage")
        self._database_service = database_service
        self._table = QTableWidget(0, 3, self)
        self._table.setHorizontalHeaderLabels(["气体", "HITRAN 编号", "本地覆盖范围"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        refresh_button = QPushButton("刷新本地数据库", self)
        refresh_button.clicked.connect(self.refresh)
        layout = QVBoxLayout(self)
        layout.addWidget(refresh_button)
        layout.addWidget(self._table)
        self.refresh()

    def refresh(self) -> None:
        gases = tuple(self._database_service.list_gases())
        self._table.setRowCount(len(gases))
        for row, gas in enumerate(gases):
            coverage = self._database_service.get_coverage(gas.gas_name)
            coverage_text = "; ".join(f"{item.nu_min:g}-{item.nu_max:g}" for item in coverage) or "无"
            for column, value in enumerate((gas.gas_name, gas.hitran_molecule_id, coverage_text)):
                self._table.setItem(row, column, QTableWidgetItem(str(value)))
        self._table.resizeColumnsToContents()


class SynthesisPage(QWidget):
    """Independent page for local-only spectrum synthesis."""

    def __init__(
        self,
        synthesis_service: SynthesisService,
        database_service: LineDatabaseService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("synthesisPage")
        self._synthesis_service = synthesis_service
        self._database_service = database_service

        self._nu_min = _double_spin_box(1.0, 100000.0, 6000.0)
        self._nu_max = _double_spin_box(1.0, 100000.0, 6500.0)
        self._nu_step = _double_spin_box(0.0001, 1000.0, 1.0, decimals=4)
        self._pressure = _double_spin_box(0.0001, 1000.0, 1.0, decimals=4)
        self._temperature = _double_spin_box(1.0, 5000.0, 296.0)
        self._path_length = _double_spin_box(0.0001, 100000.0, 10.0, decimals=4)

        self._resident_gas = QLineEdit("CO2", self)
        self._resident_concentration = _double_spin_box(0.0, 1.0e9, 400.0)
        self._variable_gas = QLineEdit("CH4", self)
        self._variable_concentration = _double_spin_box(0.0, 1.0e9, 2.0)
        self._variable_presence = QCheckBox("变量组分存在", self)
        self._variable_presence.setChecked(True)

        self._message = QTextEdit(self)
        self._message.setReadOnly(True)
        self._message.setFixedHeight(90)
        self._preview_table = QTableWidget(0, 4, self)
        self._preview_table.setHorizontalHeaderLabels(["波数", "clean", "final", "transmittance"])
        self._preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self._build_layout()

    def _build_layout(self) -> None:
        axis_form = QFormLayout()
        axis_form.addRow("起始波数 cm^-1", self._nu_min)
        axis_form.addRow("结束波数 cm^-1", self._nu_max)
        axis_form.addRow("采样间隔 cm^-1", self._nu_step)
        axis_form.addRow("压力 atm", self._pressure)
        axis_form.addRow("温度 K", self._temperature)
        axis_form.addRow("光程 cm", self._path_length)

        gas_form = QFormLayout()
        gas_form.addRow("常驻气体", self._resident_gas)
        gas_form.addRow("常驻浓度 ppm", self._resident_concentration)
        gas_form.addRow("变量气体", self._variable_gas)
        gas_form.addRow("变量浓度 ppm", self._variable_concentration)
        gas_form.addRow("", self._variable_presence)

        form_layout = QHBoxLayout()
        axis_group = QGroupBox("光谱与环境", self)
        axis_group.setLayout(axis_form)
        gas_group = QGroupBox("本地合成组分", self)
        gas_group.setLayout(gas_form)
        form_layout.addWidget(axis_group)
        form_layout.addWidget(gas_group)

        check_button = QPushButton("检查本地覆盖", self)
        check_button.clicked.connect(self.check_local_coverage)
        preview_button = QPushButton("生成本地预览", self)
        preview_button.clicked.connect(self.preview_spectrum)
        button_layout = QHBoxLayout()
        button_layout.addWidget(check_button)
        button_layout.addWidget(preview_button)
        button_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        layout.addWidget(QLabel("消息", self))
        layout.addWidget(self._message)
        layout.addWidget(self._preview_table)

    def check_local_coverage(self) -> None:
        try:
            config = self._build_config()
            gas_names = [gas.name for gas in (*config.resident_gases, *config.variable_gases) if gas.presence]
            results = self._database_service.check_coverage(gas_names, config.spectral_axis.wavenumber_range)
            lines = []
            for result in results:
                if result.is_covered:
                    lines.append(f"{result.gas_name}: 已覆盖")
                else:
                    missing = ", ".join(f"{item.nu_min:g}-{item.nu_max:g}" for item in result.missing_ranges)
                    lines.append(f"{result.gas_name}: 缺失 {missing}")
            self._message.setPlainText("\n".join(lines) or "没有需要检查的存在组分")
        except Exception as exc:  # noqa: BLE001
            self._message.setPlainText(f"覆盖检查失败：{exc}")

    def preview_spectrum(self) -> None:
        try:
            record = self._synthesis_service.preview(self._build_config())
        except Exception as exc:  # noqa: BLE001
            self._message.setPlainText(f"合成失败：{exc}")
            return

        self._message.setPlainText(
            f"合成完成：{record.sample_id}，点数 {len(record.wavenumber)}。"
            "本页面只读取本地数据库，不自动下载谱线。"
        )
        self._fill_preview_table(record.wavenumber, record.clean_absorbance, record.final_absorbance, record.transmittance)

    def _build_config(self) -> SynthesisConfig:
        resident = GasComponent(
            name=self._resident_gas.text().strip(),
            concentration=self._resident_concentration.value(),
            role=GasRole.RESIDENT,
        )
        variable_presence = self._variable_presence.isChecked()
        variable = GasComponent(
            name=self._variable_gas.text().strip(),
            concentration=self._variable_concentration.value() if variable_presence else 0.0,
            role=GasRole.VARIABLE,
            presence=variable_presence,
        )
        return SynthesisConfig(
            spectral_axis=SpectralAxisConfig(
                WavenumberRange(self._nu_min.value(), self._nu_max.value()),
                nu_step=self._nu_step.value(),
            ),
            environment=EnvironmentConfig(
                pressure=self._pressure.value(),
                temperature=self._temperature.value(),
                path_length=self._path_length.value(),
            ),
            resident_gases=(resident,),
            variable_gases=(variable,),
        )

    def _fill_preview_table(
        self,
        wavenumber: Sequence[float],
        clean_absorbance: Sequence[float],
        final_absorbance: Sequence[float],
        transmittance: Sequence[float],
    ) -> None:
        max_rows = min(50, len(wavenumber))
        self._preview_table.setRowCount(max_rows)
        for row in range(max_rows):
            values = (
                wavenumber[row],
                clean_absorbance[row],
                final_absorbance[row] if final_absorbance else clean_absorbance[row],
                transmittance[row] if transmittance else "",
            )
            for column, value in enumerate(values):
                self._preview_table.setItem(row, column, QTableWidgetItem(str(value)))
        self._preview_table.resizeColumnsToContents()


class BatchExportPage(QWidget):
    """Page for local batch synthesis and dataset export."""

    def __init__(
        self,
        batch_service: BatchSynthesisService,
        export_service: ExportService,
        result_store: ResultStore,
        result_repository: ResultRepositoryService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("batchExportPage")
        self._batch_service = batch_service
        self._export_service = export_service
        self._result_store = result_store
        self._result_repository = result_repository

        self._nu_min = _double_spin_box(1.0, 100000.0, 6000.0)
        self._nu_max = _double_spin_box(1.0, 100000.0, 6500.0)
        self._nu_step = _double_spin_box(0.0001, 1000.0, 1.0, decimals=4)
        self._pressure = _double_spin_box(0.0001, 1000.0, 1.0, decimals=4)
        self._temperature = _double_spin_box(1.0, 5000.0, 296.0)
        self._path_length = _double_spin_box(0.0001, 100000.0, 10.0, decimals=4)

        self._resident_gas = QLineEdit("CO2", self)
        self._resident_concentration = _double_spin_box(0.0, 1.0e9, 400.0)
        self._variable_gas = QLineEdit("CH4", self)
        self._variable_start = _double_spin_box(0.0, 1.0e9, 0.0)
        self._variable_end = _double_spin_box(0.0, 1.0e9, 2.0)
        self._sample_count = QSpinBox(self)
        self._sample_count.setRange(1, 100000)
        self._sample_count.setValue(3)

        self._output_format = QComboBox(self)
        for output_format in (OutputFormat.CSV, OutputFormat.NPZ, OutputFormat.HDF5, OutputFormat.PARQUET):
            self._output_format.addItem(output_format.value, output_format)
        self._output_dir = QLineEdit(str(Path("data") / "outputs"), self)

        self._message = QTextEdit(self)
        self._message.setReadOnly(True)
        self._message.setFixedHeight(90)
        self._summary_table = QTableWidget(0, 5, self)
        self._summary_table.setHorizontalHeaderLabels(["样本ID", "点数", "常驻浓度", "变量存在", "变量浓度"])
        self._summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self._build_layout()

    def _build_layout(self) -> None:
        axis_form = QFormLayout()
        axis_form.addRow("起始波数 cm^-1", self._nu_min)
        axis_form.addRow("结束波数 cm^-1", self._nu_max)
        axis_form.addRow("采样间隔 cm^-1", self._nu_step)
        axis_form.addRow("压力 atm", self._pressure)
        axis_form.addRow("温度 K", self._temperature)
        axis_form.addRow("光程 cm", self._path_length)

        batch_form = QFormLayout()
        batch_form.addRow("常驻气体", self._resident_gas)
        batch_form.addRow("常驻浓度 ppm", self._resident_concentration)
        batch_form.addRow("变量气体", self._variable_gas)
        batch_form.addRow("变量浓度起点 ppm", self._variable_start)
        batch_form.addRow("变量浓度终点 ppm", self._variable_end)
        batch_form.addRow("样本数", self._sample_count)

        output_form = QFormLayout()
        output_form.addRow("导出格式", self._output_format)
        output_form.addRow("输出目录", self._output_dir)

        axis_group = QGroupBox("批量光谱与环境", self)
        axis_group.setLayout(axis_form)
        batch_group = QGroupBox("参数网格", self)
        batch_group.setLayout(batch_form)
        output_group = QGroupBox("导出", self)
        output_group.setLayout(output_form)

        form_layout = QHBoxLayout()
        form_layout.addWidget(axis_group)
        form_layout.addWidget(batch_group)
        form_layout.addWidget(output_group)

        run_button = QPushButton("运行本地批量合成", self)
        run_button.clicked.connect(self.run_batch)
        export_button = QPushButton("导出当前结果", self)
        export_button.clicked.connect(self.export_current_records)
        button_layout = QHBoxLayout()
        button_layout.addWidget(run_button)
        button_layout.addWidget(export_button)
        button_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        layout.addWidget(QLabel("消息", self))
        layout.addWidget(self._message)
        layout.addWidget(self._summary_table)

    def run_batch(self) -> None:
        try:
            batch_config = self._build_batch_config()
            task_id = self._batch_service.run_batch(batch_config)
            result = self._batch_service.get_task_result(task_id)
        except Exception as exc:  # noqa: BLE001
            self._message.setPlainText(f"批量合成失败：{exc}")
            return

        self._result_store.set_records(result.records)
        saved_dataset = None
        if result.records:
            try:
                saved_dataset = self._result_repository.save_records(result.records, name=result.task_id)
            except Exception as exc:  # noqa: BLE001
                self._message.setPlainText(f"批量完成，但持久化保存失败：{exc}")
        self._fill_summary_table(result.records)
        failure_text = "" if not result.failures else f"，失败样本 {len(result.failures)} 个"
        save_text = "" if saved_dataset is None else f"，已保存结果集 {saved_dataset.dataset_id}"
        if saved_dataset is not None or not result.records:
            self._message.setPlainText(f"批量任务 {task_id} 完成：成功样本 {len(result.records)} 个{failure_text}{save_text}")

    def export_current_records(self) -> None:
        records = self._result_store.records
        if not records:
            self._message.setPlainText("没有可导出的结果，请先运行批量合成")
            return

        try:
            path = self._export_service.export_spectra(
                records,
                OutputConfig(
                    output_format=self._output_format.currentData(),
                    output_dir=self._output_dir.text().strip(),
                ),
            )
        except Exception as exc:  # noqa: BLE001
            self._message.setPlainText(f"导出失败：{exc}")
            return

        self._result_store.set_last_export_path(path)
        self._message.setPlainText(f"导出完成：{path}")

    def _build_batch_config(self) -> dict[str, object]:
        gas_name = self._variable_gas.text().strip()
        return {
            "base_config": SynthesisConfig(
                spectral_axis=SpectralAxisConfig(
                    WavenumberRange(self._nu_min.value(), self._nu_max.value()),
                    nu_step=self._nu_step.value(),
                ),
                environment=EnvironmentConfig(
                    pressure=self._pressure.value(),
                    temperature=self._temperature.value(),
                    path_length=self._path_length.value(),
                ),
                resident_gases=(
                    GasComponent(
                        name=self._resident_gas.text().strip(),
                        concentration=self._resident_concentration.value(),
                        role=GasRole.RESIDENT,
                    ),
                ),
                variable_gases=(
                    GasComponent(
                        name=gas_name,
                        concentration=self._variable_start.value(),
                        role=GasRole.VARIABLE,
                        presence=True,
                    ),
                ),
            ),
            "grid": {
                f"variable_gases.{gas_name}.concentration": _linear_values(
                    self._variable_start.value(),
                    self._variable_end.value(),
                    self._sample_count.value(),
                )
            },
        }

    def _fill_summary_table(self, records: Sequence[SpectrumRecord]) -> None:
        self._summary_table.setRowCount(len(records))
        for row, record in enumerate(records):
            resident_text = "; ".join(
                f"{name}={value:g}" for name, value in record.labels.resident_concentrations.items()
            )
            presence_text = "; ".join(f"{name}={value}" for name, value in record.labels.variable_presence.items())
            variable_text = "; ".join(
                f"{name}={value:g}" for name, value in record.labels.variable_concentrations.items()
            )
            values = [record.sample_id, len(record.wavenumber), resident_text, presence_text, variable_text]
            for column, value in enumerate(values):
                self._summary_table.setItem(row, column, QTableWidgetItem(str(value)))
        self._summary_table.resizeColumnsToContents()


class ResultsPage(QWidget):
    """Current-session result browser."""

    def __init__(
        self,
        result_store: ResultStore,
        result_repository: ResultRepositoryService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("resultsPage")
        self._result_store = result_store
        self._result_repository = result_repository
        self._datasets: tuple[SavedResultDataset, ...] = ()

        self._message = QLabel("", self)
        self._dataset_table = QTableWidget(0, 4, self)
        self._dataset_table.setHorizontalHeaderLabels(["结果集ID", "名称", "样本数", "创建时间"])
        self._dataset_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._dataset_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._summary_table = QTableWidget(0, 4, self)
        self._summary_table.setHorizontalHeaderLabels(["样本ID", "点数", "final min", "final max"])
        self._summary_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._summary_table.itemSelectionChanged.connect(self._show_selected_record)
        self._point_table = QTableWidget(0, 4, self)
        self._point_table.setHorizontalHeaderLabels(["波数", "clean", "final", "transmittance"])
        self._point_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        refresh_button = QPushButton("刷新结果", self)
        refresh_button.clicked.connect(self.refresh)
        load_button = QPushButton("加载选中历史结果", self)
        load_button.clicked.connect(self.load_selected_dataset)
        button_layout = QHBoxLayout()
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(load_button)
        button_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(button_layout)
        layout.addWidget(self._message)
        layout.addWidget(QLabel("持久化结果集", self))
        layout.addWidget(self._dataset_table)
        layout.addWidget(QLabel("当前会话样本", self))
        layout.addWidget(self._summary_table)
        layout.addWidget(QLabel("选中样本前 50 个点", self))
        layout.addWidget(self._point_table)
        self.refresh()

    def refresh(self) -> None:
        self._refresh_dataset_table()
        self._refresh_record_table()

    def load_selected_dataset(self) -> None:
        selected = self._dataset_table.selectionModel().selectedRows()
        if not selected:
            self._message.setText("请先选择一个持久化结果集")
            return
        row = selected[0].row()
        if row >= len(self._datasets):
            return
        dataset = self._datasets[row]
        try:
            records = tuple(self._result_repository.load_records(dataset.dataset_id))
        except Exception as exc:  # noqa: BLE001
            self._message.setText(f"加载结果集失败：{exc}")
            return
        self._result_store.set_records(records)
        self._refresh_record_table()
        self._message.setText(f"已加载结果集：{dataset.dataset_id}，样本数 {len(records)}")

    def _refresh_dataset_table(self) -> None:
        self._datasets = tuple(self._result_repository.list_datasets())
        self._dataset_table.setRowCount(len(self._datasets))
        for row, dataset in enumerate(self._datasets):
            values = [dataset.dataset_id, dataset.name, dataset.record_count, dataset.created_at]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, dataset.dataset_id)
                self._dataset_table.setItem(row, column, item)
        self._dataset_table.resizeColumnsToContents()

    def _refresh_record_table(self) -> None:
        records = self._result_store.records
        export_text = f"；最近导出：{self._result_store.last_export_path}" if self._result_store.last_export_path else ""
        self._message.setText(f"当前会话结果：{len(records)} 条{export_text}")
        self._summary_table.setRowCount(len(records))
        for row, record in enumerate(records):
            final_values = record.final_absorbance or record.clean_absorbance
            values = [
                record.sample_id,
                len(record.wavenumber),
                min(final_values) if final_values else "",
                max(final_values) if final_values else "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row)
                self._summary_table.setItem(row, column, item)
        self._summary_table.resizeColumnsToContents()
        self._point_table.setRowCount(0)

    def _show_selected_record(self) -> None:
        selected = self._summary_table.selectionModel().selectedRows()
        if not selected:
            return
        row = selected[0].row()
        records = self._result_store.records
        if row >= len(records):
            return
        record = records[row]
        max_rows = min(50, len(record.wavenumber))
        self._point_table.setRowCount(max_rows)
        for point_index in range(max_rows):
            final_values = record.final_absorbance or record.clean_absorbance
            values = (
                record.wavenumber[point_index],
                record.clean_absorbance[point_index],
                final_values[point_index],
                record.transmittance[point_index] if record.transmittance else "",
            )
            for column, value in enumerate(values):
                self._point_table.setItem(point_index, column, QTableWidgetItem(str(value)))
        self._point_table.resizeColumnsToContents()


class PlaceholderPage(QWidget):
    """Small placeholder for stages not yet wired into the GUI."""

    def __init__(self, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel(title, self)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label = QLabel(description, self)
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(description_label)


def _double_spin_box(
    minimum: float,
    maximum: float,
    value: float,
    decimals: int = 3,
) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(minimum, maximum)
    box.setDecimals(decimals)
    box.setValue(value)
    return box


def _linear_values(start: float, end: float, count: int) -> tuple[float, ...]:
    if count <= 1:
        return (start,)
    step = (end - start) / (count - 1)
    return tuple(start + step * index for index in range(count))
