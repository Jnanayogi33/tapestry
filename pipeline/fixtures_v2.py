"""v2 fixture data: Places (49), Life Archetypes (36), and the column enrichments
for anchors/strands/events. Kept separate so make_fixtures.py stays readable.

Branch logic (this is the meaningful, beautiful-and-true choice): the Latin/Western
church fans UP (West), while the Orthodox East and the whole Global South fan DOWN
(East-South) — so the Great Schism and the modern Southern blaze read directly in the
Y axis. distance_km is computed objectively by haversine from Jerusalem; distance_norm
normalizes 0-100 against the farthest place.
"""
from __future__ import annotations

from pipeline import schema as S

SYN = "SYNTHETIC FIXTURE (schema-faithful placeholder; replaced by Notion sync)"

# ---------------------------------------------------------------------------------
# PLACES (49) — (name, parent_macro_region, branch, lat, lon, era_note, notes)
# ---------------------------------------------------------------------------------
PLACES = [
    # --- Core: the Levant heartland, nearest Jerusalem (y ~ center) ---
    ("Judaea", "Roman/Mediterranean", "Core", 31.78, 35.21, "AD 30 — the seed", "Jerusalem; Christ enters here. x=0, y=0.5."),
    ("Galilee", "Roman/Mediterranean", "Core", 32.80, 35.50, "1st c.", "Where the first disciples are called."),
    ("Antioch", "Roman/Mediterranean", "Core", 36.20, 36.16, "1st c.", "Believers first called 'Christians'; mission base."),
    ("Cyprus", "Roman/Mediterranean", "Core", 35.00, 33.00, "1st c.", "Barnabas & Paul's first journey."),
    ("Asia Minor (Ephesus)", "Roman/Mediterranean", "Core", 37.94, 27.34, "1st-2nd c.", "Pauline & Johannine churches."),
    # --- West: Latin Mediterranean, Europe, the Americas (fan UP) ---
    ("Rome", "Roman/Mediterranean", "West", 41.90, 12.50, "1st c.+", "Capital; Peter & Paul. Roman/Mediterranean primary place."),
    ("Carthage", "Roman/Mediterranean", "West", 36.85, 10.32, "2nd-5th c.", "Latin African church: Tertullian, Cyprian, Augustine."),
    ("Iberia (Toledo)", "Western Europe", "West", 39.86, -4.02, "4th c.+", "Visigothic & medieval Spain."),
    ("Gaul (Lyon)", "Western Europe", "West", 45.76, 4.83, "2nd c.+", "Irenaeus; the Frankish church. Western Europe primary place."),
    ("Britain (Canterbury)", "Western Europe", "West", 51.28, 1.08, "597+", "Augustine of Canterbury; English church."),
    ("Ireland (Armagh)", "Western Europe", "West", 54.35, -6.65, "5th c.", "Patrick; insular monasticism."),
    ("Germania (Mainz)", "Western Europe", "West", 50.00, 8.27, "8th c.", "Boniface, apostle of the Germans."),
    ("Scandinavia (Uppsala)", "Western Europe", "West", 59.86, 17.64, "9th-11th c.", "Anskar; late northern conversion."),
    ("Wittenberg", "Western Europe", "West", 51.87, 12.65, "1517", "Luther; the Reformation."),
    ("Geneva", "Western Europe", "West", 46.20, 6.14, "16th c.", "Calvin's reform."),
    ("New England", "North America", "West", 42.36, -71.06, "17th c.+", "Puritans; the Great Awakenings. North America primary place."),
    ("Chesapeake (Virginia)", "North America", "West", 37.54, -77.43, "17th c.+", "Anglican colonial settlement."),
    ("West Coast (Los Angeles)", "North America", "West", 34.05, -118.24, "1906", "Azusa Street; modern Pentecostalism."),
    ("Mexico (Tenochtitlan)", "Latin America", "West", 19.43, -99.13, "1524+", "Twelve Apostles of Mexico."),
    ("Bahia (Brazil)", "Latin America", "West", -12.97, -38.51, "16th c.+", "Portuguese mission. Latin America primary place."),
    ("Andes (Lima)", "Latin America", "West", -12.05, -77.04, "16th c.+", "Spanish viceregal church."),
    ("Caribbean (Hispaniola)", "Latin America", "West", 18.47, -69.90, "1492+", "First contact."),
    # --- East-South: Orthodox East, MENA, Africa, Asia, the Pacific (fan DOWN) ---
    ("Greece (Corinth)", "Roman/Mediterranean", "East-South", 37.94, 22.93, "1st c.+", "Greek-speaking churches; Orthodoxy's root."),
    ("Constantinople", "Eastern Europe & Russia", "East-South", 41.01, 28.98, "330+", "New Rome; Byzantine center."),
    ("Balkans (Thessalonica)", "Eastern Europe & Russia", "East-South", 40.64, 22.94, "9th c.", "Cyril & Methodius' mission base."),
    ("Kiev", "Eastern Europe & Russia", "East-South", 50.45, 30.52, "988", "Baptism of the Rus. Eastern Europe & Russia primary place."),
    ("Moscow", "Eastern Europe & Russia", "East-South", 55.75, 37.62, "15th c.+", "'Third Rome'; later Soviet suppression."),
    ("Armenia (Etchmiadzin)", "Middle East & North Africa", "East-South", 40.16, 44.29, "301", "First Christian state."),
    ("Alexandria", "Middle East & North Africa", "East-South", 31.20, 29.92, "1st c.+", "Mark; Athanasius; great school. MENA primary place."),
    ("Egypt (Thebaid)", "Middle East & North Africa", "East-South", 26.00, 32.00, "3rd c.+", "Desert monasticism (Anthony)."),
    ("Mesopotamia (Ctesiphon)", "Middle East & North Africa", "East-South", 33.09, 44.58, "3rd c.+", "Church of the East."),
    ("Persia (Nisibis)", "Middle East & North Africa", "East-South", 37.07, 41.21, "4th c.+", "Nestorian school of theology."),
    ("Arabia (Najran)", "Middle East & North Africa", "East-South", 17.49, 44.13, "5th-6th c.", "Pre-Islamic Christian community."),
    ("Aksum (Ethiopia)", "Sub-Saharan Africa", "East-South", 14.13, 38.72, "4th c.+", "Ethiopian church; never extinguished."),
    ("Nubia", "Sub-Saharan Africa", "East-South", 18.00, 31.00, "6th-14th c.", "Medieval Christian kingdoms."),
    ("Yorubaland (West Africa)", "Sub-Saharan Africa", "East-South", 7.38, 3.90, "19th c.+", "Crowther; explosive modern growth. Sub-Saharan Africa primary place."),
    ("Kongo", "Sub-Saharan Africa", "East-South", -6.00, 14.00, "1500+", "Kingdom of Kongo's conversion."),
    ("East Africa (Uganda)", "Sub-Saharan Africa", "East-South", 0.35, 32.58, "20th c.", "The East African Revival."),
    ("Southern Africa", "Sub-Saharan Africa", "East-South", -26.20, 28.04, "19th-20th c.", "Mission and settler churches."),
    ("Malabar Coast", "South Asia", "East-South", 9.93, 76.27, "ancient+", "Thomas Christians of Kerala. South Asia primary place."),
    ("North India (Goa)", "South Asia", "East-South", 15.50, 73.83, "16th c.+", "Xavier; de Nobili."),
    ("Ceylon", "South Asia", "East-South", 6.93, 79.85, "16th c.+", "Portuguese & later missions."),
    ("Tang Chang'an", "East Asia", "East-South", 34.27, 108.95, "635+", "Alopen; the Nestorian stele."),
    ("Shanghai (China coast)", "East Asia", "East-South", 31.23, 121.47, "19th c.+", "Protestant missions; modern house church. East Asia primary place."),
    ("Korea (Seoul)", "East Asia", "East-South", 37.57, 126.98, "19th-20th c.", "Rapid modern growth."),
    ("Japan (Nagasaki)", "East Asia", "East-South", 32.75, 129.87, "16th c.+", "Xavier; the hidden Christians."),
    ("Manila (Philippines)", "Southeast Asia", "East-South", 14.60, 120.98, "1565+", "Spanish Catholic mission. Southeast Asia primary place."),
    ("Vietnam (Tonkin)", "Southeast Asia", "East-South", 21.03, 105.85, "17th c.+", "Alexandre de Rhodes."),
    ("Java (Indonesia)", "Southeast Asia", "East-South", -6.20, 106.85, "19th-20th c.", "Dutch-era and indigenous churches."),
]

