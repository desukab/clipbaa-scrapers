def test_package_importable():
    import scrapers
    assert scrapers.__name__ == "scrapers"


def test_cli_entrypoint_runs():
    from scrapers.cli import main
    assert main(["list-sources"]) == 0