# 参与贡献

这个项目的目标是「保持简单」：只用 Python 标准库，不引入运行时第三方依赖，不做构建步骤。提交前请确认没有破坏这三条。

## 本地检查

```bash
py -m compileall -q app main.py tests   # 语法检查
py -m unittest discover -s tests -v     # 30 项单元测试必须全绿
```

Windows 上可直接双击 `运行测试.bat`。

## 代码约定

- `app/storage.py` 负责一切落盘：JSON 用「临时文件 + `os.replace`」原子写入，读不到就给默认值，不要在各处自己 `open()`
- `app/i18n.py` 是唯一文案来源：新增键必须十种语言同时补齐（`tests` 会校验键完全一致），界面里不许出现硬编码中文
- `app/providers.py` 的公共函数只返回 `{ok, text}` / `{ok: False, error}`，不允许把异常抛给界面
- 涉及 Tkinter 的改动注意两点：`ttk` 样式的 `font` 必须是字符串（字体名带空格要加花括号），`tk.Text` 没有 `justify` 选项（用 tag 设置对齐）
- RTL（阿拉伯语）需要检查：面板顺序、按钮左右、文本对齐、Treeview 列顺序
- 修改核心逻辑必须补 `tests/test_core.py` 的断言；涉及网络的用例请用本地假服务器，不要真的请求外网
- 文本文件统一 UTF-8；`.bat` 保持 CRLF（`.gitattributes` 已处理）

## 提交信息

使用 `type: 描述` 格式：

- `feat: 新增 XX 语言`
- `fix: 修复阿拉伯语下 Treeview 列顺序错误`
- `docs: 补充打包说明`
- `test: 补齐非 JSON 响应用例`
- `chore: 调整忽略规则`

## 提 issue

请附上：Python 版本、操作系统、复现步骤、期望结果、实际结果；界面问题请附 `startup-error.log` 里的堆栈（记得先删掉 API Key 等隐私内容）。
