from od_platform.inference.pipeline_config import load_pipeline_config


def test_default_pipeline_config_is_resolved_from_workspace():
    cfg = load_pipeline_config(None)

    assert cfg.viz_enabled is True
    assert cfg.label_mapping["person"] == "人员"
    assert cfg.camera_raw["width"] == 1280
