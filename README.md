# 吸收光谱数据模拟软件

本项目用于开发桌面级吸收光谱数据模拟软件。软件面向开放光路宽光谱多组分识别算法研究，核心能力包括：

- 通过 HAPI 从 HITRAN 下载指定气体、指定波数范围的 line-by-line 谱线数据。
- 将谱线数据写入本地气体谱线数据库，支持后续扩展下载。
- 基于本地已下载谱线数据进行波数域吸收光谱合成。
- 支持 H2O/CO2 常驻背景组分与三类变量组分的批量合成。
- 输出吸光度谱、浓度标签、存在性标签、噪声和基线分量。

## 当前开发阶段

当前已完成 `P0 工程骨架`、`P1 数据模型与接口`、`P2 本地谱线数据库`、`P3 HAPI 下载`、`P4 单气体合成`、`P5 混合气体与扰动模型` 和 `P6 基础批量合成与导出`，已包含：

- Python 工程结构。
- PySide6 桌面 GUI 空主窗口。
- 基础日志配置。
- 核心数据模型。
- 统一异常类型。
- 服务层接口协议。
- 基础参数校验。
- SQLite 本地谱线数据库 schema。
- 覆盖范围合并与缺失区间检测。
- 本地谱线 Repository。
- 本地数据库服务适配器。
- HAPI 下载适配器。
- HAPI 谱线字段到内部 `LineRecord` 的转换。
- 下载任务记录、状态更新和失败回写。
- 下载服务与本地数据库写入流程。
- 波数网格生成。
- Lorentz/Gaussian/pseudo-Voigt 线型函数。
- 单气体 line-by-line 吸收系数计算。
- Beer-Lambert clean absorbance/transmittance 输出。
- 单气体合成服务封装。
- 混合气体 clean absorbance 叠加合成。
- 常驻组分浓度标签、变量组分存在性标签和浓度标签。
- Gaussian/Uniform/Relative/Spike 噪声模型。
- Constant/Linear/Polynomial/Sine/Random smooth 基线模型。
- baseline/noise/final absorbance 分量输出。
- 混合气体合成服务封装。
- 路径式参数网格展开。
- 内存串行批量合成服务。
- 批量样本失败记录。
- CSV 长表导出、标签导出和元数据导出。
- NPZ 压缩数组数据集导出。
- 最小测试入口。

当前阶段不包含后台任务队列、HDF5/Parquet 导出和完整 GUI 接入逻辑。

## 开发运行

当前推荐使用的 Python 解释器：

```powershell
C:\Pythons\python-3.12.10\python.exe
```

安装依赖：

```powershell
& "C:\Pythons\python-3.12.10\python.exe" -m pip install -e .[dev]
```

安装依赖后可启动桌面 GUI：

```powershell
$env:PYTHONPATH="src"
& "C:\Pythons\python-3.12.10\python.exe" -m spectra_sim.app.main
```

运行测试：

```powershell
$env:PYTHONPATH="src"
& "C:\Pythons\python-3.12.10\python.exe" -m unittest discover -s tests
```
