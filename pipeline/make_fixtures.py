"""Generate synthetic fixtures that match the Knowledge Base schema EXACTLY.

The fixtures are plausible (so calibration and the visualization are meaningful even
before real Notion data exists) but clearly labeled synthetic. They reproduce the
real-world realities downstream code must survive:
  * percents as PERCENTAGE POINTS (34.5 == 34.5%), counts as PERSONS;
  * all 14 GLOBAL anchor rows + the exact sparse 40-cell regional coverage pattern;
  * valid enums; JSON-array multi-selects;
  * >= 1 BC (negative) birth_year and >= 1 strand with regions_affected == ["GLOBAL"];
  * exactly 25 / 40 / 35 strands across Tier 1 / 2 / 3;
  * a lives.csv with >= 6 profiles, one encoding affiliated -> unbelieving ->
    strongly-practicing (the "Lyudmila" arc).

Run: python pipeline/make_fixtures.py
"""
from __future__ import annotations

import csv
import os
import sys
from typing import Iterable

# Allow running as `python pipeline/make_fixtures.py` (not just `-m pipeline...`).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import schema as S  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

SYN = "SYNTHETIC FIXTURE (schema-faithful placeholder; replaced by Notion sync)"
SYN_URL = "https://example.invalid/tapestry-fixture"


# ----------------------------------------------------------------------------------
# REGIONS
# ----------------------------------------------------------------------------------
REGION_DEFS = {
    "Roman/Mediterranean": (
        "The classical Mediterranean world of the Roman Empire: Italy, Greece, "
        "Anatolia, the Levant, Egypt and Roman North Africa.",
        "Antiquity-only category. Before ~640 AD the Levant/Egypt/N.-Africa Christians "
        "are counted HERE, not under Middle East & North Africa (double-count rule).",
    ),
    "Western Europe": (
        "Latin/Western Christendom: British Isles, France, Iberia, Italy, the Low "
        "Countries, German-speaking lands, Scandinavia.",
        "Apportioned split from the source's combined 'Europe' (confidence Low).",
    ),
    "Eastern Europe & Russia": (
        "Byzantine and Slavic Orthodox world: the Balkans, Greece, Russia, Ukraine, "
        "Belarus and the eastern Slavic lands.",
        "Apportioned split from the source's combined 'Europe' (confidence Low).",
    ),
    "Middle East & North Africa": (
        "Modern MENA: the Arabian peninsula, the Levant, Mesopotamia, Iran, Egypt and "
        "the Maghreb.",
        "Independent series intentionally STARTS at year 1000 to avoid double-counting "
        "with Roman/Mediterranean in antiquity.",
    ),
    "Sub-Saharan Africa": (
        "Africa south of the Sahara, including the Horn and southern Africa.",
        "Ethiopian/Nubian Christianity predates 1900 but the series is anchored from "
        "1900 where data is firm.",
    ),
    "South Asia": (
        "The Indian subcontinent: India, Pakistan, Bangladesh, Sri Lanka, Nepal.",
        "Includes the ancient Thomas-Christian communities of Kerala.",
    ),
    "East Asia": (
        "China, Japan, Korea, Mongolia and Taiwan.",
        "Anchored at 1900 and 2025; intermediate cells deferred to Phase 2.",
    ),
    "Southeast Asia": (
        "Mainland and maritime SE Asia: Indochina, Thailand, Myanmar, the Philippines, "
        "Indonesia, Malaysia.",
        "The Philippines dominates the Christian share.",
    ),
    "Latin America": (
        "Mexico, Central America, the Caribbean and South America.",
        "Series anchored from 1900; mission-era detail (1492-1600) carried by strands.",
    ),
    "North America": (
        "The United States and Canada.",
        "Series anchored from 1900.",
    ),
}


def build_regions_rows() -> list[dict]:
    rows = []
    for name in S.REGIONS:
        definition, boundary = REGION_DEFS[name]
        rows.append(
            {"Name": name, "Modern Definition": definition, "Boundary Notes": boundary}
        )
    return rows


# ----------------------------------------------------------------------------------
# ANCHORS — 14 GLOBAL rows + 40 sparse regional rows
# ----------------------------------------------------------------------------------
# (year, christians_central persons, total_population persons). Roughly CSGC-shaped.
GLOBAL_ANCHORS = {
    30:   (1_000,          170_000_000),
    100:  (800_000,        195_000_000),
    300:  (6_000_000,      190_000_000),
    313:  (7_000_000,      190_000_000),
    500:  (24_000_000,     193_000_000),
    1000: (56_000_000,     275_000_000),
    1054: (60_000_000,     280_000_000),
    1500: (90_000_000,     440_000_000),
    1517: (93_000_000,     445_000_000),
    1800: (210_000_000,    900_000_000),
    1900: (558_000_000,    1_620_000_000),
    1970: (1_230_000_000,  3_700_000_000),
    2000: (1_990_000_000,  6_120_000_000),
    2025: (2_580_000_000,  8_100_000_000),
}

