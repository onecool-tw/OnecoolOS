from pathlib import Path


def test_yfinance_major_version_is_bounded_for_reproducible_market_inputs():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    assert 'yfinance>=0.2.40,<1.0' in pyproject
    assert 'yfinance>=0.2.40,<1.0' in requirements
    assert 'pandas>=2.2,<3.0' in pyproject
    assert 'pandas>=2.2,<3.0' in requirements
