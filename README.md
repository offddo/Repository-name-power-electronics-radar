# Power Electronics Radar

> 自动追踪电力电子领域高相关技术动态的技术雷达。
>
> **在线阅读：** https://offddo.github.io/Repository-name-power-electronics-radar/

## 项目简介

Power Electronics Radar 用自动化流程持续收集、筛选、聚类和分析电力电子领域的新内容，重点不是泛能源新闻，而是与电力电子工程直接相关的技术信息。

核心方向包括：

- SST（固态变压器）
- SiC / GaN 宽禁带半导体
- GFM（构网型变流器）
- PCS / 储能变流器
- DAB / CLLC / LLC 等高频隔离型拓扑
- 800 V 电力电子系统
- AI 数据中心电源
- 高频磁性器件与磁集成
- 电源系统及产业化进展

## 国内内容

现在雷达不再只追踪国际资讯，同时增加国内高相关来源，并单独分类：

### 国内资讯

重点跟踪中国电力电子产业和企业技术动态，例如：

- 阳光电源
- 华为数字能源
- 中车时代电气
- 上能电气
- 科华数据
- 中国电力电子产业相关技术资讯

### 国内论文

重点跟踪国内电力电子及新型电力系统相关期刊/论文来源，包括：

- 《电力电子技术》
- 《电力自动化设备》
- 《电力系统自动化》
- 《电工技术学报》
- 《中国电机工程学报》
- CNKI 中与核心方向直接相关的论文

例如近期国内期刊已经出现 DAB 效率优化、CLLLC 分段调制、SiC 电力电子变压器、GFM 稳定性、变流器开源电磁暂态模型等高度相关研究。citeturn0search1turn1search9turn2search2

## 相关性筛选

项目不再把事件数量固定为 15 条。

当前每次运行会扩大候选池，再进行主题匹配、事件聚类和来源优先级处理，最终最多保留 **40 个高相关事件**用于 AI 结构化分析。重点优先考虑：

`SST / SiC / GaN / GFM / PCS / DAB / CLLC / LLC / 800V / AI Data Center / Magnetics`

因此宁可当天只有较少的高相关结果，也不为了凑数量加入大量泛能源、财经或低相关新闻。

## 自动更新

项目通过 GitHub Actions 自动运行：

**每天 08:00（北京时间）自动更新一次。**

同时支持手动触发 GitHub Actions；修改 `scripts/radar.py` 或 `.github/workflows/radar.yml` 时也会自动触发更新。

更新流程：

```text
国内论文 / 国内资讯 / 国际资讯
              ↓
          RSS 内容抓取
              ↓
        主题相关性筛选
              ↓
           事件聚类
              ↓
        Google News 原文解析
              ↓
       DeepSeek 技术结构化
              ↓
        内容清理与真实性验证
              ↓
            data.json
              ↓
         Google 风格网页
```

## AI 分析格式

每条事件分为两个层次：

### 通俗版

面向普通读者，用简洁语言说明发生了什么、为什么值得关注。

### 技术版

面向电力电子工程师，只提取原文明确出现的技术信息，例如：

- 器件：SiC、GaN、IGBT 等
- 拓扑：DAB、CLLC、LLC、三电平等
- 电压 / 功率等级
- 开关频率
- 效率 / 功率密度
- 控制方法
- 隔离方式
- 应用场景
- 实验结果与工程指标

**通俗版和技术版不会简单重复。**

## 信息真实性原则

- 原文没有提供的数据，不自行补充。
- 无法确认的技术参数不作为事实写入。
- 无法定位到具体原始来源时，不伪造原文链接。
- 企业宣传、预测和观点与已验证事实区分处理。
- 自动清理“原文未提供”“未知”等占位内容。

## 网页布局

网页采用接近 Google 搜索结果的阅读方式：

- 顶部搜索框，可直接搜索 SiC、GaN、GFM、DAB、CLLC 等关键词。
- 国内资讯 / 国内论文 / 国际资讯分类标签。
- 主区域按搜索结果形式展示标题、来源、链接、摘要和技术版。
- 右侧展示技术方向和数据规则。
- 不再把所有信息堆成大卡片，方便在平板和手机上快速浏览大量结果。

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
├── index.html              # GitHub Pages 前端
└── README.md
```

## 手动运行

可以在 GitHub Actions 页面手动运行 `Power Electronics Radar` workflow。

在线结果：

https://offddo.github.io/Repository-name-power-electronics-radar/

Actions：

https://github.com/offddo/Repository-name-power-electronics-radar/actions

## License

本项目的代码和数据处理流程用于个人技术学习与研究。原始文章、论文、图片、商标及其他内容的版权归其原作者或权利人所有。
