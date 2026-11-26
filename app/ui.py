"""PromptPersona 图形界面（Tkinter）。

结构：
- 顶部：标题、当前界面语言、切换语言、关于
- 左侧：12 维问卷（上一题 / 下一题）
- 右侧：多模型挂载（自动检索、手动添加、列表操作、运行策略）
- 底部：私密备注与生成按钮
- 结果窗口：系统提示词 + 多模型输出（独立标签页）

所有网络请求都在后台线程执行，界面不会被卡住。
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, ttk

from . import i18n, models, persona, providers, storage

FONT_BY_LANG = {
    "zh": "Microsoft YaHei UI",
    "zh-tw": "Microsoft JhengHei UI",
    "ja": "Yu Gothic UI",
    "ko": "Malgun Gothic",
    "ar": "Segoe UI",
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_data = storage.load_config()
        self.lang = str(self.config_data.get("lang") or "")

        self.entries = []
        for item in self.config_data.get("models", []):
            if isinstance(item, dict):
                self.entries.append(models.new_entry(**item))

        self.strategy = self.config_data.get("strategy", "primary")
        self.rotate_index = int(self.config_data.get("rotate_index") or 0)
        self.note = str(self.config_data.get("note") or "")
        self.include_note = bool(self.config_data.get("include_note", True))

        answers = self.config_data.get("answers") or {}
        self.answers = {key: str(answers.get(key, "") or "") for key in i18n.DIM_KEYS}

        self.q_index = 0
        self.built = False
        self.candidates = []
        self.prompt_text = ""
        self.status_var = tk.StringVar(value="")

        self.title("PromptPersona")
        self.geometry("1160x780")
        self.minsize(1000, 700)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._setup_style()

        if self.lang:
            self.build_ui()
        else:
            self.withdraw()
            self.after(150, lambda: self.ask_language(first_run=True))

    # ------------------------------------------------------------------ 基础

    def _font_spec(self, size, bold=False):
        """返回 tkinter 字体元组：含空格的字体名作为整体元素，不会被 Tcl 按空格拆开。"""
        family = FONT_BY_LANG.get(self.lang, "Segoe UI")
        return (family, size, "bold") if bold else (family, size)

    def _setup_style(self):
        try:
            ttk.Style(self).theme_use("clam")
        except tk.TkError:
            pass
        style = ttk.Style(self)
        style.configure("TFrame", background="#ffffff")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("TLabel", background="#ffffff", foreground="#1f2430")
        style.configure("Muted.TLabel", foreground="#6b7280")
        style.configure("Title.TLabel", font=self._font_spec(16, bold=True))
        style.configure("Section.TLabel", font=self._font_spec(12, bold=True))
        style.configure("Accent.TButton", font=self._font_spec(10, bold=True))
        style.configure("Q.TLabel", foreground="#111827", font=self._font_spec(12))
        style.configure("Treeview", rowheight=26)
        style.configure("Treeview.Heading", font=self._font_spec(10, bold=True))
        self.configure(background="#f3f5f9")
        self.option_add("*Font", self._font_spec(10))

    def _font_tuple(self, size):
        family = FONT_BY_LANG.get(self.lang, "Segoe UI")
        return (family, size)

    def _apply_fonts(self):
        family = FONT_BY_LANG.get(self.lang, "Segoe UI")
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(name).configure(family=family, size=10)
            except tk.TkError:
                pass
        try:
            tkfont.nametofont("TkDefaultFont").configure(family=family)
        except tk.TkError:
            pass

    def rtl(self) -> bool:
        return i18n.is_rtl(self.lang)

    def tr(self, key, **kwargs):
        return i18n.t(self.lang, key, **kwargs)

    def justify(self):
        return tk.RIGHT if self.rtl() else tk.LEFT

    def justify_text(self):
        """tk.Text 没有 justify 选项，只能通过 tag 设置对齐方式。"""
        return "right" if self.rtl() else "left"

    def prep_text(self, widget):
        widget.tag_configure("body", justify=self.justify_text())
        widget.bind(
            "<KeyRelease>",
            lambda event, w=widget: w.tag_add("body", "1.0", "end-1c"),
            add="+",
        )

    def anchor(self):
        return "e" if self.rtl() else "w"

    # ------------------------------------------------------------------ 界面

    def build_ui(self):
        self.built = True
        self._setup_style()
        self._apply_fonts()
        for child in self.winfo_children():
            child.destroy()

        header = ttk.Frame(self, padding=(20, 14, 20, 10))
        header.pack(fill="x")
        self._build_header(header)

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        left = ttk.Frame(body, padding=8)
        right = ttk.Frame(body, padding=8)
        if self.rtl():
            # 阿拉伯语从右往左读，问卷放右侧、模型放左侧
            body.add(right, weight=4)
            body.add(left, weight=3)
        else:
            body.add(left, weight=3)
            body.add(right, weight=4)

        self._build_profile(left)
        self._build_models(right)

        footer = ttk.Frame(self, padding=(16, 0, 16, 14))
        footer.pack(fill="x")
        self._build_footer(footer)

        self._refresh_models()
        self._load_question()
        self.status_var.set(self.tr("ready"))
        self._update_count()

    def _build_header(self, parent):
        pack_brand = {"side": "right"} if self.rtl() else {"side": "left"}
        pack_actions = {"side": "left"} if self.rtl() else {"side": "right"}

        brand = ttk.Frame(parent)
        brand.pack(anchor="e" if self.rtl() else "w", **pack_brand)
        ttk.Label(brand, text=self.tr("app_title"), style="Title.TLabel").pack(anchor=self.anchor())
        ttk.Label(brand, text=self.tr("app_sub"), style="Muted.TLabel").pack(anchor=self.anchor())

        actions = ttk.Frame(parent)
        actions.pack(anchor="e" if not self.rtl() else "w", **pack_actions)
        button = ttk.Button(actions, text=self.tr("lang_switch") + "：" + i18n.lang_label(self.lang), command=self.ask_language)
        button.pack(side="right" if not self.rtl() else "left", padx=4)
        ttk.Button(actions, text=self.tr("about"), command=self.show_about).pack(
            side="right" if not self.rtl() else "left", padx=4
        )

    def _build_profile(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(3, weight=1)

        title = ttk.Frame(parent)
        title.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        title.columnconfigure(0, weight=1)
        ttk.Label(title, text=self.tr("profile"), style="Section.TLabel").grid(row=0, column=0, sticky=self.anchor())
        self.progress_label = ttk.Label(title, text="", style="Muted.TLabel")
        self.progress_label.grid(row=0, column=1, sticky="e")

        self.question_label = ttk.Label(parent, text="", style="Q.TLabel", wraplength=420, justify=self.justify())
        self.question_label.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        parent.bind(
            "<Configure>",
            lambda event: self.question_label.configure(wraplength=max(240, event.width - 8)),
        )

        self.answer_text = tk.Text(
            parent, height=9, wrap="word", relief="solid", borderwidth=1,
            highlightthickness=1, highlightbackground="#d8dde8", highlightcolor="#2f6feb",
            font=self._font_tuple(11), undo=True,
        )
        self.prep_text(self.answer_text)
        self.answer_text.grid(row=3, column=0, sticky="nsew")

        nav = ttk.Frame(parent)
        nav.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        nav.columnconfigure(1, weight=1)
        self.prev_btn = ttk.Button(nav, text=self.tr("prev"), command=lambda: self.step_question(-1))
        self.prev_btn.grid(row=0, column=0, sticky="w")
        ttk.Label(nav, text=self.tr("answer_hint"), style="Muted.TLabel", wraplength=220, justify=self.justify()).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        self.next_btn = ttk.Button(nav, text=self.tr("next"), command=lambda: self.step_question(1))
        self.next_btn.grid(row=0, column=2, sticky="e")

    def _build_models(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        head = ttk.Frame(parent)
        head.grid(row=0, column=0, sticky="ew")
        head.columnconfigure(0, weight=1)
        ttk.Label(head, text=self.tr("models"), style="Section.TLabel").grid(row=0, column=0, sticky=self.anchor())
        self.count_label = ttk.Label(head, text="", style="Muted.TLabel")
        self.count_label.grid(row=0, column=1, sticky="e")

        self.strategy_var = tk.StringVar(value=self.strategy)
        strategy_frame = ttk.Frame(parent)
        strategy_frame.grid(row=1, column=0, sticky="ew", pady=(6, 6))
        ttk.Label(strategy_frame, text=self.tr("strategy") + "：", style="Muted.TLabel").pack(
            side="right" if self.rtl() else "left"
        )
        for value, key in (("poll", "s_poll"), ("parallel", "s_parallel"), ("primary", "s_primary")):
            ttk.Radiobutton(
                strategy_frame, text=self.tr(key), value=value, variable=self.strategy_var,
                command=self._on_strategy_change,
            ).pack(side="right" if self.rtl() else "left", padx=(0, 10))

        tree_frame = ttk.Frame(parent)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("state", "name", "model", "kind")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8, selectmode="browse")
        headings = {
            "state": (self.tr("c_state"), 50),
            "name": (self.tr("c_name"), 132),
            "model": (self.tr("c_model"), 132),
            "kind": (self.tr("c_kind"), 56),
        }
        for column, (text, width) in headings.items():
            self.tree.heading(column, text=text, anchor=self.anchor())
            self.tree.column(column, width=width, minwidth=48, anchor=self.anchor(), stretch=True)
        if self.rtl():
            self.tree.configure(displaycolumns=("kind", "model", "name", "state"))
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 自动检索
        search_row = ttk.Frame(parent)
        search_row.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        search_row.columnconfigure(1, weight=1)
        ttk.Button(search_row, text=self.tr("auto_search"), command=self.auto_search).grid(row=0, column=0, sticky="w")
        self.candidate_combo = ttk.Combobox(search_row, state="readonly", values=[])
        self.candidate_combo.grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(search_row, text=self.tr("add_candidate"), command=self.add_candidate).grid(row=0, column=2, sticky="e")

        # 列表操作（两行四列，避免按钮被窗口宽度挤掉）
        ops = ttk.Frame(parent)
        ops.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        actions = (
            ("add_manual", self.open_manual_dialog),
            ("delete", self.delete_model),
            ("up", lambda: self.move_model(-1)),
            ("down", lambda: self.move_model(1)),
            ("toggle", self.toggle_model),
            ("test", self.test_model),
            ("clear_all", self.clear_models),
        )
        columns = 4
        for index, (key, command) in enumerate(actions):
            column = columns - 1 - index % columns if self.rtl() else index % columns
            ttk.Button(ops, text=self.tr(key), command=command).grid(
                row=index // columns, column=column, sticky="ew", padx=2, pady=2
            )
        for column in range(columns):
            ops.columnconfigure(column, weight=1, uniform="ops")

    def _build_footer(self, parent):
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(0, 10))

        note_head = ttk.Frame(parent)
        note_head.pack(fill="x")
        ttk.Label(note_head, text=self.tr("note"), style="Section.TLabel").pack(
            side="right" if self.rtl() else "left"
        )
        ttk.Label(note_head, text=self.tr("note_hint"), style="Muted.TLabel").pack(
            side="right" if self.rtl() else "left", padx=10
        )

        self.include_var = tk.BooleanVar(value=self.include_note)
        ttk.Checkbutton(note_head, text=self.tr("inject"), variable=self.include_var).pack(
            side="left" if self.rtl() else "right"
        )

        self.note_text = tk.Text(
            parent, height=3, wrap="word", relief="solid", borderwidth=1,
            highlightthickness=1, highlightbackground="#d8dde8", highlightcolor="#2f6feb",
            font=self._font_tuple(10),
        )
        self.prep_text(self.note_text)
        self.note_text.pack(fill="x", pady=(6, 10))
        self.note_text.insert("1.0", self.note, "body")

        actions = ttk.Frame(parent)
        actions.pack(fill="x")
        self.status_label = ttk.Label(actions, textvariable=self.status_var, style="Muted.TLabel")
        self.status_label.pack(side="right" if not self.rtl() else "left")

        ttk.Button(actions, text=self.tr("open_dir"), command=self.open_folder).pack(
            side="left" if not self.rtl() else "right", padx=(0, 6)
        )
        ttk.Button(actions, text=self.tr("copy_prompt"), command=self.copy_last_prompt).pack(
            side="left" if not self.rtl() else "right", padx=(0, 6)
        )
        self.generate_btn = ttk.Button(actions, text=self.tr("generate"), style="Accent.TButton", command=self.generate)
        self.generate_btn.pack(side="left" if not self.rtl() else "right")

    # ------------------------------------------------------------------ 语言

    def ask_language(self, first_run=False):
        top = tk.Toplevel(self)
        top.title(self.tr("lang_title"))
        # 首次启动时主窗口是 withdraw 的，transient 会让子窗口一起隐藏，所以只在之后再绑定
        if not first_run:
            top.transient(self)
        top.resizable(False, False)
        top.grab_set()

        frame = ttk.Frame(top, padding=22)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=self.tr("lang_title"), style="Title.TLabel").pack(anchor=self.anchor())
        ttk.Label(frame, text=self.tr("lang_hint"), style="Muted.TLabel", wraplength=520, justify=self.justify()).pack(
            anchor=self.anchor(), pady=(6, 14)
        )

        grid = ttk.Frame(frame)
        grid.pack(fill="x")
        buttons = []
        for index, item in enumerate(i18n.LANGS):
            button = ttk.Button(grid, text=item["label"], width=18, command=lambda code=item["code"]: choose(code))
            button.grid(row=index // 5, column=index % 5, padx=4, pady=4, sticky="ew")
            buttons.append(button)
        for column in range(5):
            grid.columnconfigure(column, weight=1)

        def choose(code):
            self.lang = code
            self.config_data["lang"] = code
            storage.save_config(self.config_data)
            top.destroy()
            if first_run and not self.built:
                self.deiconify()
                self.build_ui()
            else:
                self.rebuild_ui()
            if i18n.is_rtl(code):
                self.after(200, self.show_rtl_hint)

        top.protocol("WM_DELETE_WINDOW", lambda: (top.destroy(), self._on_language_cancel(first_run)))
        top.update_idletasks()
        try:
            x = self.winfo_screenwidth() // 2 - top.winfo_width() // 2
            y = self.winfo_screenheight() // 3 - top.winfo_height() // 2
            top.geometry("+%d+%d" % (x, y))
        except tk.TkError:
            pass
        top.deiconify()
        top.lift()
        if first_run:
            top.wait_window()

    def _on_language_cancel(self, first_run):
        if first_run and not self.built:
            self.lang = self.config_data.get("lang") or "zh"
            self.deiconify()
            self.build_ui()

    def show_rtl_hint(self):
        messagebox.showinfo(self.tr("rtl_title"), self.tr("rtl_body"))

    def rebuild_ui(self):
        self._sync_answer()
        self.note = self.note_text.get("1.0", "end").strip()
        self.include_note = bool(self.include_var.get())
        self.build_ui()

    def show_about(self):
        messagebox.showinfo(self.tr("about"), self.tr("about_body"))

    # ------------------------------------------------------------------ 问卷

    def _load_question(self):
        key = i18n.DIM_KEYS[self.q_index]
        self.question_label.configure(text=i18n.question(self.lang, key))
        self.progress_label.configure(text=self.tr("progress", n=self.q_index + 1, total=len(i18n.DIM_KEYS)))
        self.answer_text.delete("1.0", "end")
        self.answer_text.insert("1.0", self.answers.get(key, ""), "body")
        self.prev_btn.configure(state="normal" if self.q_index > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.q_index < len(i18n.DIM_KEYS) - 1 else "disabled")

    def _sync_answer(self):
        if not self.built:
            return
        key = i18n.DIM_KEYS[self.q_index]
        self.answers[key] = self.answer_text.get("1.0", "end").strip()

    def step_question(self, delta):
        self._sync_answer()
        target = self.q_index + delta
        if 0 <= target < len(i18n.DIM_KEYS):
            self.q_index = target
            self._load_question()

    # ------------------------------------------------------------------ 模型

    def _refresh_models(self):
        if not self.built:
            return
        self.tree.delete(*self.tree.get_children())
        for entry in self.entries:
            self.tree.insert(
                "", "end", iid=entry["id"],
                values=(
                    self.tr("enabled") if entry.get("enabled") else self.tr("disabled"),
                    entry.get("name", ""),
                    entry.get("model", ""),
                    self.tr("src_auto") if entry.get("source") == models.SOURCE_AUTO else self.tr("src_manual"),
                ),
            )
        self._update_count()

    def _update_count(self):
        if self.built:
            self.count_label.configure(text=self.tr("count", n=len(self.entries)))

    def selected_entry(self):
        selection = self.tree.selection()
        if not selection:
            return None
        target = selection[0]
        for entry in self.entries:
            if entry["id"] == target:
                return entry
        return None

    def _on_strategy_change(self):
        self.strategy = self.strategy_var.get()
        self.config_data["strategy"] = self.strategy

    def auto_search(self):
        self.candidates = models.catalog_for(self.lang)
        if not self.candidates:
            self.candidate_combo.configure(values=[])
            self.candidate_combo.set("")
            self.status_var.set(self.tr("no_candidates"))
            return
        names = [item["name"] for item in self.candidates]
        self.candidate_combo.configure(values=names)
        self.candidate_combo.set(names[0])
        self.status_var.set(self.tr("auto_search") + "：" + self.tr("count", n=len(names)))

    def add_candidate(self):
        name = self.candidate_combo.get()
        if not name:
            self.status_var.set(self.tr("no_candidates"))
            return
        data = next((item for item in self.candidates if item["name"] == name), None)
        if not data:
            return
        entry = models.new_entry(
            name=data["name"],
            base_url=data["base_url"],
            model=data["model"],
            source=models.SOURCE_AUTO,
            langs=data.get("langs", []),
            enabled=True,
        )
        self._add_entry(entry)

    def _add_entry(self, entry):
        if models.is_duplicate(self.entries, entry):
            messagebox.showwarning(self.tr("models"), self.tr("duplicate"))
            return
        self.entries.append(entry)
        self._refresh_models()
        self.status_var.set(self.tr("added", name=entry["name"]))

    def open_manual_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title(self.tr("manual_title"))
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=self.tr("manual_title"), style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky=self.anchor(), pady=(0, 10)
        )

        fields = {}
        labels = (("f_name", "name"), ("f_base", "base_url"), ("f_key", "api_key"), ("f_model", "model"), ("f_local", "local_path"))
        for row, (label_key, field) in enumerate(labels, start=1):
            ttk.Label(frame, text=self.tr(label_key)).grid(row=row, column=0, sticky=self.anchor(), pady=4, padx=(0, 8))
            widget = ttk.Entry(frame, width=44)
            widget.grid(row=row, column=1, sticky="ew", pady=4)
            fields[field] = widget

        hint = ttk.Label(frame, text=self.tr("local_only_hint"), style="Muted.TLabel", wraplength=380, justify=self.justify())
        hint.grid(row=len(labels) + 1, column=0, columnspan=2, sticky=self.anchor(), pady=(8, 4))

        def save():
            entry = models.new_entry(
                name=fields["name"].get().strip(),
                base_url=fields["base_url"].get().strip(),
                api_key=fields["api_key"].get().strip(),
                model=fields["model"].get().strip(),
                local_path=fields["local_path"].get().strip(),
                source=models.SOURCE_MANUAL,
                enabled=True,
            )
            ok, reason = models.validate(entry)
            if not ok:
                messages = {
                    "name_required": self.tr("f_name"),
                    "model_required": self.tr("f_model"),
                    "base_required": self.tr("f_base"),
                    "base_invalid": self.tr("base_invalid"),
                }
                if reason in ("name_required", "model_required", "base_required"):
                    text = messages[reason] + " " + self.tr("required")
                else:
                    text = messages.get(reason, reason)
                messagebox.showwarning(self.tr("err"), text)
                return
            self._add_entry(entry)
            dialog.destroy()

        actions = ttk.Frame(frame)
        actions.grid(row=len(labels) + 2, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(actions, text=self.tr("cancel"), command=dialog.destroy).pack(side="right", padx=4)
        ttk.Button(actions, text=self.tr("save"), command=save).pack(side="right", padx=4)

    def delete_model(self):
        entry = self.selected_entry()
        if not entry:
            self.status_var.set(self.tr("need_select"))
            return
        self.entries = [item for item in self.entries if item["id"] != entry["id"]]
        self._refresh_models()
        self.status_var.set(self.tr("deleted"))

    def move_model(self, delta):
        entry = self.selected_entry()
        if not entry:
            self.status_var.set(self.tr("need_select"))
            return
        index = next(i for i, item in enumerate(self.entries) if item["id"] == entry["id"])
        models.move(self.entries, index, delta)
        self._refresh_models()
        self.tree.selection_set(entry["id"])

    def toggle_model(self):
        entry = self.selected_entry()
        if not entry:
            self.status_var.set(self.tr("need_select"))
            return
        entry["enabled"] = not entry.get("enabled")
        self._refresh_models()
        self.tree.selection_set(entry["id"])

    def clear_models(self):
        if not self.entries:
            return
        if messagebox.askyesno(self.tr("models"), self.tr("clear_all") + "?"):
            self.entries = []
            self._refresh_models()

    def test_model(self):
        entry = self.selected_entry()
        if not entry:
            self.status_var.set(self.tr("need_select"))
            return
        self.status_var.set(self.tr("running"))

        def worker():
            result = providers.test_connection(entry)
            self.after(0, lambda: self._show_test_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def _show_test_result(self, result):
        if not self.winfo_exists():
            return
        if result.get("ok"):
            text = str(result.get("text", ""))[:80].replace("\n", " ")
            self.status_var.set(self.tr("test_ok", text=text))
        else:
            self.status_var.set(self.tr("test_fail", error=result.get("error", "")))

    # ------------------------------------------------------------------ 生成

    def _collect_form(self):
        """把界面上的回答、备注、策略收进内存。"""
        self._sync_answer()
        try:
            self.note = self.note_text.get("1.0", "end").strip()
            self.include_note = bool(self.include_var.get())
        except tk.TkError:
            pass

    def generate(self):
        self._collect_form()
        if not any(value.strip() for value in self.answers.values()):
            messagebox.showwarning(self.tr("profile"), self.tr("no_answer"))
            return

        persona_data = persona.build_persona(self.answers, self.lang)
        storage.save_json(storage.PERSONA_FILE, persona_data)
        storage.save_json(storage.SECRET_FILE, persona.build_secret_note(self.note, self.include_note))
        self.prompt_text = persona.build_system_prompt(persona_data, self.note, self.include_note)
        storage.save_text(storage.PROMPT_FILE, self.prompt_text)

        active = models.enabled(self.entries)
        if not active:
            self.status_var.set(self.tr("no_models"))
        else:
            self.status_var.set(self.tr("done") + " · " + self.tr("model_count", n=len(active)))

        self._persist()
        ResultWindow(self, self.prompt_text, active, self.strategy, self.rotate_index)

    def copy_last_prompt(self):
        if not self.prompt_text:
            self._collect_form()
            persona_data = persona.build_persona(self.answers, self.lang)
            self.prompt_text = persona.build_system_prompt(persona_data, self.note, self.include_note)
        self.clipboard_clear()
        self.clipboard_append(self.prompt_text)
        self.status_var.set(self.tr("copy") + " ✓")

    def open_folder(self):
        directory = storage.app_dir()
        try:
            if sys.platform.startswith("win"):
                os.startfile(directory)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", directory])
            else:
                subprocess.Popen(["xdg-open", directory])
        except OSError as error:
            messagebox.showwarning(self.tr("err"), str(error))

    # ------------------------------------------------------------------ 持久化

    def _persist(self):
        self.config_data.update({
            "lang": self.lang,
            "models": self.entries,
            "strategy": self.strategy,
            "rotate_index": self.rotate_index,
            "note": self.note,
            "include_note": self.include_note,
            "answers": self.answers,
        })
        try:
            storage.save_config(self.config_data)
        except OSError as error:
            self.status_var.set(self.tr("err") + ": " + str(error))

    def on_close(self):
        self._collect_form()
        self._persist()
        self.destroy()


class ResultWindow(tk.Toplevel):
    """生成结果：系统提示词 + 多模型输出，模型调用在后台线程。"""

    def __init__(self, app: App, prompt: str, active: list, strategy: str, rotate_index: int):
        super().__init__(app)
        self.app = app
        self.prompt = prompt
        self.active = active
        self.strategy = strategy
        self.rotate_index = rotate_index
        self.queue = queue.Queue()

        self.title(app.tr("result_title"))
        self.geometry("900x700")
        self.transient(app)
        self.minsize(720, 560)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=10)

        prompt_tab = ttk.Frame(notebook, padding=8)
        output_tab = ttk.Frame(notebook, padding=8)
        notebook.add(prompt_tab, text=app.tr("tab_prompt"))
        notebook.add(output_tab, text=app.tr("tab_outputs"))

        prompt_text = tk.Text(
            prompt_tab, wrap="word", relief="solid", borderwidth=1,
            font=(FONT_BY_LANG.get(app.lang, "Segoe UI"), 10), padx=8, pady=8,
        )
        app.prep_text(prompt_text)
        prompt_text.pack(fill="both", expand=True)
        prompt_text.insert("1.0", prompt, "body")
        prompt_text.configure(state="disabled")

        buttons = ttk.Frame(prompt_tab)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text=app.tr("copy"), command=self._copy).pack(
            side="right" if app.rtl() else "left"
        )
        ttk.Button(buttons, text=app.tr("close"), command=self.destroy).pack(
            side="left" if app.rtl() else "right"
        )

        self.output_text = tk.Text(
            output_tab, wrap="word", relief="solid", borderwidth=1,
            font=(FONT_BY_LANG.get(app.lang, "Segoe UI"), 10), padx=8, pady=8,
        )
        app.prep_text(self.output_text)
        self.output_text.pack(fill="both", expand=True)
        self.output_text.insert("1.0", app.tr("running") if active else app.tr("no_models"), "body")
        self.output_text.configure(state="disabled")

        if active:
            self.after(120, self._start)

    def _copy(self):
        self.app.clipboard_clear()
        self.app.clipboard_append(self.prompt)
        self.app.status_var.set(self.app.tr("copy") + " ✓")

    def _start(self):
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": self.app.tr("probe")},
        ]

        def worker():
            results, next_index = providers.run(messages, self.active, self.strategy, self.rotate_index)
            self.queue.put((results, next_index))

        threading.Thread(target=worker, daemon=True).start()
        self.after(200, self._poll)

    def _poll(self):
        if not self.winfo_exists():
            return
        try:
            results, next_index = self.queue.get_nowait()
        except queue.Empty:
            self.after(250, self._poll)
            return

        self.app.rotate_index = next_index
        self.app._persist()

        lines = []
        for item in results:
            header = "== %s (%s) ==" % (item.get("name"), item.get("model"))
            body = item.get("text") if item.get("ok") else "✗ " + str(item.get("error"))
            lines.append(header + "\n" + str(body).strip())
        if not lines:
            lines.append(self.app.tr("no_models"))

        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", "\n\n".join(lines), "body")
        self.output_text.configure(state="disabled")
        self.app.status_var.set(self.app.tr("done"))
