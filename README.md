# Power Electronics Radar

> 自动追踪电力电子领域技术动态的技术雷达。
>
> **在线阅读：** https://offddo.github.io/Repository-name-power-electronics-radar/

## 项目简介

Power Electronics Radar 用自动化流程持续收集、筛选和分析电力电子领域的新内容，重点关注：

- SST（固态变压器）
- SiC / GaN 宽禁带半导体
- GFM（构网型变流器）
- PCS / 储能变流器
- DAB / CLLC / LLC 等高频隔离型拓扑
- 800 V 电力电子系统
- AI 数据中心电源
- 高频磁性器件与磁集成
- 电源系统及相关产业化进展

## 自动更新

项目通过 GitHub Actions 自动运行：

**每天 08:00（北京时间）自动更新一次。**

同时支持手动触发 GitHub Actions；修改 `scripts/radar.py` 或 `.github/workflows/radar.yml` 时也会自动触发更新。

更新流程：

```text
RSS / 新闻源
    ↓
内容抓取
    ↓
主题筛选
    ↓
事件聚类
    ↓
原始来源解析
    ↓
DeepSeek 技术分析
    ↓
内容清理与验证
    ↓
data.json
    ↓
GitHub Pages
```

## AI 分析格式

每条事件的 AI 分析分为两个层次：

### 通俗版

面向普通读者，用简洁语言说明：

- 发生了什么
- 这件事为什么值得关注
- 对电力电子行业可能意味着什么

### 技术版

面向电力电子工程师，重点提取原文中实际出现的技术信息，例如：

- 器件：SiC、GaN、IGBT 等
- 拓扑：DAB、CLLC、LLC、三电平等
- 电压 / 功率等级
- 开关频率
- 效率 / 功率密度
- 控制方法
- 隔离方式
- 应用场景
- 测试结果与工程指标

**通俗版和技术版不会简单重复。**

## 信息真实性原则

项目只发布能够从实际来源中得到支持的信息：

- 原文没有提供的数据，不自行补充。
- 无法确认的技术参数不作为事实写入。
- 无法定位到具体原始来源时，不伪造原文链接。
- 对来源中的企业宣传、预测或观点，与已验证事实区分处理。
- 自动清理没有可靠依据的占位内容，避免把“原文未提供”“未知”等提示直接展示给用户。

因此，某些事件可能只有通俗版或基础信息，而不会强行填充完整的技术参数。

## 数据文件

主要输出文件：

```text
data.json
```

网页端读取 `data.json` 并展示最新雷达结果。

## 项目结构

```text
.
├── .github/
│   └── workflows/
│       └── radar.yml       # GitHub Actions 自动更新任务
├── scripts/
│   └── radar.py            # 雷达核心程序
├── data.json               # 最新雷达数据
└── README.md
```

## 手动运行

可以在 GitHub Actions 页面手动运行 `Power Electronics Radar` workflow。

在线结果：

https://offddo.github.io/Repository-name-power-electronics-radar/

Actions：

https://github.com/offddo/Repository-name-power-electronics-radar/actions

## 适用场景

这个项目主要用于快速了解电力电子领域的技术动态，减少每天手动浏览大量新闻、论文资讯和企业技术消息的时间。

尤其适合关注以下方向的工程师：

- 电力电子
- 新能源
- 储能
- 光伏 / 风电
- 数据中心电源
- 宽禁带半导体
- 高频磁集成
- 电能变换与电源系统

## License

本项目的代码和数据处理流程用于个人技术学习与研究。原始文章、图片、商标及其他内容的版权归其原作者或权利人所有。