# Famous strands placed at a specific Place (otherwise region->primary place).
STRAND_PLACE_OVERRIDE = {
    "Jesus of Nazareth": "Judaea",
    "Simon Peter": "Rome",
    "Paul of Tarsus": "Antioch",
    "The Twelve Apostles": "Judaea",
    "Constantine the Great": "Constantinople",
    "Athanasius of Alexandria": "Alexandria",
    "Augustine of Hippo": "Carthage",
    "Benedict of Nursia": "Rome",
    "Gregory the Great": "Rome",
    "Cyril and Methodius": "Balkans (Thessalonica)",
    "Vladimir of Kiev": "Kiev",
    "Thomas Aquinas": "Rome",
    "Martin Luther": "Wittenberg",
    "William Tyndale": "Britain (Canterbury)",
    "John Calvin": "Geneva",
    "Ignatius of Loyola": "Rome",
    "Polycarp of Smyrna": "Asia Minor (Ephesus)",
    "Jonathan Edwards": "New England",
    "John Wesley": "Britain (Canterbury)",
    "William Carey": "Malabar Coast",
    "William J. Seymour": "West Coast (Los Angeles)",
    "Mother Teresa": "Malabar Coast",
    "Billy Graham": "New England",
    "Pope John Paul II": "Kiev",
    "Patrick of Ireland": "Ireland (Armagh)",
    "Boniface": "Germania (Mainz)",
    "Francis Xavier": "Japan (Nagasaki)",
    "Matteo Ricci": "Tang Chang'an",
    "Hudson Taylor": "Shanghai (China coast)",
    "David Livingstone": "Southern Africa",
    "Samuel Ajayi Crowther": "Yorubaland (West Africa)",
    "Alopen": "Tang Chang'an",
    "The Twelve Apostles of Mexico": "Mexico (Tenochtitlan)",
    "Adoniram Judson": "Vietnam (Tonkin)",
    "Robert Morrison": "Shanghai (China coast)",
}

