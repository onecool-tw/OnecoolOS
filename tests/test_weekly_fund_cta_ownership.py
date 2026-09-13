from scripts import update_fund_alpha as updater


def test_weekly_alpha_preserves_daily_cta_evidence(tmp_path, monkeypatch):
    target = tmp_path / 'data/market/fund_nav/fund_cta_latest.json'
    target.parent.mkdir(parents=True)
    original = '{"generated_at":"2026-09-12T01:00:00Z","nav_refresh":{"status":"COMPLETE"},"results":[]}'
    target.write_text(original)
    monkeypatch.setattr(updater, 'FUND_WATCHLIST', {})
    monkeypatch.setattr(updater, 'alpha_payload', lambda *args: {})
    monkeypatch.setattr(updater, 'refresh_peer_rankings', lambda *args: {})
    updater.update(tmp_path)
    assert target.read_text() == original
    assert target.with_name('alpha_latest.json').exists()
