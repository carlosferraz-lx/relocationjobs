"""Standard-of-living salary floor computation.

The idea: your current gross salary in Portugal buys a certain lifestyle. To keep
that lifestyle in another country you need enough *net* income to cover that
country's (higher) cost of living, which in turn requires a certain *gross*
salary given local taxes.

    portugal_net        = current_gross * net_ratio[PT]
    required_net(C)     = portugal_net * (col_index[C] / col_index[PT]) * margin
    required_gross(C)   = required_net(C) / net_ratio[C]              # in EUR
    required_gross_local= required_gross(C) / eur_per_unit[currency]  # local ccy

All numbers below are approximate and easy to edit. Cost-of-living figures are
based on Numbeo's "Cost of Living Plus Rent" index (capital-city level); net
ratios are rough effective take-home rates for a single mid/senior salary.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CountryEconomics:
    name: str
    currency: str
    # Cost of living incl. rent, Numbeo-style, Lisbon normalised to 100.
    col_index: float
    # Approximate net/gross take-home ratio for a single mid/senior salary.
    net_ratio: float


# Lisbon is the baseline (col_index = 100).
COUNTRIES: dict[str, CountryEconomics] = {
    "PT": CountryEconomics("Portugal", "EUR", 100.0, 0.66),
    "GB": CountryEconomics("United Kingdom", "GBP", 168.0, 0.68),
    "NL": CountryEconomics("Netherlands", "EUR", 128.0, 0.65),
    "BE": CountryEconomics("Belgium", "EUR", 122.0, 0.62),
    "CA": CountryEconomics("Canada", "CAD", 130.0, 0.70),
    "NO": CountryEconomics("Norway", "NOK", 150.0, 0.70),
    "SE": CountryEconomics("Sweden", "SEK", 118.0, 0.69),
    "IS": CountryEconomics("Iceland", "ISK", 165.0, 0.68),
    "DK": CountryEconomics("Denmark", "DKK", 150.0, 0.62),
    "FI": CountryEconomics("Finland", "EUR", 120.0, 0.66),
}

# City-level cost-of-living overrides (Lisbon = 100). Optional; falls back to the
# country index when a city is not listed.
CITY_COL_INDEX: dict[str, float] = {
    "london": 178.0,
    "manchester": 120.0,
    "edinburgh": 130.0,
    "oslo": 150.0,
    "bergen": 135.0,
    "stockholm": 122.0,
    "gothenburg": 108.0,
    "malmo": 100.0,
    "reykjavik": 165.0,
    "copenhagen": 155.0,
    "aarhus": 128.0,
    "helsinki": 122.0,
    "espoo": 118.0,
    "amsterdam": 135.0,
    "rotterdam": 120.0,
    "the hague": 122.0,
    "utrecht": 115.0,
    "brussels": 125.0,
    "brugge": 110.0,
    "antwerp": 120.0,
    "ghent": 115.0,
    "toronto": 145.0,
    "vancouver": 150.0,
    "montreal": 125.0,
    "ottawa": 120.0,
    "calgary": 120.0,
    "edmonton": 118.0,
}

# Approximate EUR value of one unit of each currency. Editable; refresh anytime.
EUR_PER_UNIT: dict[str, float] = {
    "EUR": 1.0,
    "GBP": 1.17,
    "NOK": 0.086,
    "SEK": 0.088,
    "DKK": 0.134,
    "ISK": 0.0066,
    "USD": 0.92,
    "CAD": 0.65,
}


def to_eur(amount: float, currency: str) -> float | None:
    rate = EUR_PER_UNIT.get(currency.upper())
    if rate is None:
        return None
    return amount * rate


def annualise(amount: float, period: str) -> float:
    p = (period or "year").lower()
    if p.startswith("month"):
        return amount * 12
    if p.startswith("hour"):
        return amount * 40 * 52  # 40h/week, 52 weeks
    if p.startswith("day"):
        return amount * 5 * 52
    if p.startswith("week"):
        return amount * 52
    return amount


def col_index_for(country: str, city: str | None) -> float:
    if city:
        idx = CITY_COL_INDEX.get(city.strip().lower())
        if idx is not None:
            return idx
    econ = COUNTRIES.get(country.upper())
    return econ.col_index if econ else 100.0


def portugal_net(current_gross: float) -> float:
    return current_gross * COUNTRIES["PT"].net_ratio


def required_gross_eur(
    country: str,
    city: str | None,
    current_gross_pt: float,
    margin: float = 1.0,
) -> float | None:
    """Annual gross, in EUR, needed in `country` to match the PT lifestyle."""
    econ = COUNTRIES.get(country.upper())
    if not econ:
        return None
    base_net = portugal_net(current_gross_pt)
    col_ratio = col_index_for(country, city) / COUNTRIES["PT"].col_index
    required_net = base_net * col_ratio * margin
    return required_net / econ.net_ratio


def required_gross_local(
    country: str,
    city: str | None,
    current_gross_pt: float,
    margin: float = 1.0,
) -> tuple[float, str] | None:
    """Annual gross floor expressed in the country's local currency."""
    econ = COUNTRIES.get(country.upper())
    gross_eur = required_gross_eur(country, city, current_gross_pt, margin)
    if econ is None or gross_eur is None:
        return None
    rate = EUR_PER_UNIT.get(econ.currency, 1.0)
    return gross_eur / rate, econ.currency
