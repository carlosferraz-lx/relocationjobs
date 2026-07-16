from jobfinder import cost_of_living as col


def test_annualise():
    assert col.annualise(5000, "month") == 60000
    assert col.annualise(60000, "year") == 60000
    assert col.annualise(50, "hour") == 50 * 40 * 52


def test_to_eur_known_and_unknown():
    assert col.to_eur(100, "EUR") == 100
    assert col.to_eur(100, "GBP") == 117.0
    assert col.to_eur(100, "XYZ") is None


def test_city_override_beats_country_index():
    # London is pricier than the UK country-level index.
    assert col.col_index_for("GB", "London") > col.col_index_for("GB", None)


def test_required_gross_higher_in_expensive_country():
    pt = 60000
    uk = col.required_gross_eur("GB", "London", pt)
    se = col.required_gross_eur("SE", "Stockholm", pt)
    # A pricier city demands a higher gross than Sweden's capital.
    assert uk > se > 0


def test_required_gross_local_returns_currency():
    res = col.required_gross_local("NO", "Oslo", 60000)
    assert res is not None
    amount, currency = res
    assert currency == "NOK" and amount > 0


def test_unknown_country_returns_none():
    assert col.required_gross_eur("ZZ", None, 60000) is None
