"""Offline regression checks. No real credentials or service imports required."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_RECIPIENT = "synthetic-recipient-offline"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrivacyTests(unittest.TestCase):
    def setUp(self):
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = Mock()
        self.patch_modules = patch.dict(sys.modules, {"dotenv": dotenv})
        self.patch_modules.start()
        self.addCleanup(self.patch_modules.stop)
        self.main = load_module("offline_main", "src/main.py")

    def test_missing_recipient_fails_before_service_imports(self):
        # A service import would fail: this also catches import-time API setup.
        with patch.dict(os.environ, {}, clear=True), patch.dict(
            sys.modules, {"src.collectors.rss_collector": None}
        ), self.assertRaisesRegex(ValueError, "must be configured"):
            self.main.run()

    def test_empty_recipient_fails_before_service_imports(self):
        with patch.dict(os.environ, {"TELEGRAM_CHAT_ID": ""}), patch.dict(
            sys.modules, {"src.collectors.rss_collector": None}
        ), self.assertRaisesRegex(ValueError, "must be configured"):
            self.main.run()

    def test_whitespace_recipient_fails_before_service_imports(self):
        with patch.dict(os.environ, {"TELEGRAM_CHAT_ID": "  \n"}), patch.dict(
            sys.modules, {"src.collectors.rss_collector": None}
        ), self.assertRaisesRegex(ValueError, "must be configured"):
            self.main.run()

    def test_single_recipient_preserves_outputs_without_database(self):
        articles, digest, market = [{"title": "Synthetic"}], {"ai_news": []}, []
        calls = []
        mocks = {}
        modules = {"src.storage.user_store": None}
        services = {
            "src.collectors.rss_collector": ("fetch_all_feeds", articles),
            "src.collectors.market_collector": ("fetch_market_data", market),
            "src.processing.dedup": ("deduplicate_articles", articles),
            "src.processing.summarizer": ("generate_digest", digest),
            "src.charts.chart_generator": ("generate_market_chart", None),
            "src.delivery.telegram_sender": ("send_digest_sync", None),
            "src.storage.digest_store": ("save_digest", None),
            "src.dashboard.build_dashboard": ("build_dashboard", None),
        }
        for module_name, (function, result) in services.items():
            module = types.ModuleType(module_name)

            def record(*args, _function=function, _result=result, **kwargs):
                calls.append(_function)
                return _result

            mocks[function] = Mock(side_effect=record)
            setattr(module, function, mocks[function])
            modules[module_name] = module
        output = io.StringIO()
        with patch.dict(sys.modules, modules), patch.dict(
            os.environ, {"TELEGRAM_CHAT_ID": f" {SYNTHETIC_RECIPIENT} "}
        ), contextlib.redirect_stdout(output):
            self.main.run()
        mocks["fetch_market_data"].assert_called_once_with(
            market="both", custom_tickers=[]
        )
        sender = mocks["send_digest_sync"]
        sender.assert_called_once()
        self.assertEqual(sender.call_args.kwargs["chat_id"], SYNTHETIC_RECIPIENT)
        self.assertIs(sender.call_args.kwargs["digest"], digest)
        self.assertIs(sender.call_args.kwargs["market_data"], market)
        date = sender.call_args.kwargs["date_str"]
        mocks["save_digest"].assert_called_once_with(digest, date)
        mocks["build_dashboard"].assert_called_once_with(digest, market, date)
        self.assertEqual(calls, [
            "fetch_all_feeds", "deduplicate_articles", "generate_digest",
            "save_digest", "fetch_market_data", "generate_market_chart",
            "build_dashboard", "send_digest_sync",
        ])
        self.assertNotIn(SYNTHETIC_RECIPIENT, output.getvalue())
        self.assertFalse(Path(sender.call_args.kwargs["chart_path"]).exists())

    def test_sender_brief_and_chart_sequence_is_private(self):
        self.check_sender(chart=True, market=True, second_method="send_photo")

    def test_sender_market_fallback_sequence_is_private(self):
        self.check_sender(chart=False, market=True, second_method="send_message")

    def test_sender_unavailable_fallback_sequence_is_private(self):
        self.check_sender(chart=False, market=False, second_method="send_message")

    def check_sender(self, chart, market, second_method):
        telegram = types.ModuleType("telegram")
        bot = Mock()
        bot.send_message = AsyncMock()
        bot.send_photo = AsyncMock()
        telegram.Bot = Mock(return_value=bot)
        telegram.InlineKeyboardButton = Mock()
        telegram.InlineKeyboardMarkup = Mock()
        with patch.dict(sys.modules, {"telegram": telegram}), patch.dict(
            os.environ, {"TELEGRAM_BOT_TOKEN": "synthetic-offline-token"}
        ):
            sender = load_module("offline_sender", "src/delivery/telegram_sender.py")
        market_data = [{"label": "TEST", "currency": "$", "price": 1,
                        "change_pct": 0}] if market else []
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            chart_path = Path(directory) / "synthetic.png"
            if chart:
                chart_path.write_bytes(b"synthetic-chart")
            with contextlib.redirect_stdout(output):
                sender.send_digest_sync(SYNTHETIC_RECIPIENT, {}, market_data,
                                        str(chart_path), "2000-01-01")
        self.assertEqual([call[0] for call in bot.mock_calls],
                         ["send_message", second_method])
        self.assertEqual(bot.send_message.await_count, 1 if chart else 2)
        self.assertEqual(bot.send_photo.await_count, 1 if chart else 0)
        for call in bot.mock_calls:
            self.assertEqual(call.kwargs["chat_id"], SYNTHETIC_RECIPIENT)
        self.assertNotIn(SYNTHETIC_RECIPIENT, output.getvalue())

    def test_workflow_stages_only_public_outputs_and_ignores_private_files(self):
        workflow = (ROOT / ".github/workflows/daily_digest.yml").read_text()
        self.assertIn('cron: "30 2 * * *"', workflow)
        self.assertIn("TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}", workflow)
        self.assertNotIn("users.db", workflow)
        staging = [line.strip() for line in workflow.splitlines()
                   if line.strip().startswith("git add ")]
        self.assertEqual(staging, ["git add digests/ docs/"])
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)

            def git(*args):
                return subprocess.run(["git", *args], cwd=cwd, check=True,
                                      capture_output=True, text=True).stdout

            git("init", "--quiet")
            (cwd / ".gitignore").write_text((ROOT / ".gitignore").read_text())
            files = ["digests/2000-01-01.json", "docs/index.html", "users.db",
                     "users.db-wal", "users.db-shm", "users.db-journal",
                     "worker/.wrangler/cache/account.json", ".env",
                     ".env.local", "worker/.dev.vars"]
            for file in files:
                path = cwd / file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic")
            # Execute only the actual staging command, never the workflow.
            git(*staging[0].split()[1:])
            self.assertEqual(git("diff", "--cached", "--name-only").splitlines(),
                             ["digests/2000-01-01.json", "docs/index.html"])
            for file in files[2:]:
                self.assertEqual(git("check-ignore", file).strip(), file)


if __name__ == "__main__":
    unittest.main()