# Regional christians_central (persons) and total_population (persons) for the 40
# covered cells. Roman/Mediterranean carries antiquity; others anchor from 1900
# (MENA/Europe from 1000). Sums at 1900 & 2025 are kept within 15% of GLOBAL.
# Format: region -> {year: (christians_central, total_population, practicing_pct|None)}
REGIONAL_ANCHORS: dict[str, dict[int, tuple[int, int, float | None]]] = {
    "Roman/Mediterranean": {
        30:   (900,        60_000_000,  None),
        100:  (700_000,    60_000_000,  None),
        300:  (5_500_000,  57_000_000,  None),
        313:  (6_400_000,  57_000_000,  None),
        500:  (21_000_000, 50_000_000,  None),
    },
    "Western Europe": {
        1000: (28_000_000, 38_000_000,  None),
        1500: (57_000_000, 70_000_000,  None),
        1900: (190_000_000, 270_000_000, None),
        1970: (340_000_000, 430_000_000, 18.0),
        2000: (300_000_000, 490_000_000, 12.0),
        2025: (255_000_000, 500_000_000, 9.0),
    },
    "Eastern Europe & Russia": {
        1000: (18_000_000, 30_000_000,  None),
        1900: (160_000_000, 200_000_000, None),
        1970: (130_000_000, 360_000_000, 6.0),
        2000: (215_000_000, 340_000_000, 7.0),
        2025: (250_000_000, 340_000_000, 8.0),
    },
    "Middle East & North Africa": {
        1000: (6_000_000,  35_000_000,  None),
        1500: (3_000_000,  30_000_000,  None),
        1900: (11_000_000, 45_000_000,  None),
        1970: (12_000_000, 130_000_000, None),
        2000: (13_000_000, 300_000_000, None),
        2025: (15_000_000, 500_000_000, None),
    },
    "Sub-Saharan Africa": {
        1900: (9_000_000,   95_000_000,  None),
        1970: (140_000_000, 290_000_000, None),
        2000: (380_000_000, 670_000_000, None),
        2025: (700_000_000, 1_200_000_000, None),
    },
    "Latin America": {
        1900: (62_000_000,  65_000_000,  None),
        1970: (270_000_000, 285_000_000, None),
        2000: (470_000_000, 520_000_000, None),
        2025: (600_000_000, 660_000_000, None),
    },
    "North America": {
        1900: (79_000_000,  82_000_000,  None),
        1970: (210_000_000, 230_000_000, 45.0),
        2000: (250_000_000, 310_000_000, 38.0),
        2025: (270_000_000, 375_000_000, 31.0),
    },
    "South Asia": {
        1900: (5_000_000,   290_000_000, None),
        2025: (70_000_000,  1_950_000_000, None),
    },
    "East Asia": {
        1900: (2_000_000,   450_000_000, None),
        2025: (120_000_000, 1_600_000_000, None),
    },
    "Southeast Asia": {
        1900: (3_000_000,   80_000_000,  None),
        2025: (160_000_000, 690_000_000, None),
    },
}

CONFIDENCE_BY_YEAR = {
    30: "Speculative", 100: "Speculative", 300: "Low", 313: "Low", 500: "Low",
    1000: "Low", 1054: "Low", 1500: "Medium", 1517: "Medium", 1800: "Medium",
    1900: "High", 1970: "High", 2000: "High", 2025: "High",
}


def _band(central: int, conf: str) -> tuple[int, int]:
    """Return (low, high) around central, wider for softer confidence."""
    spread = {"High": 0.06, "Medium": 0.12, "Low": 0.25, "Speculative": 0.5}.get(conf, 0.2)
    low = int(round(central * (1 - spread)))
    high = int(round(central * (1 + spread)))
    return max(0, low), high


def build_anchor_rows() -> list[dict]:
    rows: list[dict] = []
    # 14 GLOBAL rows.
    for year in S.ANCHOR_YEARS:
        central, pop = GLOBAL_ANCHORS[year]
        conf = CONFIDENCE_BY_YEAR[year]
        low, high = _band(central, conf)
        pct = round(100.0 * central / pop, 3)
        rows.append({
            "label": f"GLOBAL — {year}",
            "region": S.GLOBAL,
            "year": year,
            "christians_low": low,
            "christians_central": central,
            "christians_high": high,
            "total_population": pop,
            "christians_pct_central": pct,
            "practicing_pct": "",
            "source": SYN,
            "source_url": SYN_URL,
            "confidence": conf,
            "notes": "Global total across all regions.",
        })
    # 40 regional rows, only for covered cells.
    for region, year_map in REGIONAL_ANCHORS.items():
        for year in S.REGIONAL_COVERAGE[region]:
            central, pop, practicing = year_map[year]
            conf = CONFIDENCE_BY_YEAR[year]
            # Europe split is explicitly soft.
            if region in ("Western Europe", "Eastern Europe & Russia") and year <= 1517:
                conf = "Low"
            low, high = _band(central, conf)
            pct = round(100.0 * central / pop, 3)
            rows.append({
                "label": f"{region} — {year}",
                "region": region,
                "year": year,
                "christians_low": low,
                "christians_central": central,
                "christians_high": high,
                "total_population": pop,
                "christians_pct_central": pct,
                "practicing_pct": "" if practicing is None else practicing,
                "source": SYN,
                "source_url": SYN_URL,
                "confidence": conf,
                "notes": (
                    "Pre-640 Levant/Egypt/N.-Africa counted here, not under MENA."
                    if region == "Roman/Mediterranean" else
                    "Apportioned Europe split (soft)."
                    if region in ("Western Europe", "Eastern Europe & Russia") and year <= 1517
                    else ""
                ),
            })
    return rows


