"""Destination activity banks for the itinerary weaver.

Each activity has a name, an estimated per-person cost (USD, 0 = free), the
slots it suits, and the vibes it matches. Banks cover the eight cities in
the project's artwork (Paris, Tokyo, New York, London, Rome, Sydney,
Dubai, Bali); other gazetteer cities use the generic bank with the city
name woven in.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Activity:
    name: str
    cost: float
    slots: tuple[str, ...]  # subset of ("morning", "afternoon", "evening")
    vibes: tuple[str, ...]


def A(name: str, cost: float, slots: str, vibes: str) -> Activity:
    return Activity(name, cost, tuple(slots.split(",")), tuple(vibes.split(",")))


BANKS: dict[str, list[Activity]] = {
    "Paris": [
        A("Sunrise croissants at a Marais bakery crawl", 18, "morning", "foodie,culture"),
        A("Eiffel Tower summit tickets", 42, "morning,afternoon", "culture,family,adventure"),
        A("Louvre masterpieces highlights tour", 55, "morning,afternoon", "culture"),
        A("Seine river walk and bookstall browsing", 0, "afternoon,evening", "relax,culture"),
        A("Montmartre and Sacré-Cœur at golden hour", 0, "afternoon,evening", "culture,relax"),
        A("Le Marais food tour: falafel, cheese, pastries", 65, "afternoon", "foodie"),
        A("Musée d'Orsay impressionists", 24, "morning,afternoon", "culture"),
        A("French cooking class near Bastille", 95, "morning,afternoon", "foodie,family"),
        A("Canal Saint-Martin picnic with market finds", 22, "afternoon,evening", "foodie,relax"),
        A("Evening jazz cellar in the Latin Quarter", 30, "evening", "culture,relax"),
        A("Bistro dinner in Saint-Germain", 70, "evening", "foodie"),
        A("Catacombs after-dark entry", 36, "afternoon,evening", "adventure,culture"),
        A("Versailles day trip by train", 68, "morning,afternoon", "culture,family"),
        A("Père Lachaise wandering and café stop", 8, "morning,afternoon", "culture,relax"),
    ],
    "Tokyo": [
        A("Tsukiji outer market breakfast graze", 25, "morning", "foodie"),
        A("Senso-ji temple and Nakamise street at opening", 0, "morning", "culture,family"),
        A("teamLab digital art museum", 32, "morning,afternoon", "culture,family,adventure"),
        A("Shibuya crossing and Harajuku backstreets", 0, "afternoon,evening", "culture,family"),
        A("Sushi-making class in Ginza", 85, "morning,afternoon", "foodie"),
        A("Meiji Shrine and Yoyogi Park stroll", 0, "morning,afternoon", "relax,culture"),
        A("Akihabara arcades and retro game shops", 20, "afternoon,evening", "family,adventure"),
        A("Izakaya alley dinner in Shinjuku", 45, "evening", "foodie"),
        A("Day trip to Mt. Takao for hiking", 28, "morning,afternoon", "adventure"),
        A("Tokyo Skytree at sunset", 30, "afternoon,evening", "family,culture"),
        A("Onsen soak in Odaiba", 26, "evening", "relax"),
        A("Ramen tasting crawl in Nakameguro", 35, "evening", "foodie"),
        A("Imperial Palace East Gardens", 0, "morning,afternoon", "culture,relax"),
        A("Sumo morning practice viewing (seasonal)", 40, "morning", "culture,adventure"),
    ],
    "New York": [
        A("Bagels and coffee in the West Village", 16, "morning", "foodie"),
        A("Statue of Liberty and Ellis Island ferry", 32, "morning,afternoon", "culture,family"),
        A("The Met's greatest-hits route", 30, "morning,afternoon", "culture"),
        A("Central Park rowboats and Bethesda Terrace", 20, "afternoon", "relax,family"),
        A("Brooklyn Bridge walk at golden hour", 0, "afternoon,evening", "culture,relax,adventure"),
        A("Chinatown and Little Italy food crawl", 38, "afternoon,evening", "foodie"),
        A("Top of the Rock at sunset", 44, "evening", "family,culture"),
        A("Broadway show (rush tickets)", 79, "evening", "culture"),
        A("Chelsea Market and the High Line", 15, "morning,afternoon", "foodie,culture"),
        A("Harlem gospel brunch", 42, "morning", "foodie,culture"),
        A("Kayaking the Hudson (seasonal, free)", 0, "morning,afternoon", "adventure"),
        A("MoMA late-night Friday entry", 30, "evening", "culture"),
        A("Coney Island boardwalk and hot dogs", 24, "afternoon", "family,beach,foodie"),
        A("Greenwich Village jazz club set", 35, "evening", "culture,relax"),
    ],
    "London": [
        A("Borough Market breakfast wander", 20, "morning", "foodie"),
        A("Tower of London and Crown Jewels", 38, "morning,afternoon", "culture,family"),
        A("British Museum highlights", 0, "morning,afternoon", "culture,family"),
        A("Thames walk: Southbank to Tower Bridge", 0, "afternoon,evening", "relax,culture"),
        A("West End matinee", 55, "afternoon,evening", "culture"),
        A("Camden Market and canal towpath", 12, "afternoon", "culture,adventure"),
        A("Afternoon tea in Bloomsbury", 48, "afternoon", "foodie,relax"),
        A("Sky Garden free viewpoint at sunset", 0, "evening", "relax,culture"),
        A("Brick Lane curry house dinner", 32, "evening", "foodie"),
        A("Greenwich: observatory and market", 22, "morning,afternoon", "culture,family"),
        A("Hyde Park and Kensington Gardens ramble", 0, "morning,afternoon", "relax,family"),
        A("Pub quiz night in Shoreditch", 18, "evening", "relax,culture"),
        A("Hampstead Heath and Parliament Hill view", 0, "morning,afternoon", "adventure,relax"),
        A("Street-food night market in Peckham", 26, "evening", "foodie,adventure"),
    ],
    "Rome": [
        A("Espresso and cornetto at a Trastevere bar", 9, "morning", "foodie,relax"),
        A("Colosseum and Roman Forum entry", 34, "morning,afternoon", "culture,family"),
        A("Vatican Museums and Sistine Chapel", 42, "morning,afternoon", "culture"),
        A("Pantheon and Piazza Navona wander", 0, "morning,afternoon,evening", "culture,relax"),
        A("Pasta-making class near Campo de' Fiori", 78, "morning,afternoon", "foodie,family"),
        A("Trastevere golden-hour aperitivo", 18, "evening", "foodie,relax"),
        A("Appian Way e-bike ride", 45, "morning,afternoon", "adventure"),
        A("Borghese Gallery and gardens", 25, "afternoon", "culture,relax"),
        A("Testaccio market food tour", 52, "morning,afternoon", "foodie"),
        A("Trevi Fountain and Spanish Steps after dark", 0, "evening", "culture,relax"),
        A("Catacombs of San Callisto", 16, "afternoon", "culture,adventure"),
        A("Carbonara pilgrimage dinner in Monti", 38, "evening", "foodie"),
        A("Day trip to Ostia Antica ruins", 20, "morning,afternoon", "culture,adventure"),
        A("Gelato tasting crawl: three classic shops", 14, "afternoon,evening", "foodie,family"),
    ],
    "Sydney": [
        A("Harbour sunrise walk at Mrs Macquarie's Point", 0, "morning", "relax,culture"),
        A("Sydney Opera House tour", 33, "morning,afternoon", "culture,family"),
        A("Bondi to Coogee coastal walk", 0, "morning,afternoon", "beach,adventure,relax"),
        A("Ferry to Manly and beach afternoon", 12, "afternoon", "beach,family"),
        A("The Rocks markets and oldest pubs", 15, "afternoon,evening", "culture,foodie"),
        A("BridgeClimb at twilight", 190, "evening", "adventure"),
        A("Surry Hills café and gallery crawl", 18, "morning,afternoon", "foodie,culture"),
        A("Blue Mountains day trip: Katoomba and the Three Sisters", 65, "morning,afternoon", "adventure,family"),
        A("Harbour kayak at dawn", 55, "morning", "adventure"),
        A("Seafood dinner at Circular Quay", 60, "evening", "foodie"),
        A("Royal Botanic Garden picnic", 10, "afternoon", "relax,family"),
        A("Surf lesson at Bondi", 70, "morning", "beach,adventure"),
        A("Barangaroo sunset drinks", 22, "evening", "relax"),
        A("Taronga Zoo by ferry", 38, "morning,afternoon", "family"),
    ],
    "Dubai": [
        A("Old Dubai: abra ride across the Creek", 5, "morning", "culture,adventure"),
        A("Gold and Spice Souks with a local guide", 20, "morning,afternoon", "culture"),
        A("Burj Khalifa At The Top (124th floor)", 55, "afternoon,evening", "family,culture"),
        A("Desert safari with dune drive and dinner", 85, "afternoon,evening", "adventure,family"),
        A("Jumeirah Beach and Kite Beach afternoon", 0, "afternoon", "beach,relax"),
        A("Dubai Mall and fountain show at night", 0, "evening", "family,culture"),
        A("Al Fahidi historic quarter and coffee museum", 10, "morning,afternoon", "culture"),
        A("Palm Jumeirah monorail and Atlantis views", 18, "afternoon", "culture,family"),
        A("Emirati breakfast in Deira", 16, "morning", "foodie"),
        A("Marina dhow dinner cruise", 60, "evening", "foodie,relax"),
        A("Miracle Garden (seasonal)", 27, "morning,afternoon", "family,relax"),
        A("Ski Dubai indoor slopes", 68, "afternoon", "adventure,family"),
        A("Global Village evening (seasonal)", 8, "evening", "foodie,culture,family"),
        A("Sunset yacht tour from Dubai Marina", 75, "evening", "relax,adventure"),
    ],
    "Bali": [
        A("Sunrise at Tegalalang rice terraces", 6, "morning", "adventure,culture"),
        A("Ubud Monkey Forest and palace walk", 8, "morning,afternoon", "family,culture"),
        A("Balinese cooking class with market visit", 38, "morning", "foodie"),
        A("Mount Batur sunrise trek", 55, "morning", "adventure"),
        A("Spa and flower bath in Ubud", 30, "afternoon,evening", "relax"),
        A("Uluwatu Temple and kecak fire dance at sunset", 14, "evening", "culture"),
        A("Seminyak beach clubs and sunset", 20, "afternoon,evening", "beach,relax"),
        A("Snorkeling trip to Nusa Penida", 65, "morning,afternoon", "beach,adventure"),
        A("Waterfall hop: Tibumana and Tegenungan", 12, "morning,afternoon", "adventure,relax"),
        A("Warung dinner crawl in Denpasar", 15, "evening", "foodie"),
        A("Yoga at sunrise in a jungle shala", 12, "morning", "relax"),
        A("Surf lesson in Canggu", 28, "morning,afternoon", "beach,adventure"),
        A("Tirta Empul water purification temple", 10, "morning", "culture,relax"),
        A("Night market snacks in Gianyar", 9, "evening", "foodie,adventure"),
    ],
}


def generic_bank(city_name: str) -> list[Activity]:
    return [
        A(f"Old Town walking tour of {city_name}", 25, "morning,afternoon", "culture"),
        A(f"{city_name} history museum", 18, "morning,afternoon", "culture,family"),
        A("Central market food graze", 20, "morning,afternoon", "foodie"),
        A("Riverside / main park stroll", 0, "afternoon,evening", "relax"),
        A("Neighborhood café crawl", 14, "morning,afternoon", "foodie,relax"),
        A("Viewpoint at golden hour", 0, "evening", "relax,culture"),
        A("Local cooking class", 60, "morning,afternoon", "foodie,family"),
        A("Day hike on the city-edge trails", 10, "morning,afternoon", "adventure"),
        A("Street-food dinner in the old quarter", 28, "evening", "foodie"),
        A("Live music at a local venue", 22, "evening", "culture"),
        A("Farmers market and picnic supplies", 16, "morning", "foodie,family"),
        A("Bike rental: river path loop", 19, "morning,afternoon", "adventure,family"),
    ]


def bank_for(destination: str) -> list[Activity]:
    return BANKS.get(destination) or generic_bank(destination)
