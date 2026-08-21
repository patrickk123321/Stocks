from app.portfolio_engine import compute_allocation, compute_recommendations, derive_target_allocation


def test_derive_target_allocation_known_profile():
    assert derive_target_allocation("aggressive") == {"stock": 90.0, "bond": 10.0, "cash": 0.0}


def test_derive_target_allocation_unknown_falls_back_to_moderate():
    assert derive_target_allocation("not-a-real-profile") == derive_target_allocation("moderate")


def test_compute_allocation_splits_by_asset_class_and_sector():
    holdings = [
        {"ticker": "AAPL", "shares": 10, "value": 1000},  # stock, Technology
        {"ticker": "MSFT", "shares": 5, "value": 1000},  # stock, Technology
        {"ticker": "BND", "shares": 20, "value": 2000},  # bond
    ]
    allocation = compute_allocation(holdings)
    assert allocation["total_value"] == 4000
    assert allocation["asset_class"]["stock"]["pct"] == 50.0
    assert allocation["asset_class"]["bond"]["pct"] == 50.0
    # both equity holdings are Technology -> 100% of equity value
    assert allocation["sector"]["Technology"]["pct"] == 100.0


def test_compute_allocation_unclassified_ticker_does_not_crash():
    holdings = [{"ticker": "ZZZNOTREAL", "shares": 1, "value": 500}]
    allocation = compute_allocation(holdings)
    assert allocation["asset_class"]["Unclassified"]["pct"] == 100.0
    assert allocation["sector"] == {}  # only "stock" holdings contribute to sector breakdown


def test_compute_allocation_empty_holdings_does_not_divide_by_zero():
    allocation = compute_allocation([])
    assert allocation["total_value"] == 0
    assert allocation["asset_class"] == {}


def test_compute_recommendations_flags_overweight_equities():
    # 100% stock vs. a conservative target of 30% stock -> large overweight gap
    holdings = [{"ticker": "AAPL", "shares": 10, "value": 10000}]
    result = compute_recommendations(holdings, "conservative")
    stock_gap = next(g for g in result["gaps"] if g["asset_class"] == "stock")
    assert stock_gap["direction"] == "overweight"
    assert stock_gap["current_pct"] == 100.0
    # overweight gaps don't get "buy more" fund suggestions
    assert stock_gap["suggested_funds"] == []


def test_compute_recommendations_suggests_funds_for_underweight():
    # all cash vs. an aggressive target (90% stock) -> stock is heavily underweight
    holdings = [{"ticker": "CASH", "shares": 1, "value": 10000}]
    result = compute_recommendations(holdings, "aggressive")
    stock_gap = next(g for g in result["gaps"] if g["asset_class"] == "stock")
    assert stock_gap["direction"] == "underweight"
    assert len(stock_gap["suggested_funds"]) > 0


def test_compute_recommendations_no_gap_within_threshold():
    # moderate target is 60/30/10 stock/bond/cash — match it closely, expect no gaps flagged
    holdings = [
        {"ticker": "AAPL", "shares": 1, "value": 600},
        {"ticker": "BND", "shares": 1, "value": 300},
        {"ticker": "CASH", "shares": 1, "value": 100},
    ]
    result = compute_recommendations(holdings, "moderate")
    assert result["gaps"] == []


def test_compute_recommendations_flags_sector_concentration():
    holdings = [
        {"ticker": "AAPL", "shares": 1, "value": 4000},  # Technology
        {"ticker": "MSFT", "shares": 1, "value": 4000},  # Technology
        {"ticker": "JNJ", "shares": 1, "value": 2000},  # Healthcare
    ]
    result = compute_recommendations(holdings, "aggressive")
    tech_flag = next((f for f in result["sector_flags"] if f["sector"] == "Technology"), None)
    assert tech_flag is not None
    assert tech_flag["pct"] == 80.0
