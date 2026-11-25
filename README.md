# PromptPersona · 本地用户画像生成器

[![CI](https://github.com/luoyuda123/promptpersona/actions/workflows/ci.yml/badge.svg)](https://github.com/luoyuda123/promptpersona/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)

把「我想要一个懂我的 AI」变成一份可以直接粘贴的系统提示词。

12 道问卷 → 中文标签画像（`persona.json`）→ 中文系统提示词（`persona_system.txt`），
界面支持十种语言（含阿拉伯语 RTL），可以挂载多个 OpenAI 兼容模型，按轮询 / 并行对比 / 单模型优先三种策略执行。
**纯 Python 标准库 + Tkinter，不联网也能填问卷，双击即可运行。**

## 它解决什么问题

每次换 AI 工具都要重新解释一遍「我是谁、说话别绕弯、别提我的公司名」——很烦。
PromptPersona 把这件事做成一次性的：填一次问卷，得到一个固定的画像文件与一段系统提示词，粘到任何支持 System Prompt 的客户端里即可。

- **画像用中文标签做键**（`身份与背景`、`沟通风格`……），换界面语言不影响 Agent 读取
- **私密备注**单独存 `secret_note.json`，可以只留本地、选择是否注入提示词
- **多模型对照**：同一条提示词同时问几个模型，看谁更懂你
- **全部本地**：没有账号、没有云同步，API Key 只写在本机

## 快速开始

1. 安装 Python 3.9 或更高版本（Windows 安装时勾选 *Add python.exe to PATH*，Tkinter 随官方安装包自带）。
2. 双击 `启动.bat`；或在项目目录执行：

   ```bash
   py main.py        # Windows 启动器
   python3 main.py   # macOS / Linux
   ```

3. 首次启动会弹出语言选择，选完写入 `config.json`，下次直接进主界面。
4. 左侧逐题填写（可跳过任意维度），右侧挂载模型，点「生成画像」。
5. 结果窗口分两页：**系统提示词**（可一键复制）与**模型输出**（各模型对这条提示词的回应）。

想直接要一个 exe：双击 `打包exe.bat`，产物在 `dist\PromptPersona.exe`（单文件、免安装）。

## 界面语言

| 代码 | 语言 | 说明 |
| --- | --- | --- |
| `zh` | 简体中文 | 默认 |
| `zh-tw` | 繁體中文 | |
| `en` | English | |
| `ja` | 日本語 | |
| `ko` | 한국어 | |
| `fr` | Français | |
| `ru` | Русский | |
| `es` | Español | |
| `de` | Deutsch | |
| `ar` | العربية | 从右到左排版，面板左右镜像 |

十种语言的界面文案、12 道问题全部人工对齐；`tests` 里有一条测试专门校验「所有语言的键完全一致且非空」，缺翻译会直接失败。

## 接入模型

两种方式，都是 OpenAI 兼容协议（`POST {base_url}/chat/completions`）：

- **自动检索**：内置候选库按当前界面语言过滤（GPT-4o、DeepSeek、Qwen、Kimi、Gemini、OpenRouter、Groq、本地 Ollama），选中即挂载
- **手动添加**：名称 / Base URL / API Key / 模型 ID / 本地路径，Base URL 必须是 `http(s)://`

挂载后可以排序、启用停用、测连接、清空。本地模型示例：

```
Base URL : http://127.0.0.1:11434/v1
模型 ID  : qwen2.5:7b
API Key  : 留空
```

## 三种执行策略

| 策略 | 行为 | 适合 |
| --- | --- | --- |
| 轮询（poll） | 每次只问下一个模型，游标自动推进并记住 | 想轮流省钱 / 分摊额度 |
| 并行对比（parallel） | 同时问所有启用模型（最多 8 并发），结果并排看 | 挑模型、对比风格 |
| 单模型优先（primary） | 只问列表第一个启用模型 | 已经选定主力模型 |

网络请求全部在后台线程，界面不会卡；失败只会显示错误文本，不会弹异常。

## 生成的文件

| 文件 | 内容 | 是否可入库 |
| --- | --- | --- |
| `config.json` | 语言、策略、模型列表（含 API Key）、问卷答案 | 否，`.gitignore` 已排除 |
| `persona.json` | 中文标签画像 | 否，个人数据 |
| `secret_note.json` | 私密备注与是否注入 | 否 |
| `persona_system.txt` | 最终系统提示词 | 否 |

源码运行时文件写在项目根目录；打包成 exe 后写在 exe 同目录（`storage.app_dir()` 负责区分）。
JSON 写入是「临时文件 + `os.replace`」，中途断电不会写坏原文件。

## 项目结构

```
.
├── main.py                  # 入口：DPI 感知、启动、异常兜底
├── app/
│   ├── ui.py                # Tkinter 主界面、结果窗口、RTL 处理
│   ├── i18n.py              # 十语言文案、12 维问题与中文标签
│   ├── models.py            # 候选库、校验、去重、排序
│   ├── persona.py           # 画像与系统提示词构建
│   ├── providers.py         # OpenAI 兼容调用与三种策略
│   └── storage.py           # 原子读写与默认值合并
├── tests/test_core.py       # 30 项单元测试（含本地假服务器）
├── 启动.bat / 运行测试.bat / 打包exe.bat
├── 项目方案.txt / 第一代.txt  # 设计文档（第一代实现要点）
└── .github/workflows/       # CI + 打 tag 构建 exe
```

## 开发与测试

```bash
py -m compileall -q app main.py tests
py -m unittest discover -s tests -v
```

Windows 上也可以双击 `运行测试.bat`。测试不依赖显示器，覆盖：

- 十语言键一致性、占位符渲染、RTL 判定
- 画像只保留非空维度、中文标签、备注注入开关
- 模型候选过滤、字段校验、去重、排序
- 配置文件默认合并、坏 JSON 兜底、原子写入
- 本地 HTTP 假服务器模拟 OpenAI 响应：成功、HTTP 错误、非 JSON 响应
- 轮询游标推进、并行结果合并、单模型优先

### 新增一种界面语言

1. 在 `app/i18n.py` 的 `LANGS` 加一项（`code` / `label` / `rtl`）；
2. 在 `STRINGS` 补同键文案（必须覆盖全部键，`q1..q12` 也要）；
3. 跑一次测试，键不一致会立刻报错。

### 新增内置候选模型

在 `app/models.py` 的 `CATALOG` 加一条：`name` / `base_url` / `model` / `langs`（`all` 表示所有语言可见）。

## 打包 exe

```bash
py -m pip install pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed --name PromptPersona main.py
```

或者直接双击 `打包exe.bat`（会自动检查并安装 PyInstaller）。
`--onefile` 首次启动要解压，慢一两秒属正常；杀软误报可以改用 `--onedir`。

推 `v*` 标签时，`.github/workflows/build-exe.yml` 会在 Windows runner 上构建 exe 并作为 artifact 上传。

## 隐私

- 问卷答案、备注、API Key 全部只存在本机文件里，代码不包含任何上报逻辑
- 只有点击「测试连接 / 生成画像」并挂载了模型时才会发起网络请求，目标就是你自己填的 Base URL
- 分享仓库前确认 `config.json`、`persona*.json`、`secret_note.json` 没有被提交（`.gitignore` 已默认排除）

## 常见问题

**双击没反应？** 看项目目录下的 `startup-error.log`，里面是完整堆栈。

**提示找不到 `py`？** 没装 Python 或没加 PATH；装完重开命令行。也可以把 `启动.bat` 里的 `py` 换成 `python`。

**模型测连接失败？** 先确认 Base URL 带 `/v1`（如 `https://api.deepseek.com/v1`），再确认 Key 有额度；本地模型要先启动 Ollama。

**换语言后界面没变？** 语言切换会重建界面并保留已填答案；如果异常，删掉 `config.json` 重开即可。

## 许可证

[MIT](LICENSE)
