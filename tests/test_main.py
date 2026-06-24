from unittest.mock import MagicMock, patch

import heizung.__main__ as main_mod


def test_main_wires_config_gpio_and_runs():
    cfg = {"operating_mode": "pellets", "logger": "False"}
    fake_control = MagicMock()

    with (
        patch.object(main_mod, "load_config", return_value=cfg) as load_config,
        patch.object(main_mod, "setup_gpio", return_value=(False, None)) as setup_gpio,
        patch.object(main_mod, "FiringControl", return_value=fake_control) as FiringControl,
    ):
        main_mod.main()

    load_config.assert_called_once()
    setup_gpio.assert_called_once()
    FiringControl.assert_called_once_with(cfg, None)
    fake_control.run.assert_called_once()


def test_main_logs_to_logger_when_enabled():
    cfg = {"operating_mode": "firewood", "logger": "True"}

    with (
        patch.object(main_mod, "load_config", return_value=cfg),
        patch.object(main_mod, "setup_gpio", return_value=(False, None)),
        patch.object(main_mod, "FiringControl", return_value=MagicMock()),
        patch("logging.getLogger") as get_logger,
    ):
        main_mod.main()

    # logger branch was used at least once
    assert get_logger.called

