import types

import pytest

from src.trainer.background import BackgroundTrainer


class FakeProcessManager:
    def __init__(self):
        self.attached = False

    def attach(self) -> bool:
        self.attached = True
        return True

    def detach(self) -> None:
        self.attached = False

    def is_attached(self) -> bool:
        return self.attached


class FakeMemoryScanner:
    def __init__(self, process_manager):
        self.process_manager = process_manager
        self.attached = False
        self.detach_calls = 0

    def attach(self) -> bool:
        self.attached = True
        return True

    def detach(self) -> None:
        self.attached = False
        self.detach_calls += 1

    def is_attached(self) -> bool:
        return self.attached


class FakeCheatManager:
    def __init__(self):
        self.deactivated = False

    def deactivate_all_cheats(self) -> None:
        self.deactivated = True


class FakeHotkeyManager:
    def __init__(self):
        self.registered = []
        self.started = False

    def register_hotkey(self, key, action, description, modifiers=None):
        self.registered.append(
            {
                "key": key,
                "modifiers": modifiers or [],
                "action": action,
                "description": description,
            }
        )
        return True

    def start(self):
        self.started = True
        return True

    def stop(self):
        self.started = False

    def is_listening(self):
        return self.started


class FakeTrainerCheats:
    def __init__(self):
        self.setup_called_with = None

    def setup_default_cheat_hotkeys(self, cheat_manager):
        self.setup_called_with = cheat_manager
        return True


class FakeMonitor:
    def __init__(self):
        self.poll_interval = 0.5
        self.started = False
        self.stopped = False
        self.on_start = None
        self.on_stop = None
        self.on_update = None

    def set_callbacks(self, on_game_started=None, on_game_stopped=None, on_state_update=None, **_):
        self.on_start = on_game_started
        self.on_stop = on_game_stopped
        self.on_update = on_state_update

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


@pytest.fixture()
def trainer_with_fakes():
    process_manager = FakeProcessManager()
    scanner = FakeMemoryScanner(process_manager)
    cheat_manager = FakeCheatManager()
    hotkey_manager = FakeHotkeyManager()
    cheat_hotkeys = FakeTrainerCheats()
    monitor = FakeMonitor()

    trainer = BackgroundTrainer(
        process_manager=process_manager,
        memory_scanner=scanner,
        cheat_manager=cheat_manager,
        hotkey_manager=hotkey_manager,
        cheat_hotkeys=cheat_hotkeys,
        game_monitor=monitor,
        gui_launcher=lambda: None,
    )
    return types.SimpleNamespace(
        trainer=trainer,
        process_manager=process_manager,
        scanner=scanner,
        cheat_manager=cheat_manager,
        hotkey_manager=hotkey_manager,
        cheat_hotkeys=cheat_hotkeys,
        monitor=monitor,
    )


def test_background_trainer_registers_hotkeys_and_starts_listener(trainer_with_fakes):
    trainer_with_fakes.trainer.start()

    assert trainer_with_fakes.hotkey_manager.started is True
    assert trainer_with_fakes.monitor.started is True
    assert trainer_with_fakes.cheat_hotkeys.setup_called_with is trainer_with_fakes.cheat_manager

    gui_hotkeys = [
        reg for reg in trainer_with_fakes.hotkey_manager.registered if reg["key"] == "f10"
    ]
    assert gui_hotkeys, "GUI hotkey should be registered"
    assert gui_hotkeys[0]["modifiers"] == ["ctrl"]


def test_background_trainer_attaches_and_detaches_on_events(trainer_with_fakes):
    trainer = trainer_with_fakes.trainer
    monitor = trainer_with_fakes.monitor

    trainer.start()
    monitor.on_start(1234)
    assert trainer_with_fakes.scanner.attached is True

    monitor.on_stop()
    assert trainer_with_fakes.scanner.attached is False
    assert trainer_with_fakes.cheat_manager.deactivated is True
    assert trainer_with_fakes.scanner.detach_calls == 1


def test_background_trainer_retries_attach_on_state_update(trainer_with_fakes):
    trainer = trainer_with_fakes.trainer
    monitor = trainer_with_fakes.monitor

    trainer.start()
    trainer_with_fakes.scanner.attached = False

    monitor.on_update({"pid": 9876})
    assert trainer_with_fakes.scanner.attached is True
