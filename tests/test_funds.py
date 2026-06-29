import json
from decimal import Decimal
from pathlib import Path

from onecool_os.__main__ import main
from onecool_os.assets.funds.loader import FundLoader, FundLoaderError
from onecool_os.assets.funds.models import FundAsset, FundPosition
from onecool_os.portfolio.models import PortfolioError


def write_settings(config_dir: Path, root_dir: Path) -> None:
    config_dir.mkdir(exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        f"""
app:
  name: Onecool OS
  version: 0.5.0
  timezone: Asia/Taipei
  language: en
database:
  path: {root_dir / "onecool.sqlite3"}
paths:
  data_dir: {root_dir / "data"}
  cache_dir: {root_dir / "cache"}
  logs_dir: {root_dir / "logs"}
  exports_dir: {root_dir / "exports"}
runtime:
  debug: false
  environment: test
logging:
  level: INFO
""".strip(),
        encoding="utf-8",
    )


def test_fund_asset_creation() -> None:
    fund = sample_fund_asset()
    asset = fund.to_asset()

    assert fund.asset_type == "MUTUAL_FUND"
    assert fund.fund_house == "Sample Funds"
    assert asset.asset_type == "MUTUAL_FUND"
    assert asset.symbol == "USGROWTH"


def test_fund_asset_rejects_invalid_asset_type() -> None:
    try:
        FundAsset(
            asset_id="bad",
            symbol="BAD",
            asset_type="ETF",
            name="Bad Fund",
            currency="USD",
        )
    except PortfolioError as exc:
        assert "Unsupported fund asset_type" in str(exc)
    else:
        raise AssertionError("Invalid fund asset_type should be rejected.")


def test_fund_position_calculation() -> None:
    position = FundPosition(
        asset=sample_fund_asset(),
        quantity=Decimal("100"),
        average_cost=Decimal("12.50"),
        current_price=Decimal("13.20"),
    )

    assert position.total_cost() == Decimal("1250.00")
    assert position.market_value() == Decimal("1320.00")
    assert position.unrealized_pnl() == Decimal("70.00")


def test_fund_loader_valid_json(tmp_path: Path) -> None:
    result = FundLoader().load(write_funds_json(tmp_path))

    assert len(result.positions) == 2
    assert result.portfolio.total_cost() == Decimal("2030.00")
    assert result.portfolio.total_market_value() == Decimal("2128.00")


def test_fund_loader_invalid_json(tmp_path: Path) -> None:
    json_path = tmp_path / "funds.json"
    json_path.write_text("{invalid", encoding="utf-8")

    try:
        FundLoader().load(json_path)
    except FundLoaderError as exc:
        assert "Invalid funds JSON" in str(exc)
    else:
        raise AssertionError("Invalid JSON should be rejected.")


def test_fund_loader_missing_fields(tmp_path: Path) -> None:
    payload = funds_json_payload()
    del payload["funds"][0]["symbol"]
    json_path = write_funds_json(tmp_path, payload)

    try:
        FundLoader().load(json_path)
    except FundLoaderError as exc:
        assert "Missing required field" in str(exc)
        assert "symbol" in str(exc)
    else:
        raise AssertionError("Missing fields should be rejected.")


def test_fund_loader_invalid_asset_type(tmp_path: Path) -> None:
    payload = funds_json_payload()
    payload["funds"][0]["asset_type"] = "ETF"
    json_path = write_funds_json(tmp_path, payload)

    try:
        FundLoader().load(json_path)
    except FundLoaderError as exc:
        assert "Unsupported fund asset_type" in str(exc)
    else:
        raise AssertionError("Invalid asset_type should be rejected.")


def test_fund_loader_invalid_quantity(tmp_path: Path) -> None:
    payload = funds_json_payload()
    payload["funds"][0]["quantity"] = "invalid"
    json_path = write_funds_json(tmp_path, payload)

    try:
        FundLoader().load(json_path)
    except FundLoaderError as exc:
        assert "Invalid quantity" in str(exc)
    else:
        raise AssertionError("Invalid quantity should be rejected.")


def test_cli_funds_import_works(tmp_path: Path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    json_path = write_funds_json(tmp_path)

    assert main(["funds", "import", str(json_path)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(payload["funds"]) == 2
    assert payload["total_cost"] == "2030.00"
    assert payload["total_market_value"] == "2128.00"
    assert payload["total_unrealized_pnl"] == "98.00"


def test_fund_loader_portfolio_totals_correct(tmp_path: Path) -> None:
    result = FundLoader().load(write_funds_json(tmp_path))

    total_unrealized_pnl = (
        result.portfolio.total_market_value() - result.portfolio.total_cost()
    )

    assert result.portfolio.total_cost() == Decimal("2030.00")
    assert result.portfolio.total_market_value() == Decimal("2128.00")
    assert total_unrealized_pnl == Decimal("98.00")


def sample_fund_asset() -> FundAsset:
    return FundAsset(
        asset_id="FUND-US-GROWTH",
        symbol="USGROWTH",
        asset_type="MUTUAL_FUND",
        name="Sample US Growth Fund",
        currency="USD",
        fund_house="Sample Funds",
        region="US",
        theme="Growth",
    )


def funds_json_payload() -> dict[str, object]:
    return {
        "funds": [
            {
                "asset_id": "FUND-US-GROWTH",
                "symbol": "USGROWTH",
                "asset_type": "MUTUAL_FUND",
                "name": "Sample US Growth Fund",
                "currency": "USD",
                "fund_house": "Sample Funds",
                "region": "US",
                "theme": "Growth",
                "quantity": "100",
                "average_cost": "12.50",
                "current_price": "13.20",
            },
            {
                "asset_id": "FUND-GLOBAL-INCOME",
                "symbol": "GLBINCOME",
                "asset_type": "MUTUAL_FUND",
                "name": "Sample Global Income Fund",
                "currency": "USD",
                "fund_house": "Example Asset Management",
                "region": "Global",
                "theme": "Income",
                "quantity": "80",
                "average_cost": "9.75",
                "current_price": "10.10",
            },
        ],
    }


def write_funds_json(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
) -> Path:
    json_path = tmp_path / "funds.json"
    json_path.write_text(
        json.dumps(payload or funds_json_payload()),
        encoding="utf-8",
    )
    return json_path