# ----------------------------------------------------------------------------------
# EVENTS — 21 rows
# ----------------------------------------------------------------------------------
# (Event Name, year_text, year_sort, [regions], effect, mechanism, description)
EVENTS = [
    ("Pentecost", "33", 33, ["Roman/Mediterranean", "GLOBAL"], "Strong+", "conversion",
     "The Spirit falls on the first disciples in Jerusalem; the church is born and the first thousands believe."),
    ("Neronian Persecution", "64", 64, ["Roman/Mediterranean"], "Mild-", "persecution",
     "After the Great Fire of Rome, Nero scapegoats and executes Christians; Peter and Paul are traditionally martyred."),
    ("Destruction of the Second Temple", "70", 70, ["Roman/Mediterranean", "Middle East & North Africa"], "Mild-", "schism",
     "Rome razes Jerusalem's temple; the church and synagogue decisively part ways."),
    ("Edict of Milan", "313", 313, ["Roman/Mediterranean"], "Strong+", "conversion",
     "Constantine and Licinius legalize Christianity across the empire, ending state persecution."),
    ("First Council of Nicaea", "325", 325, ["Roman/Mediterranean"], "Mild+", "schism",
     "The first ecumenical council defines the divinity of Christ against Arianism and sets the Nicene Creed."),
    ("Christianity made the state religion", "380", 380, ["Roman/Mediterranean"], "Strong+", "conversion",
     "Theodosius I's Edict of Thessalonica makes Nicene Christianity the official religion of the empire."),
    ("Council of Chalcedon", "451", 451, ["Roman/Mediterranean", "Middle East & North Africa"], "Mild-", "schism",
     "Defines the two natures of Christ; the Oriental Orthodox churches separate over its formula."),
    ("Fall of Western Rome", "476", 476, ["Western Europe", "Roman/Mediterranean"], "Neutral", "conversion",
     "The Western empire collapses; monasteries become the arks that carry literacy and faith through the upheaval."),
    ("Gregorian mission to England", "596", 596, ["Western Europe"], "Mild+", "conversion",
     "Gregory the Great sends Augustine of Canterbury to the Anglo-Saxons, beginning England's conversion."),
    ("Islamic conquests of the Christian East", "634–750 (7th–8th c.)", 700,
     ["Middle East & North Africa", "Roman/Mediterranean"], "Strong-", "persecution",
     "The Levant, Egypt and North Africa pass under Muslim rule; over centuries these heartlands become majority-Muslim."),
    ("Conversion of Kievan Rus", "988", 988, ["Eastern Europe & Russia"], "Strong+", "conversion",
     "Vladimir of Kiev is baptized and the Rus adopt Byzantine Christianity, seeding Russian Orthodoxy."),
    ("Great Schism", "1054", 1054, ["Eastern Europe & Russia", "Roman/Mediterranean", "Western Europe"], "Mild-", "schism",
     "Mutual excommunications formalize the split between the Latin West and the Greek East."),
    ("Fall of Constantinople", "1453", 1453, ["Eastern Europe & Russia", "Middle East & North Africa"], "Mild-", "persecution",
     "The Ottomans take Constantinople; Byzantine Christianity ends as a state and Orthodoxy's center shifts to Moscow."),
    ("Protestant Reformation", "1517", 1517, ["Western Europe"], "Mild+", "schism",
     "Luther's Ninety-five Theses ignite a movement that splits Western Christendom and renews lay devotion."),
    ("Mission to the Americas", "1492–1600", 1500, ["Latin America", "North America"], "Strong+", "conversion",
     "European contact and Catholic missions bring large-scale (and often coerced) conversion across the New World."),
    ("Vernacular Bible printing", "1534–1611", 1550, ["Western Europe"], "Strong+", "translation",
     "Luther's German Bible and the King James Version put Scripture into the hands of ordinary readers."),
    ("Peace of Westphalia", "1648", 1648, ["Western Europe"], "Neutral", "secularization",
     "Ends the Wars of Religion with a confessional settlement, beginning the long separation of church and state."),
    ("Great Awakenings", "1730–1860", 1790, ["North America", "Western Europe"], "Strong+", "revival",
     "Waves of evangelical revival sweep the English-speaking world, reshaping personal faith and reform movements."),
    ("Modern Missionary Movement", "1792–1910", 1850,
     ["Sub-Saharan Africa", "South Asia", "East Asia", "Southeast Asia"], "Strong+", "conversion",
     "Protestant and Catholic missions plant churches across Africa and Asia; translation and schools follow."),
    ("Soviet state atheism", "1917–1991", 1950, ["Eastern Europe & Russia"], "Strong-", "persecution",
     "The USSR enforces militant atheism — closed churches, imprisoned clergy — yet faith survives underground."),
    ("Western secularization", "1960–present", 1980, ["Western Europe", "North America"], "Strong-", "secularization",
     "Across the post-war West, affiliation and practice decline sharply as societies grow secular."),
]


def build_event_rows() -> list[dict]:
    rows = []
    for name, ytext, ysort, regions, effect, mech, desc in EVENTS:
        rows.append({
            "Event Name": name,
            "year": ytext,
            "year_sort": ysort,
            "regions": S.dump_multiselect(regions),
            "description": desc,
            "effect": effect,
            "mechanism": mech,
            "source": SYN,
            "source_url": SYN_URL,
        })
    return rows