# Per-year GLOBAL practicing ratio (practicing share of all Christians) — early church
# mostly practicing, modern church more nominal.
GLOBAL_PRACTICING_RATIO = {
    30: 0.95, 100: 0.92, 300: 0.88, 313: 0.85, 500: 0.70, 1000: 0.55, 1054: 0.55,
    1500: 0.50, 1517: 0.50, 1800: 0.50, 1900: 0.45, 1970: 0.40, 2000: 0.40, 2025: 0.42,
}


def build_places_rows() -> list[dict]:
    """Compute objective great-circle distances and 0-100 normalization."""
    raw = []
    for name, region, branch, lat, lon, era, notes in PLACES:
        dist = S.haversine_km(lat, lon)
        raw.append((name, region, branch, lat, lon, dist, era, notes))
    maxd = max(r[5] for r in raw) or 1.0
    rows = []
    for name, region, branch, lat, lon, dist, era, notes in raw:
        rows.append({
            "name": name,
            "parent_macro_region": region,
            "branch": branch,
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "distance_km": round(dist, 1),
            "distance_norm": round(100.0 * dist / maxd, 2),
            "era_note": era,
            "notes": notes,
        })
    return rows


# ---------------------------------------------------------------------------------
# LIFE ARCHETYPES (36) — the generative library the sim samples.
# (name, era, region, disposition, belief_path, end_state, weight, drivers, tags, summary)
# The "dark warp" never-lit archetypes carry the HIGHEST weight.
# ---------------------------------------------------------------------------------
ARCHETYPES = [
    # --- dark warp (most of humanity; never lit) ---
    ("The Unreached (antiquity)", "1st-3rd c.", "GLOBAL", "low", "Unexposed -> Unexposed", "Unaffiliated", 100,
     ["family"], ["dark warp"], "Most of humanity in antiquity never hears the gospel; the dark warp behind the light."),
    ("The Unreached (medieval)", "Medieval", "GLOBAL", "low", "Unexposed -> Unexposed", "Unaffiliated", 100,
     ["family"], ["dark warp"], "Beyond Christendom's edges, the field stays dark for a thousand years."),
    ("The Unreached (early modern)", "Early Modern", "GLOBAL", "low", "Unexposed -> Unexposed", "Unaffiliated", 92,
     ["family"], ["dark warp"], "Asia and the interior remain largely unreached before the missionary century."),
    ("Born after the conquest (MENA)", "Medieval", "Middle East & North Africa", "low", "Unexposed -> Unexposed", "Unaffiliated", 82,
     ["institution/state", "family"], ["dark warp"], "After the 7th-c. conquests the Christian East becomes a shrinking minority."),
    ("Confucian-Buddhist world (Asia)", "20th c.", "East Asia", "low", "Unexposed -> Unexposed", "Unaffiliated", 88,
     ["family", "secular culture"], ["dark warp"], "Even amid modern missions, most of East Asia remains unreached."),
    ("Hindu world (South Asia)", "20th c.", "South Asia", "low", "Unexposed -> Unexposed", "Unaffiliated", 85,
     ["family"], ["dark warp"], "Christianity stays a small minority across the subcontinent."),
    # --- antiquity believers ---
    ("Apostolic convert", "1st-3rd c.", "Roman/Mediterranean", "high", "Unexposed -> Affiliated -> Practicing", "Practicing", 8,
     ["missionary contact", "conversion experience", "social ties"], ["convert", "steady faith"],
     "Hears an apostle or a neighbor, believes, and is baptized."),
    ("Martyr of the persecutions", "1st-3rd c.", "Roman/Mediterranean", "high", "Practicing -> Martyred", "Martyred", 3,
     ["persecution", "martyrdom witness"], ["martyr", "persecuted-faithful"],
     "Refuses to recant; the blood of the martyrs becomes seed."),
    ("House-church matron", "1st-3rd c.", "Roman/Mediterranean", "high", "Affiliated -> Practicing", "Practicing", 5,
     ["family", "social ties"], ["steady faith"], "Keeps a household church; the quiet backbone of the early church."),
    # --- late antiquity ---
    ("Constantinian nominal", "4th-6th c.", "Roman/Mediterranean", "medium", "Unexposed -> Affiliated -> Nominal", "Nominal", 18,
     ["institution/state", "prosperity"], ["nominal inheritance", "convert"],
     "Joins when the faith becomes respectable; belief stays a label."),
    ("Desert ascetic", "4th-6th c.", "Middle East & North Africa", "high", "Affiliated -> Practicing", "Practicing", 4,
     ["mysticism", "conversion experience"], ["steady faith"], "Flees to the desert to seek God wholly."),
    ("Barbarian baptized with the king", "4th-6th c.", "Western Europe", "low", "Unexposed -> Affiliated -> Nominal", "Nominal", 16,
     ["institution/state", "family"], ["nominal inheritance"], "Converted top-down when the chieftain is baptized."),
    # --- medieval ---
    ("Monastic copyist", "Medieval", "Western Europe", "high", "Affiliated -> Practicing", "Practicing", 6,
     ["institution/state", "scripture/translation"], ["steady faith"], "Carries faith and letters through the dark centuries."),
    ("Medieval peasant believer", "Medieval", "Western Europe", "medium", "Affiliated -> Practicing -> Nominal", "Nominal", 26,
     ["family", "institution/state"], ["nominal inheritance", "steady faith"],
     "Born into Christendom; devout in form, ordinary in fervor."),
    ("Orthodox faithful of the Rus", "Medieval", "Eastern Europe & Russia", "medium", "Unexposed -> Affiliated -> Practicing", "Practicing", 12,
     ["institution/state", "family", "mysticism"], ["convert", "steady faith"], "Baptized with the Rus; Orthodoxy becomes the soul of a people."),
    ("Thomas Christian of Malabar", "Medieval", "South Asia", "high", "Affiliated -> Practicing", "Practicing", 4,
     ["family", "displacement/migration"], ["steady faith", "diaspora"], "An ancient church surviving on the Indian coast."),
    # --- reformation / early modern ---
    ("Reformation lay reader", "Reformation", "Western Europe", "high", "Nominal -> Practicing", "Practicing", 9,
     ["scripture/translation", "revival", "intellectual doubt"], ["revival-swept", "convert"],
     "Reads Scripture in the vernacular and finds living faith."),
    ("Recusant martyr", "Reformation", "Western Europe", "high", "Practicing -> Martyred", "Martyred", 2,
     ["persecution", "martyrdom witness"], ["martyr", "persecuted-faithful"], "Dies for confession in an age of religious war."),
    ("New World mission convert", "Early Modern", "Latin America", "medium", "Unexposed -> Affiliated -> Nominal", "Nominal", 22,
     ["missionary contact", "institution/state"], ["convert", "nominal inheritance"],
     "Baptized en masse under colonial mission; faith folk and inherited."),
    ("Hidden Christian (Japan)", "Early Modern", "East Asia", "high", "Practicing -> Practicing", "Practicing", 3,
     ["persecution", "family", "social ties"], ["underground", "persecuted-faithful"],
     "Keeps the faith in secret across generations of persecution."),
    ("Pietist of the awakening", "Early Modern", "Western Europe", "high", "Nominal -> Practicing", "Practicing", 7,
     ["revival", "social ties"], ["revival-swept", "convert"], "Heart-religion rekindled in small renewal societies."),
    ("Great-Awakening convert", "Early Modern", "North America", "high", "Nominal -> Practicing", "Practicing", 11,
     ["revival", "conversion experience"], ["revival-swept", "convert"], "Swept up in the colonial revivals."),
    # --- 19th century missions ---
    ("Mission-school pupil (Africa)", "19th c.", "Sub-Saharan Africa", "medium", "Unexposed -> Affiliated -> Practicing", "Practicing", 15,
     ["missionary contact", "scripture/translation"], ["convert"], "Learns to read Scripture at a mission school and believes."),
    ("Slave-convert of the diaspora", "19th c.", "North America", "high", "Unexposed -> Affiliated -> Practicing", "Practicing", 9,
     ["displacement/migration", "revival", "social ties"], ["convert", "diaspora", "steady faith"],
     "Finds in the gospel both hope and a community in bondage."),
    ("First reader of a new translation", "19th c.", "Sub-Saharan Africa", "high", "Unexposed -> Affiliated -> Practicing", "Practicing", 7,
     ["scripture/translation", "missionary contact"], ["convert"], "The Bible arrives in the mother tongue; the church takes root."),
    ("Colonial nominal Christian", "19th c.", "Sub-Saharan Africa", "low", "Unexposed -> Affiliated -> Nominal", "Nominal", 16,
     ["institution/state", "prosperity"], ["nominal inheritance"], "Adopts the colonizer's religion as a label."),
    # --- 20th century ---
    ("Pentecostal of Azusa", "20th c.", "North America", "high", "Nominal -> Practicing", "Practicing", 9,
     ["revival", "conversion experience", "social ties"], ["revival-swept", "convert"], "Touched by the Pentecostal outpouring."),
    ("East African revivalist", "20th c.", "Sub-Saharan Africa", "high", "Nominal -> Practicing", "Practicing", 18,
     ["revival", "social ties"], ["revival-swept"], "Confession and song turn a mission church into living faith."),
    ("Base-community Catholic", "20th c.", "Latin America", "medium", "Nominal -> Practicing", "Practicing", 20,
     ["social ties", "institution/state"], ["steady faith", "nominal inheritance"], "Faith deepened in small grassroots communities."),
    ("Soviet secret believer (Lyudmila)", "20th c.", "Eastern Europe & Russia", "medium",
     "Affiliated -> Lapsed -> Unaffiliated -> Practicing", "Practicing", 6,
     ["persecution", "family", "social ties", "mysticism"], ["returned", "frayed/declining", "persecuted-faithful"],
     "Raised under atheism, lapses, then returns late through believing ties — the Lyudmila arc."),
    ("Soviet atheist (lost faith)", "20th c.", "Eastern Europe & Russia", "low", "Affiliated -> Lapsed -> Unaffiliated", "Unaffiliated", 42,
     ["institution/state", "secular culture"], ["secularized", "lapsed", "dark warp"], "State atheism severs an inherited faith."),
    ("Chinese house-church believer", "20th c.", "East Asia", "high", "Unexposed -> Affiliated -> Practicing", "Practicing", 11,
     ["social ties", "missionary contact"], ["underground", "convert", "revival-swept"],
     "Comes to faith in a hidden church and stays despite pressure."),
    ("Korean megachurch convert", "20th c.", "East Asia", "high", "Unexposed -> Affiliated -> Practicing", "Practicing", 8,
     ["revival", "social ties", "prosperity"], ["convert", "revival-swept"], "Part of Korea's rapid 20th-c. growth."),
    ("Western nominal who drifts", "20th c.", "Western Europe", "low", "Practicing -> Nominal -> Lapsed", "Lapsed", 38,
     ["secular culture", "family"], ["frayed/declining", "secularized", "lapsed"], "Inherited faith quietly thins to nothing."),
    # --- 21st century ---
    ("Post-Christian seeker who returns", "21st c.", "North America", "medium", "Lapsed -> Unaffiliated -> Practicing", "Practicing", 6,
     ["personal crisis", "social ties", "conversion experience"], ["returned", "convert"], "After drifting, comes home through a crisis and a friend."),
    ("Global-South migrant believer", "21st c.", "GLOBAL", "high", "Practicing -> Practicing", "Practicing", 12,
     ["displacement/migration", "family"], ["diaspora", "steady faith"],
     "Carries a vibrant faith along the routes of migration."),
]


