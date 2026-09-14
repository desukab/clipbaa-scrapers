import pytest

import scrapers.registry as reg


def _reset():
    reg._SOURCES.clear()


def test_register_and_get():
    _reset()
    spec = reg.SourceSpec(
        name="amazon",
        title="Amazon",
        output_file="amazon_raw.json",
        default_max_products=5,
        live_capable=True,
        mock_items=(),
    )
    reg.register_source(spec)
    assert reg.get_source("amazon") is spec
    assert reg.builtin_names() == ("amazon",)


def test_duplicate_rejected():
    _reset()
    spec = reg.SourceSpec(name="amazon", title="A", output_file="a.json",
                          default_max_products=1, live_capable=True, mock_items=())
    reg.register_source(spec)
    with pytest.raises(ValueError):
        reg.register_source(spec)


def test_get_unknown_lists_names():
    _reset()
    reg.register_source(reg.SourceSpec(name="x", title="X", output_file="x.json",
                                       default_max_products=1, live_capable=True, mock_items=()))
    with pytest.raises(KeyError) as exc:
        reg.get_source("nope")
    assert "x" in str(exc.value)