# ----------------------------------------------------------------------------------
# STRANDS — curated real figures, padded with labeled filler to 25 / 40 / 35.
# Tuple: (name, birth, death, [primary_region], role, mechanism_template,
#         [regions_affected], window_start, window_end, strength, confidence)
# birth/death None == null (BC is negative).
# ----------------------------------------------------------------------------------
G = ["GLOBAL"]
TIER1 = [
    ("Jesus of Nazareth", -4, 30, ["Roman/Mediterranean"], "The origin of the faith", "SEED", G, 30, 33, 5, "High"),
    ("Simon Peter", 1, 64, ["Roman/Mediterranean"], "Apostle, leader of the Twelve", "APOSTOLIC_PROPAGATION", ["Roman/Mediterranean", "Western Europe"], 30, 64, 5, "High"),
    ("Paul of Tarsus", 5, 65, ["Roman/Mediterranean"], "Apostle to the Gentiles", "APOSTOLIC_PROPAGATION", ["Roman/Mediterranean", "Western Europe", "Eastern Europe & Russia"], 46, 65, 5, "High"),
    ("The Twelve Apostles", None, None, ["Roman/Mediterranean", "Middle East & North Africa"], "The first missionary band", "APOSTOLIC_PROPAGATION", ["Roman/Mediterranean", "Middle East & North Africa", "South Asia"], 30, 80, 4, "Medium"),
    ("Constantine the Great", 272, 337, ["Roman/Mediterranean"], "Emperor who legalized the faith", "INSTITUTIONAL", ["Roman/Mediterranean"], 312, 337, 5, "High"),
    ("Athanasius of Alexandria", 296, 373, ["Middle East & North Africa"], "Defender of Nicene orthodoxy", "THEOLOGICAL", ["Roman/Mediterranean"], 328, 373, 4, "High"),
    ("Augustine of Hippo", 354, 430, ["Middle East & North Africa", "Roman/Mediterranean"], "Theologian of grace", "THEOLOGICAL", ["Roman/Mediterranean", "Western Europe"], 387, 430, 5, "High"),
    ("Benedict of Nursia", 480, 547, ["Western Europe"], "Father of Western monasticism", "INSTITUTIONAL", ["Western Europe"], 529, 547, 4, "High"),
    ("Gregory the Great", 540, 604, ["Western Europe"], "Pope who sent missions north", "INSTITUTIONAL", ["Western Europe"], 590, 604, 4, "High"),
    ("Cyril and Methodius", 826, 885, ["Eastern Europe & Russia"], "Apostles to the Slavs", "TRANSLATION", ["Eastern Europe & Russia"], 863, 885, 5, "High"),
    ("Vladimir of Kiev", 958, 1015, ["Eastern Europe & Russia"], "Baptizer of the Rus", "INSTITUTIONAL", ["Eastern Europe & Russia"], 988, 1015, 4, "High"),
    ("Thomas Aquinas", 1225, 1274, ["Western Europe"], "Synthesizer of faith and reason", "THEOLOGICAL", ["Western Europe"], 1265, 1274, 4, "High"),
    ("Martin Luther", 1483, 1546, ["Western Europe"], "Reformer; sola fide, sola scriptura", "THEOLOGICAL", ["Western Europe"], 1517, 1546, 5, "High"),
    ("William Tyndale", 1494, 1536, ["Western Europe"], "Translator of the English Bible", "TRANSLATION", ["Western Europe", "North America"], 1525, 1536, 4, "High"),
    ("John Calvin", 1509, 1564, ["Western Europe"], "Reformer of Geneva", "THEOLOGICAL", ["Western Europe", "North America"], 1536, 1564, 4, "High"),
    ("Ignatius of Loyola", 1491, 1556, ["Western Europe"], "Founder of the Jesuits", "INSTITUTIONAL", G, 1540, 1556, 5, "High"),
    ("Polycarp of Smyrna", 69, 155, ["Roman/Mediterranean"], "Bishop and martyr", "MARTYRDOM", ["Roman/Mediterranean"], 155, 156, 4, "High"),
    ("Jonathan Edwards", 1703, 1758, ["North America"], "Preacher of the Great Awakening", "REVIVAL", ["North America"], 1734, 1758, 4, "High"),
    ("John Wesley", 1703, 1791, ["Western Europe", "North America"], "Founder of Methodism", "REVIVAL", ["Western Europe", "North America"], 1738, 1791, 5, "High"),
    ("Count Zinzendorf", 1700, 1760, ["Western Europe"], "Leader of the Moravian missions", "REVIVAL", G, 1727, 1760, 4, "High"),
    ("William Carey", 1761, 1834, ["South Asia"], "Father of modern missions", "TRANSLATION", ["South Asia"], 1793, 1834, 4, "High"),
    ("William J. Seymour", 1870, 1922, ["North America"], "Leader of the Azusa Street Revival", "REVIVAL", G, 1906, 1922, 5, "High"),
    ("Mother Teresa", 1910, 1997, ["South Asia"], "Servant of the poorest", "INSTITUTIONAL", G, 1950, 1997, 4, "High"),
    ("Billy Graham", 1918, 2018, ["North America"], "Evangelist to the nations", "REVIVAL", G, 1949, 2005, 5, "High"),
    ("Pope John Paul II", 1920, 2005, ["Eastern Europe & Russia"], "Pope of the global church", "INSTITUTIONAL", G, 1978, 2005, 5, "High"),
]

