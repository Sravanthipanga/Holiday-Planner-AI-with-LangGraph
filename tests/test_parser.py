"""Brief parser cases across many natural phrasings."""

from datetime import date

from holidayplanner.parser import parse_brief_rules

TODAY = date(2026, 11, 19)  # a Thursday


def parse(text):
    return parse_brief_rules(text, today=TODAY)


def test_foodie_paris_next_month():
    b = parse("Plan a 5-day foodie trip from Chicago to Paris next month, budget $2,500 for 2 people")
    assert (b.origin_iata, b.destination_iata) == ("ORD", "CDG")
    assert b.days == 5 and b.nights == 4
    assert b.start_date == date(2026, 12, 1)
    assert b.travelers == 2
    assert b.budget_usd == 2500
    assert b.vibe == "foodie"


def test_beach_long_weekend_solo_under_budget():
    b = parse("A relaxing beach long weekend in Bali under $2,000, just me")
    assert b.destination_iata == "DPS"
    assert b.days == 4
    assert b.travelers == 1
    assert b.budget_usd == 2000
    assert b.vibe == "beach"


def test_business_explicit_date_range():
    b = parse("Business trip to New York from June 3 to June 7 for a conference")
    assert b.destination_iata == "JFK"
    assert b.origin_iata == "ORD"  # default origin
    assert b.start_date == date(2027, 6, 3)
    assert b.end_date == date(2027, 6, 7)
    assert b.days == 5
    assert b.vibe == "business"


def test_week_in_tokyo_in_june_for_four():
    b = parse("Trip to Tokyo in June for 4 people, a week of adventure, around $6,000")
    assert b.destination_iata == "HND"
    assert b.days == 7
    assert b.travelers == 4
    assert b.budget_usd == 6000
    assert b.start_date == date(2027, 6, 1)
    assert b.vibe == "adventure"


def test_honeymoon_rome():
    b = parse("Romantic honeymoon in Rome, 6 days, under $3,000")
    assert b.destination_iata == "FCO"
    assert b.days == 6
    assert b.travelers == 2
    assert b.budget_usd == 3000


def test_solo_adventure_sydney():
    b = parse("Solo adventure in Sydney for 10 days")
    assert b.destination_iata == "SYD"
    assert b.travelers == 1
    assert b.days == 10
    assert b.vibe == "adventure"
    assert b.budget_usd is None


def test_weekend_getaway_default_travelers():
    b = parse("Weekend getaway to Miami from Chicago")
    assert b.destination_iata == "MIA"
    assert b.origin_iata == "ORD"
    assert b.days == 3
    assert b.travelers == 2


def test_for_three_days_is_not_three_travelers():
    b = parse("Culture trip to Berlin for three days")
    assert b.destination_iata == "BER"
    assert b.days == 3
    assert b.travelers == 2


def test_iso_dates_and_family_of():
    b = parse("Family of 4 to London from 2027-03-12 to 2027-03-15, museums and history")
    assert b.destination_iata == "LHR"
    assert b.travelers == 4
    assert b.days == 4
    assert b.start_date == date(2027, 3, 12)
    assert b.vibe == "family"  # "Family of 4" leads the request
