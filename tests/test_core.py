"""核心逻辑单元测试（不依赖 tkinter，可在无显示环境运行）。

运行：py -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import i18n, models, persona, providers, storage  # noqa: E402


class I18nTest(unittest.TestCase):
    def test_all_languages_have_same_keys(self):
        base = set(i18n.STRINGS["zh"].keys())
        for code in i18n.LANG_CODES:
            self.assertIn(code, i18n.STRINGS, "缺少语言 %s" % code)
            self.assertEqual(base, set(i18n.STRINGS[code].keys()), "语言 %s 的键与中文不一致" % code)

    def test_every_translation_is_non_empty(self):
        for code in i18n.LANG_CODES:
            for key, value in i18n.STRINGS[code].items():
                self.assertTrue(str(value).strip(), "%s/%s 为空" % (code, key))

    def test_questions_cover_all_dimensions(self):
        self.assertEqual(len(i18n.DIM_KEYS), 12)
        for code in i18n.LANG_CODES:
            for key in i18n.DIM_KEYS:
                self.assertTrue(i18n.question(code, key).strip())

    def test_rtl_and_labels(self):
        self.assertTrue(i18n.is_rtl("ar"))
        self.assertFalse(i18n.is_rtl("en"))
        self.assertEqual(i18n.lang_label("zh"), "简体中文")

    def test_placeholders_render(self):
        self.assertIn("3", i18n.t("en", "progress", n=3, total=12))
        self.assertIn("模型", i18n.t("zh", "added", name="模型"))


class PersonaTest(unittest.TestCase):
    def test_build_persona_uses_chinese_labels(self):
        answers = {"dim1": "广州 测试", "dim3": "  直接  ", "dim5": ""}
        data = persona.build_persona(answers, "fr")
        self.assertEqual(data["ui_language"], "fr")
        self.assertIn("身份与背景", data["dimensions"])
        self.assertIn("沟通风格", data["dimensions"])
        self.assertNotIn("兴趣爱好", data["dimensions"], "空回答不应写入画像")

    def test_system_prompt_contains_tags_and_rules(self):
        data = persona.build_persona({"dim1": "广州"}, "en")
        prompt = persona.build_system_prompt(data, "不要提我的公司名", True)
        self.assertIn("【用户画像】", prompt)
        self.assertIn("身份与背景", prompt)
        self.assertIn("不要提我的公司名", prompt)
        self.assertIn("【回答要求】", prompt)

    def test_secret_note_can_be_excluded(self):
        data = persona.build_persona({"dim1": "广州"}, "en")
        prompt = persona.build_system_prompt(data, "私密内容", False)
        self.assertNotIn("私密内容", prompt)

    def test_empty_persona_still_valid(self):
        data = persona.build_persona({}, "zh")
        self.assertEqual(data["dimensions"], {})
        prompt = persona.build_system_prompt(data)
        self.assertIn("尚未填写任何维度", prompt)

    def test_secret_note_payload(self):
        payload = persona.build_secret_note("备注", True)
        self.assertEqual(payload["note"], "备注")
        self.assertTrue(payload["include_in_prompt"])


class ModelsTest(unittest.TestCase):
    def test_catalog_matches_language(self):
        fr = models.catalog_for("fr")
        self.assertTrue(fr)
        for item in fr:
            self.assertTrue("all" in item["langs"] or "fr" in item["langs"])

    def test_every_catalog_entry_has_required_fields(self):
        for item in models.CATALOG:
            self.assertTrue(item["name"])
            self.assertTrue(item["base_url"].startswith("http"))
            self.assertTrue(item["model"])

    def test_validate(self):
        good = models.new_entry(name="A", base_url="https://a.com/v1", model="m")
        self.assertEqual(models.validate(good), (True, ""))
        # 名称为空时自动回退成模型 ID，因此校验只需要模型与地址
        fallback = models.new_entry(name="", model="m", base_url="https://a.com")
        self.assertEqual(fallback["name"], "m")
        self.assertEqual(models.validate(fallback), (True, ""))
        self.assertEqual(models.validate(models.new_entry(name="A", model="", base_url="https://a.com"))[1], "model_required")
        self.assertEqual(models.validate(models.new_entry(name="A", model="m", base_url=""))[1], "base_required")
        self.assertEqual(models.validate(models.new_entry(name="A", model="m", base_url="ftp://a"))[1], "base_invalid")

    def test_duplicate_detection(self):
        entry = models.new_entry(name="A", base_url="https://a.com/v1", model="m")
        self.assertTrue(models.is_duplicate([entry], models.new_entry(name="B", base_url="https://a.com/v1/", model="m")))
        self.assertFalse(models.is_duplicate([entry], models.new_entry(name="B", base_url="https://a.com/v1", model="m2")))

    def test_move_and_enabled(self):
        items = [models.new_entry(name=str(i), base_url="https://a.com/v1", model=str(i)) for i in range(3)]
        models.move(items, 0, 1)
        self.assertEqual([item["name"] for item in items], ["1", "0", "2"])
        models.move(items, 0, -1)  # 越界不改变顺序
        self.assertEqual([item["name"] for item in items], ["1", "0", "2"])
        items[1]["enabled"] = False
        self.assertEqual(len(models.enabled(items)), 2)


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = storage.app_dir
        storage.app_dir = lambda: self.temp.name

    def tearDown(self):
        storage.app_dir = self.original
        self.temp.cleanup()

    def test_json_roundtrip(self):
        storage.save_json("x.json", {"中文": "值"})
        self.assertEqual(storage.load_json("x.json")["中文"], "值")

    def test_load_missing_returns_default(self):
        self.assertIsNone(storage.load_json("none.json"))
        self.assertEqual(storage.load_json("none.json", {}), {})

    def test_broken_json_returns_default(self):
        with open(os.path.join(self.temp.name, "bad.json"), "w", encoding="utf-8") as handle:
            handle.write("{not json")
        self.assertEqual(storage.load_json("bad.json", {"ok": 1}), {"ok": 1})

    def test_config_defaults_are_merged(self):
        storage.save_config({"lang": "ja"})
        config = storage.load_config()
        self.assertEqual(config["lang"], "ja")
        self.assertEqual(config["strategy"], "primary")
        self.assertEqual(config["models"], [])
        self.assertIsInstance(config["answers"], dict)

    def test_text_roundtrip(self):
        storage.save_text("p.txt", "系统提示词")
        self.assertEqual(storage.read_text("p.txt"), "系统提示词")


class ProviderTest(unittest.TestCase):
    def test_endpoint_join(self):
        self.assertEqual(providers._endpoint("https://a.com/v1"), "https://a.com/v1/chat/completions")
        self.assertEqual(providers._endpoint("https://a.com/v1/"), "https://a.com/v1/chat/completions")
        self.assertEqual(
            providers._endpoint("https://a.com/v1/chat/completions"),
            "https://a.com/v1/chat/completions",
        )

    def test_unreachable_host_returns_error_not_raise(self):
        entry = models.new_entry(name="x", base_url="http://127.0.0.1:9/v1", model="m")
        result = providers.chat(entry, [{"role": "user", "content": "hi"}], timeout=3)
        self.assertFalse(result["ok"])
        self.assertTrue(result["error"])

    def test_invalid_url_returns_error(self):
        entry = models.new_entry(name="x", base_url="not-a-url", model="m")
        result = providers.chat(entry, [{"role": "user", "content": "hi"}], timeout=3)
        self.assertFalse(result["ok"])

    def test_run_without_entries(self):
        results, index = providers.run([{"role": "user", "content": "hi"}], [], "poll", 5)
        self.assertEqual(results, [])
        self.assertEqual(index, 5)


class ProviderStubServerTest(unittest.TestCase):
    """用本地假服务器验证 OpenAI 兼容协议与三种执行策略。"""

    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) or b"{}"
                payload = json.loads(raw or b"{}")
                model = str(payload.get("model", ""))

                if model == "boom":
                    body = json.dumps({"error": {"message": "bad model"}}).encode("utf-8")
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                if model == "junk":
                    body = b"<html>not json</html>"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                body = json.dumps(
                    {"choices": [{"message": {"content": "reply from " + model}}]}
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def entry(self, model):
        return models.new_entry(
            name=model,
            base_url="http://127.0.0.1:%d/v1" % self.port,
            model=model,
        )

    def messages(self):
        return [{"role": "user", "content": "hi"}]

    def test_chat_success(self):
        result = providers.chat(self.entry("ok-1"), self.messages(), timeout=5)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["text"], "reply from ok-1")

    def test_chat_http_error_detail(self):
        result = providers.chat(self.entry("boom"), self.messages(), timeout=5)
        self.assertFalse(result["ok"])
        self.assertIn("bad model", result["error"])

    def test_chat_non_json_response(self):
        result = providers.chat(self.entry("junk"), self.messages(), timeout=5)
        self.assertFalse(result["ok"])
        self.assertIn("OpenAI", result["error"])

    def test_poll_strategy_rotates(self):
        entries = [self.entry("ok-1"), self.entry("ok-2")]
        first, index = providers.run(self.messages(), entries, "poll", 0)
        self.assertEqual(first[0]["text"], "reply from ok-1")
        self.assertEqual(index, 1)
        second, index = providers.run(self.messages(), entries, "poll", index)
        self.assertEqual(second[0]["text"], "reply from ok-2")
        self.assertEqual(index, 0)

    def test_parallel_strategy_returns_every_model(self):
        entries = [self.entry("ok-1"), self.entry("ok-2"), self.entry("boom")]
        results, index = providers.run(self.messages(), entries, "parallel", 3)
        self.assertEqual(len(results), 3)
        self.assertEqual(index, 3)
        ok = [item for item in results if item["ok"]]
        self.assertEqual(len(ok), 2)
        self.assertTrue(any("bad model" in item.get("error", "") for item in results if not item["ok"]))

    def test_primary_strategy_uses_first_entry(self):
        entries = [self.entry("ok-1"), self.entry("boom")]
        results, index = providers.run(self.messages(), entries, "primary", 0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "ok-1")
        self.assertEqual(index, 0)


if __name__ == "__main__":
    unittest.main()