TIER2 = [
    ("Justin Martyr", 100, 165, ["Roman/Mediterranean"], "Philosopher-apologist", "THEOLOGICAL", ["Roman/Mediterranean"], 150, 165, 3, "Medium"),
    ("Irenaeus of Lyons", 130, 202, ["Western Europe", "Roman/Mediterranean"], "Opponent of Gnosticism", "THEOLOGICAL", ["Western Europe"], 180, 202, 3, "Medium"),
    ("Origen of Alexandria", 184, 253, ["Middle East & North Africa"], "Biblical scholar", "THEOLOGICAL", ["Roman/Mediterranean"], 220, 253, 3, "Medium"),
    ("Perpetua and Felicity", 181, 203, ["Middle East & North Africa"], "Martyrs of Carthage", "MARTYRDOM", ["Roman/Mediterranean", "Middle East & North Africa"], 203, 204, 3, "Medium"),
    ("Diocletian", 244, 311, ["Roman/Mediterranean"], "Emperor of the Great Persecution", "SUPPRESSION", ["Roman/Mediterranean"], 303, 311, 4, "High"),
    ("Anthony the Great", 251, 356, ["Middle East & North Africa"], "Father of desert monasticism", "INSTITUTIONAL", ["Middle East & North Africa"], 270, 356, 3, "Medium"),
    ("Jerome", 342, 420, ["Roman/Mediterranean"], "Translator of the Latin Vulgate", "TRANSLATION", ["Western Europe"], 382, 420, 4, "High"),
    ("John Chrysostom", 349, 407, ["Eastern Europe & Russia", "Middle East & North Africa"], "Golden-mouthed preacher", "THEOLOGICAL", ["Roman/Mediterranean"], 386, 407, 3, "Medium"),
    ("Patrick of Ireland", 385, 461, ["Western Europe"], "Apostle of Ireland", "APOSTOLIC_PROPAGATION", ["Western Europe"], 432, 461, 4, "Medium"),
    ("Columba", 521, 597, ["Western Europe"], "Missionary of Iona", "APOSTOLIC_PROPAGATION", ["Western Europe"], 563, 597, 3, "Medium"),
    ("Alopen", None, None, ["East Asia"], "First missionary to China (Nestorian)", "APOSTOLIC_PROPAGATION", ["East Asia"], 635, 650, 3, "Low"),
    ("Boniface", 675, 754, ["Western Europe"], "Apostle of the Germans", "APOSTOLIC_PROPAGATION", ["Western Europe"], 716, 754, 4, "Medium"),
    ("Charlemagne", 748, 814, ["Western Europe"], "Emperor who Christianized by sword and school", "INSTITUTIONAL", ["Western Europe"], 768, 814, 4, "High"),
    ("Anselm of Canterbury", 1033, 1109, ["Western Europe"], "Father of scholasticism", "THEOLOGICAL", ["Western Europe"], 1078, 1109, 3, "Medium"),
    ("Francis of Assisi", 1181, 1226, ["Western Europe"], "Reformer of poverty and joy", "REVIVAL", ["Western Europe"], 1209, 1226, 4, "High"),
    ("Dominic de Guzmán", 1170, 1221, ["Western Europe"], "Founder of the Order of Preachers", "INSTITUTIONAL", ["Western Europe"], 1216, 1221, 3, "Medium"),
    ("John Wycliffe", 1328, 1384, ["Western Europe"], "Morning star of the Reformation", "TRANSLATION", ["Western Europe"], 1382, 1384, 3, "Medium"),
    ("Jan Hus", 1369, 1415, ["Eastern Europe & Russia"], "Bohemian reformer and martyr", "MARTYRDOM", ["Eastern Europe & Russia"], 1402, 1415, 3, "Medium"),
    ("Erasmus of Rotterdam", 1466, 1536, ["Western Europe"], "Editor of the Greek New Testament", "TRANSLATION", ["Western Europe"], 1516, 1536, 3, "High"),
    ("Ulrich Zwingli", 1484, 1531, ["Western Europe"], "Reformer of Zürich", "THEOLOGICAL", ["Western Europe"], 1519, 1531, 3, "Medium"),
    ("Thomas Cranmer", 1489, 1556, ["Western Europe"], "Architect of the English Prayer Book", "INSTITUTIONAL", ["Western Europe"], 1533, 1556, 3, "Medium"),
    ("Teresa of Ávila", 1515, 1582, ["Western Europe"], "Mystic and reformer of Carmel", "REVIVAL", ["Western Europe"], 1560, 1582, 3, "Medium"),
    ("Francis Xavier", 1506, 1552, ["East Asia", "Southeast Asia", "South Asia"], "Apostle of the East Indies", "APOSTOLIC_PROPAGATION", ["East Asia", "Southeast Asia", "South Asia"], 1541, 1552, 4, "High"),
    ("The Twelve Apostles of Mexico", None, None, ["Latin America"], "Franciscan founders of the Mexican church", "APOSTOLIC_PROPAGATION", ["Latin America"], 1524, 1560, 4, "Medium"),
    ("Bartolomé de las Casas", 1484, 1566, ["Latin America"], "Defender of the indigenous", "INSTITUTIONAL", ["Latin America"], 1514, 1566, 3, "High"),
    ("Matteo Ricci", 1552, 1610, ["East Asia"], "Jesuit bridge to China", "APOSTOLIC_PROPAGATION", ["East Asia"], 1582, 1610, 3, "Medium"),
    ("John Knox", 1514, 1572, ["Western Europe"], "Reformer of Scotland", "THEOLOGICAL", ["Western Europe"], 1559, 1572, 3, "Medium"),
    ("George Whitefield", 1714, 1770, ["North America", "Western Europe"], "Itinerant of the Awakening", "REVIVAL", ["North America", "Western Europe"], 1740, 1770, 4, "High"),
    ("David Brainerd", 1718, 1747, ["North America"], "Missionary to the Delaware", "APOSTOLIC_PROPAGATION", ["North America"], 1743, 1747, 2, "Low"),
    ("Adoniram Judson", 1788, 1850, ["Southeast Asia"], "Translator of the Burmese Bible", "TRANSLATION", ["Southeast Asia"], 1813, 1850, 3, "Medium"),
    ("William Wilberforce", 1759, 1833, ["Western Europe"], "Christian abolitionist", "INSTITUTIONAL", ["Western Europe"], 1787, 1833, 3, "High"),
    ("David Livingstone", 1813, 1873, ["Sub-Saharan Africa"], "Missionary-explorer of Africa", "APOSTOLIC_PROPAGATION", ["Sub-Saharan Africa"], 1841, 1873, 3, "Medium"),
    ("Hudson Taylor", 1832, 1905, ["East Asia"], "Founder of the China Inland Mission", "APOSTOLIC_PROPAGATION", ["East Asia"], 1854, 1905, 4, "High"),
    ("Samuel Ajayi Crowther", 1809, 1891, ["Sub-Saharan Africa"], "First African Anglican bishop", "TRANSLATION", ["Sub-Saharan Africa"], 1843, 1891, 3, "High"),
    ("Charles Spurgeon", 1834, 1892, ["Western Europe"], "Prince of preachers", "REVIVAL", ["Western Europe"], 1854, 1892, 3, "Medium"),
    ("Dwight L. Moody", 1837, 1899, ["North America"], "Mass-revival evangelist", "REVIVAL", ["North America", "Western Europe"], 1870, 1899, 3, "Medium"),
    ("Karl Barth", 1886, 1968, ["Western Europe"], "Theologian of the Word", "THEOLOGICAL", ["Western Europe", "North America"], 1919, 1968, 3, "High"),
    ("Dietrich Bonhoeffer", 1906, 1945, ["Western Europe"], "Martyr against Nazism", "MARTYRDOM", ["Western Europe"], 1943, 1945, 3, "High"),
    ("C. S. Lewis", 1898, 1963, ["Western Europe"], "Apologist of mere Christianity", "THEOLOGICAL", ["Western Europe", "North America"], 1940, 1963, 4, "High"),
    ("Watchman Nee", 1903, 1972, ["East Asia"], "Builder of the indigenous Chinese church", "INSTITUTIONAL", ["East Asia"], 1928, 1972, 3, "Medium"),
]