def build_archetype_rows() -> list[dict]:
    rows = []
    for (name, era, region, disp, path, end, weight, drivers, tags, summary) in ARCHETYPES:
        rows.append({
            "name": name,
            "era": era,
            "region": region,
            "start_disposition": disp,
            "belief_path": path,
            "end_state": end,
            "weight": weight,
            "drivers": S.dump_multiselect(drivers),
            "pattern_tags": S.dump_multiselect(tags),
            "summary": summary,
        })
    return rows


# ---------------------------------------------------------------------------------
# Column enrichments for existing tables.
# ---------------------------------------------------------------------------------
def enrich_global_anchor(row: dict) -> None:
    """Populate practicing/nominal/lapsed/unaffiliated for a GLOBAL anchor row so the
    four sum to ~100 and practicing+nominal+lapsed ≈ christians_pct_central."""
    year = int(row["year"])
    cpc = float(row["christians_pct_central"])
    ratio = GLOBAL_PRACTICING_RATIO.get(year, 0.45)
    practicing = cpc * ratio
    rest = max(0.0, cpc - practicing)
    nominal = rest * 0.6
    lapsed = rest - nominal
    unaffiliated = max(0.0, 100.0 - cpc)
    row["practicing_pct"] = round(practicing, 3)
    row["nominal_pct"] = round(nominal, 3)
    row["lapsed_pct"] = round(lapsed, 3)
    row["unaffiliated_pct"] = round(unaffiliated, 3)


