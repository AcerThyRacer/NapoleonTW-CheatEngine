"""
Tests for the shared EngineService startup flow.
"""

import logging
from pathlib import Path
from unittest.mock import Mock, patch

from src.engine_service import EngineService


class TestEngineService:
    """Tests for canonical application bootstrap."""

    def test_bootstrap_uses_ini_log_level_once(self, tmp_path):
        ini_path = tmp_path / "napoleon.ini"
        ini_path.write_text("[Logging]\nlevel = warning\n", encoding="utf-8")

        setup_logging = Mock()
        error_reporter_factory = Mock(return_value=Mock())
        service = EngineService(
            ini_path=ini_path,
            logging_setup=setup_logging,
            error_reporter_factory=error_reporter_factory,
        )

        with patch.object(service, "load_startup_plugins") as mock_plugins:
            first_result = service.run(lambda current: current, load_plugins=True)
            second_result = service.run(lambda current: current)

        assert first_result is service
        assert second_result is service
        setup_logging.assert_called_once_with(level=logging.WARNING, log_dir=Path.cwd())
        error_reporter_factory.assert_called_once_with()
        mock_plugins.assert_called_once_with()

    def test_debug_flag_overrides_ini_log_level(self, tmp_path):
        ini_path = tmp_path / "napoleon.ini"
        ini_path.write_text("[logging]\nlevel = error\n", encoding="utf-8")

        setup_logging = Mock()
        service = EngineService(
            ini_path=ini_path,
            debug=True,
            logging_setup=setup_logging,
            error_reporter_factory=Mock(return_value=Mock()),
        )

        service.bootstrap()

        assert setup_logging.call_args.kwargs["level"] == logging.DEBUG


class TestMainEntryPoint:
    """Tests for main mode dispatch."""

    def test_main_defaults_to_gui(self):
        import src.main as main_module

        with patch.object(main_module, "launch_gui") as mock_launch_gui:
            main_module.main([])

        service = mock_launch_gui.call_args.args[0]
        assert isinstance(service, EngineService)
        assert service.ini_path == Path("napoleon.ini")

    def test_main_routes_web_mode(self):
        import src.main as main_module

        with patch.object(main_module, "launch_web") as mock_launch_web:
            main_module.main(["--web", "--ini", "custom.ini"])

        service = mock_launch_web.call_args.args[0]
        assert isinstance(service, EngineService)
        assert service.ini_path == Path("custom.ini")

    def test_launch_cli_uses_shared_engine_service(self):
        import src.main as main_module
        from src.cli import interactive as cli_module

        service = Mock()
        service.run = Mock(return_value="cli-result")

        result = main_module.launch_cli(service)

        assert result == "cli-result"
        service.run.assert_called_once_with(cli_module.run_cli)

    def test_launch_web_uses_shared_engine_service(self):
        import src.main as main_module
        from src.server import websocket_server

        service = Mock()
        service.run = Mock(return_value="web-result")

        result = main_module.launch_web(service)

        assert result == "web-result"
        service.run.assert_called_once_with(websocket_server.run_server)