TIER3 = [
    ("Clement of Rome", 35, 99, ["Roman/Mediterranean"], "Early bishop of Rome", "THEOLOGICAL", ["Roman/Mediterranean"], 88, 99, 2, "Low"),
    ("Ignatius of Antioch", 35, 108, ["Middle East & North Africa"], "Bishop and martyr", "MARTYRDOM", ["Roman/Mediterranean"], 107, 108, 2, "Low"),
    ("Tertullian", 155, 220, ["Middle East & North Africa"], "Latin apologist", "THEOLOGICAL", ["Roman/Mediterranean"], 197, 220, 2, "Low"),
    ("Cyprian of Carthage", 200, 258, ["Middle East & North Africa"], "Bishop and martyr", "MARTYRDOM", ["Roman/Mediterranean"], 248, 258, 2, "Low"),
    ("Julian the Apostate", 331, 363, ["Roman/Mediterranean"], "Emperor who tried to restore paganism", "SUPPRESSION", ["Roman/Mediterranean"], 361, 363, 2, "Medium"),
    ("Basil of Caesarea", 330, 379, ["Eastern Europe & Russia"], "Cappadocian father", "INSTITUTIONAL", ["Roman/Mediterranean"], 370, 379, 2, "Low"),
    ("Gregory of Nyssa", 335, 395, ["Eastern Europe & Russia"], "Cappadocian theologian", "THEOLOGICAL", ["Roman/Mediterranean"], 372, 395, 2, "Low"),
    ("Ambrose of Milan", 339, 397, ["Western Europe"], "Bishop who taught Augustine", "INSTITUTIONAL", ["Western Europe"], 374, 397, 2, "Low"),
    ("Leo the Great", 400, 461, ["Roman/Mediterranean"], "Pope who defined Chalcedon", "INSTITUTIONAL", ["Roman/Mediterranean"], 440, 461, 2, "Low"),
    ("John of Damascus", 675, 749, ["Middle East & North Africa"], "Last of the Greek fathers", "THEOLOGICAL", ["Middle East & North Africa"], 726, 749, 2, "Low"),
    ("The Venerable Bede", 672, 735, ["Western Europe"], "Historian of English Christianity", "THEOLOGICAL", ["Western Europe"], 700, 735, 2, "Low"),
    ("Anskar", 801, 865, ["Western Europe"], "Apostle of the North", "APOSTOLIC_PROPAGATION", ["Western Europe"], 829, 865, 2, "Low"),
    ("Olga of Kiev", 890, 969, ["Eastern Europe & Russia"], "First Christian Rus ruler", "INSTITUTIONAL", ["Eastern Europe & Russia"], 957, 969, 2, "Low"),
    ("Stephen of Hungary", 975, 1038, ["Eastern Europe & Russia"], "Christianizer of Hungary", "INSTITUTIONAL", ["Eastern Europe & Russia"], 1000, 1038, 2, "Low"),
    ("Bernard of Clairvaux", 1090, 1153, ["Western Europe"], "Cistercian reformer", "REVIVAL", ["Western Europe"], 1115, 1153, 2, "Low"),
    ("Catherine of Siena", 1347, 1380, ["Western Europe"], "Mystic and reformer", "REVIVAL", ["Western Europe"], 1366, 1380, 2, "Low"),
    ("Julian of Norwich", 1343, 1416, ["Western Europe"], "English mystic", "THEOLOGICAL", ["Western Europe"], 1373, 1416, 1, "Low"),
    ("Girolamo Savonarola", 1452, 1498, ["Western Europe"], "Florentine reform-preacher", "REVIVAL", ["Western Europe"], 1494, 1498, 2, "Low"),
    ("Philipp Melanchthon", 1497, 1560, ["Western Europe"], "Systematizer of Lutheran theology", "THEOLOGICAL", ["Western Europe"], 1521, 1560, 2, "Low"),
    ("Menno Simons", 1496, 1561, ["Western Europe"], "Anabaptist leader", "THEOLOGICAL", ["Western Europe", "North America"], 1536, 1561, 2, "Low"),
    ("Roberto de Nobili", 1577, 1656, ["South Asia"], "Inculturating missionary in India", "APOSTOLIC_PROPAGATION", ["South Asia"], 1605, 1656, 2, "Low"),
    ("John Eliot", 1604, 1690, ["North America"], "Translator of the Algonquin Bible", "TRANSLATION", ["North America"], 1640, 1690, 2, "Low"),
    ("George Fox", 1624, 1691, ["Western Europe"], "Founder of the Quakers", "REVIVAL", ["Western Europe", "North America"], 1647, 1691, 2, "Low"),
    ("Philipp Spener", 1635, 1705, ["Western Europe"], "Father of Pietism", "REVIVAL", ["Western Europe"], 1675, 1705, 2, "Low"),
    ("Charles Wesley", 1707, 1788, ["Western Europe"], "Hymn-writer of the revival", "REVIVAL", ["Western Europe", "North America"], 1738, 1788, 2, "Low"),
    ("Francis Asbury", 1745, 1816, ["North America"], "Father of American Methodism", "INSTITUTIONAL", ["North America"], 1771, 1816, 2, "Low"),
    ("Charles Finney", 1792, 1875, ["North America"], "Revivalist of the Second Awakening", "REVIVAL", ["North America"], 1821, 1875, 2, "Low"),
    ("Robert Morrison", 1782, 1834, ["East Asia"], "First Protestant Bible in Chinese", "TRANSLATION", ["East Asia"], 1807, 1834, 2, "Low"),
    ("Lottie Moon", 1840, 1912, ["East Asia"], "Missionary to China", "APOSTOLIC_PROPAGATION", ["East Asia"], 1873, 1912, 1, "Low"),
    ("Amy Carmichael", 1867, 1951, ["South Asia"], "Rescuer of temple children", "INSTITUTIONAL", ["South Asia"], 1901, 1951, 1, "Low"),
    ("Sundar Singh", 1889, 1929, ["South Asia"], "Indian sadhu evangelist", "APOSTOLIC_PROPAGATION", ["South Asia"], 1905, 1929, 2, "Low"),
    ("John Sung", 1901, 1944, ["East Asia", "Southeast Asia"], "Revivalist of the Chinese diaspora", "REVIVAL", ["East Asia", "Southeast Asia"], 1927, 1944, 2, "Low"),
    ("Aimee Semple McPherson", 1890, 1944, ["North America"], "Pentecostal mass-evangelist", "REVIVAL", ["North America"], 1918, 1944, 1, "Low"),
    ("Simon Kimbangu", 1887, 1951, ["Sub-Saharan Africa"], "Founder of an African church", "REVIVAL", ["Sub-Saharan Africa"], 1921, 1951, 2, "Low"),
    ("Festo Kivengere", 1919, 1988, ["Sub-Saharan Africa"], "Voice of the East African Revival", "REVIVAL", ["Sub-Saharan Africa"], 1970, 1988, 2, "Low"),
]