def strand_v2_fields(name: str, primary_regions: list[str], strength: int,
                     mechanism: str) -> dict:
    """place (override or region->primary place), ignition_radius, effect_decay."""
    if name in STRAND_PLACE_OVERRIDE:
        place = STRAND_PLACE_OVERRIDE[name]
    elif mechanism == "SEED":
        place = "Judaea"
    else:
        reg = next((r for r in primary_regions if r in S.REGION_PRIMARY_PLACE), None)
        place = S.REGION_PRIMARY_PLACE.get(reg, "Rome") if reg else "Rome"
    return {
        "place": place,
        "ignition_radius": round(0.6 + 0.25 * (strength or 1), 3),
        "effect_decay": 0.15,
    }


def event_v2_fields(regions: list[str], effect: str, mechanism: str,
                    year_text: str, year_sort: float) -> dict:
    """places (text; region primary places joined), rate_effect, reach, duration_years."""
    expanded = S.expand_regions_affected(regions)
    places = "; ".join(S.REGION_PRIMARY_PLACE.get(r, "") for r in expanded if r in S.REGION_PRIMARY_PLACE)
    sign = {"Strong+": "conversion+ strong", "Mild+": "conversion+ mild", "Neutral": "neutral",
            "Mild-": "suppression- mild", "Strong-": "suppression- strong"}.get(effect, "neutral")
    rate_effect = f"{mechanism}: {sign}"
    is_global = "GLOBAL" in regions
    reach = 70 if is_global else (45 if effect in ("Strong+", "Strong-") else 30)
    # duration from a parseable year range, else default.
    import re as _re
    nums = _re.findall(r"\d{1,4}", (year_text or "").replace("present", "2025"))
    duration = 20
    if len(nums) >= 2 and int(nums[1]) > int(nums[0]):
        duration = int(nums[1]) - int(nums[0])
    return {"places": places, "rate_effect": rate_effect, "reach": reach,
            "duration_years": duration}
