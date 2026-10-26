from od_platform.cli.train_model import _parse_batch


def test_parse_batch_keeps_integer_as_batch_size():
    assert _parse_batch("16") == 16
    assert isinstance(_parse_batch("16"), int)


def test_parse_batch_keeps_fraction_as_memory_ratio():
    assert _parse_batch("0.7") == 0.7
    assert isinstance(_parse_batch("0.7"), float)