# Filler pool: plausible regional witnesses to top up any tier to its exact target,
# clearly marked Speculative + filler so they are never mistaken for curated data.
FILLER_TEMPLATES = [
    ("APOSTOLIC_PROPAGATION", "Regional evangelist"),
    ("TRANSLATION", "Regional Bible translator"),
    ("INSTITUTIONAL", "Regional church-builder"),
    ("REVIVAL", "Regional revival preacher"),
    ("THEOLOGICAL", "Regional teacher"),
    ("MARTYRDOM", "Regional martyr"),
]


def _filler_strand(idx: int, tier: str) -> tuple:
    region = S.REGIONS[idx % len(S.REGIONS)]
    mech, role = FILLER_TEMPLATES[idx % len(FILLER_TEMPLATES)]
    base = 200 + (idx * 137) % 1700  # spread across the timeline 200–1900
    birth = base
    death = base + 60
    strength = 1 + (idx % 2)
    name = f"{role} of {region} (c. {base})"
    return (name, birth, death, [region], role, mech, [region], base + 20, death, strength, "Speculative")


def build_strand_rows() -> list[dict]:
    tiers = {"Tier 1": list(TIER1), "Tier 2": list(TIER2), "Tier 3": list(TIER3)}
    targets = {"Tier 1": 25, "Tier 2": 40, "Tier 3": 35}
    rows: list[dict] = []
    fill_idx = 0
    for tier, items in tiers.items():
        # Pad with labeled filler to the exact target count.
        while len(items) < targets[tier]:
            items.append(_filler_strand(fill_idx, tier))
            fill_idx += 1
        if len(items) > targets[tier]:
            raise AssertionError(f"{tier} has {len(items)} > target {targets[tier]}")
        for (name, birth, death, primary, role, mech, affected,
             ws, we, strength, conf) in items:
            is_filler = role in {t[1] for t in FILLER_TEMPLATES} and "Regional" in name
            rows.append({
                "name": name,
                "birth_year": "" if birth is None else birth,
                "death_year": "" if death is None else death,
                "primary_region": S.dump_multiselect(primary),
                "role": role,
                "mechanism_template": mech,
                "regions_affected": S.dump_multiselect(affected),
                "effect_window_start": ws,
                "effect_window_end": we,
                "strength": strength,
                "depth_tier": tier,
                "confidence": conf,
                "sources": (SYN + " — filler") if is_filler else SYN,
            })
    return rows


# ----------------------------------------------------------------------------------
# LIVES — >= 6 profiles; one is the affiliated -> unbelieving -> strongly-practicing arc
# ----------------------------------------------------------------------------------
LIVES = [
    {
        "id": "life_lyudmila",
        "name": "Lyudmila",
        "era": "20th century",
        "region": "Eastern Europe & Russia",
        "start_disposition": "Affiliated",
        "trajectory": "Affiliated -> Lapsed -> Unaffiliated -> Practicing",
        "drivers": "Soviet schooling and state atheism pull her from a nominal childhood faith into unbelief; decades later the quiet prayers of a believing grandmother and a praying neighbor draw her back to a deep, practicing faith.",
        "summary": "Baptized as an infant but raised under militant atheism, Lyudmila spends her middle years convinced religion is a relic. In her sixties, surrounded by a grandmother and friends who never stopped praying for her, she returns — and becomes the most devout person in her family.",
    },
    {
        "id": "life_marcus",
        "name": "Marcus",
        "era": "2nd century",
        "region": "Roman/Mediterranean",
        "start_disposition": "Unexposed",
        "trajectory": "Unexposed -> Affiliated -> Practicing",
        "drivers": "A Roman artisan meets Christians who care for the sick during a plague; their fearlessness in death converts him.",
        "summary": "Marcus knows nothing of the new faith until an epidemic empties his street and only the Christians stay to nurse the dying. Their hope under death undoes him; he is baptized within the year.",
    },
    {
        "id": "life_aelia",
        "name": "Aelia",
        "era": "4th century",
        "region": "Roman/Mediterranean",
        "start_disposition": "Affiliated",
        "trajectory": "Affiliated -> Practicing",
        "drivers": "After the Edict of Milan it is suddenly safe — and advantageous — to be Christian; she moves from nominal membership to genuine devotion through a local bishop's teaching.",
        "summary": "Aelia's family joined the church when it became respectable. A patient bishop turns her inherited label into living practice.",
    },
    {
        "id": "life_bjorn",
        "name": "Björn",
        "era": "11th century",
        "region": "Western Europe",
        "start_disposition": "Unexposed",
        "trajectory": "Unexposed -> Affiliated -> Lapsed",
        "drivers": "Converted top-down when his chieftain is baptized; the faith never reaches his heart and fades within a generation.",
        "summary": "Björn is baptized because his lord was. The forms remain but the fire never catches; by old age he keeps the feasts and little else.",
    },
    {
        "id": "life_mei",
        "name": "Mei",
        "era": "20th century",
        "region": "East Asia",
        "start_disposition": "Unexposed",
        "trajectory": "Unexposed -> Affiliated -> Practicing",
        "drivers": "Meets believers in an underground house church; complex social ties and personal study deepen a tentative interest into committed faith despite pressure.",
        "summary": "Mei first attends a house church to keep a friend company. Quiet community and risk shared together turn curiosity into conviction.",
    },
    {
        "id": "life_thomas",
        "name": "Thomas",
        "era": "21st century",
        "region": "North America",
        "start_disposition": "Practicing",
        "trajectory": "Practicing -> Lapsed -> Unaffiliated",
        "drivers": "Raised devout, he drifts in a secular university culture; without believing ties nearby, affiliation quietly dissolves into 'none'.",
        "summary": "Thomas grew up in church but moved to a city where no one he respected believed. Nothing dramatic happened; he simply stopped, and then stopped calling himself anything.",
    },
    {
        "id": "life_grace",
        "name": "Grace",
        "era": "20th century",
        "region": "Sub-Saharan Africa",
        "start_disposition": "Affiliated",
        "trajectory": "Affiliated -> Practicing",
        "drivers": "A mission school and the East African Revival turn a nominal mission-church upbringing into ardent, joyful practice.",
        "summary": "Grace's village had a mission church for a generation, but it was the revival's singing and confession that made the faith her own.",
    },
]


def build_lives_rows() -> list[dict]:
    return [dict(life) for life in LIVES]


# ----------------------------------------------------------------------------------
# Writer
# ----------------------------------------------------------------------------------
def _write_csv(path: str, columns: list[str], rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    regions = build_regions_rows()
    anchors = build_anchor_rows()
    events = build_event_rows()
    strands = build_strand_rows()
    lives = build_lives_rows()

    _write_csv(os.path.join(DATA_DIR, "regions.csv"), S.REGIONS_COLUMNS, regions)
    _write_csv(os.path.join(DATA_DIR, "anchors.csv"), S.ANCHORS_COLUMNS, anchors)
    _write_csv(os.path.join(DATA_DIR, "events.csv"), S.EVENTS_COLUMNS, events)
    _write_csv(os.path.join(DATA_DIR, "strands.csv"), S.STRANDS_COLUMNS, strands)
    _write_csv(os.path.join(DATA_DIR, "lives.csv"), S.LIVES_COLUMNS, lives)

    # Sanity assertions matching the spec's fixture requirements.
    global_years = sorted(r["year"] for r in anchors if r["region"] == S.GLOBAL)
    assert global_years == S.ANCHOR_YEARS, "missing GLOBAL anchor rows"
    tier_counts = {t: sum(1 for r in strands if r["depth_tier"] == t) for t in S.DEPTH_TIERS}
    assert tier_counts == {"Tier 1": 25, "Tier 2": 40, "Tier 3": 35}, tier_counts
    assert any(int(r["birth_year"]) < 0 for r in strands if r["birth_year"] != ""), "need a BC birth_year"
    assert any(S.load_multiselect(r["regions_affected"]) == S.REGIONS or
               r["regions_affected"] == S.dump_multiselect(["GLOBAL"]) for r in strands), "need a GLOBAL strand"
    mechs = {r["mechanism_template"] for r in strands}
    assert mechs == set(S.STRAND_MECHANISM_ENUM), f"missing mechanism_templates: {set(S.STRAND_MECHANISM_ENUM) - mechs}"
    assert len(lives) >= 6, "need >= 6 lives"

    print(f"Fixtures written to {DATA_DIR}/")
    print(f"  regions.csv : {len(regions)} rows")
    print(f"  anchors.csv : {len(anchors)} rows ({len(global_years)} GLOBAL + {len(anchors)-len(global_years)} regional)")
    print(f"  events.csv  : {len(events)} rows")
    print(f"  strands.csv : {len(strands)} rows  {tier_counts}")
    print(f"  lives.csv   : {len(lives)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
