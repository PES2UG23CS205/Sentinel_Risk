"""
SentinelRisk — Merchant Generator

Generates ~1,500 merchants with realistic category-specific properties.
Each merchant has a behavioral profile that influences transaction patterns.
"""

import numpy as np
from datetime import timedelta
from simulation.data_generation.config import GenerationConfig

# Realistic merchant name prefixes by category
_NAME_PREFIXES = {
    "electronics":      ["TechZone", "GadgetHub", "ElectroMart", "DigitalWorld", "ByteStore",
                         "CircuitCity", "MegaPixel", "PowerTech", "SmartBuy", "ChipNex"],
    "fashion":          ["StyleStreet", "TrendSet", "FashionVault", "LookBook", "WearHouse",
                         "ThreadBarn", "UrbanStitch", "ModaFit", "ClosetBox", "FabricLane"],
    "grocery":          ["FreshMart", "DailyNeeds", "GreenBasket", "QuickGrocery", "PantryPlus",
                         "NatureFresh", "ValueMart", "StaplePick", "FarmDirect", "GroceHub"],
    "food_delivery":    ["BiteBuddy", "FoodDash", "MealBox", "QuickEats", "TastyTrail",
                         "SpiceRoute", "ChefDoor", "HungryOwl", "DineExpress", "CraveTown"],
    "travel":           ["JetSetGo", "TripWise", "SkyRoute", "WanderBook", "FlyEasy",
                         "TravelNest", "VoyagePlan", "GlobeHopper", "RouteMaster", "PackNGo"],
    "education":        ["LearnHub", "EduVerse", "SkillCraft", "ClassBridge", "StudyNest",
                         "BrainWorks", "CourseTrail", "AcadEdge", "MentorLab", "KnowPath"],
    "digital_services": ["CloudSync", "DataFlow", "StreamLine", "AppForge", "NetPulse",
                         "SaaSPoint", "CodeBridge", "DigitalNex", "PlatformX", "ByteShift"],
    "health":           ["MediCare", "HealthFirst", "WellnessHub", "PharmEasy", "VitalCare",
                         "CureQuick", "LifePulse", "DocConnect", "FitPath", "HealZone"],
    "home":             ["HomeNest", "InteriorCo", "DecorVault", "FurniWorld", "HouseJoy",
                         "LivingSpace", "WallCraft", "CozyCorner", "RoomStyle", "BuildMart"],
    "entertainment":    ["FunZone", "PlayBox", "JoyRide", "GameVerse", "ShowTime",
                         "TicketBay", "EventPulse", "MediaWave", "StarStream", "AmusePark"],
}


def generate_merchants(rng: np.random.Generator, config: GenerationConfig) -> list[dict]:
    """
    Generate merchants with category-specific behavioral profiles.

    Returns list of dicts with keys:
        id, name, category, created_at, typical_order_value,
        typical_order_value_std, expected_daily_transactions, tier
    """
    categories = [c[0] for c in config.merchant_categories]
    cat_weights = np.array([c[1] for c in config.merchant_categories])
    cat_weights /= cat_weights.sum()

    cat_aov = {c[0]: c[2] for c in config.merchant_categories}
    cat_aov_std = {c[0]: c[3] for c in config.merchant_categories}
    cat_daily_base = {c[0]: c[4] for c in config.merchant_categories}

    tier_names = [t[0] for t in config.merchant_tiers]
    tier_weights = np.array([t[1] for t in config.merchant_tiers])
    tier_weights /= tier_weights.sum()
    tier_vol_mult = {t[0]: t[2] for t in config.merchant_tiers}

    # Assign categories proportionally
    assigned_cats = rng.choice(categories, size=config.num_merchants, p=cat_weights)
    assigned_tiers = rng.choice(tier_names, size=config.num_merchants, p=tier_weights)

    # Merchant creation dates: spread across first 3 months with earlier bias
    sim_days = (config.sim_end - config.sim_start).days
    creation_days = rng.beta(1.5, 4.0, size=config.num_merchants) * min(sim_days, 90)

    merchants = []
    cat_counters: dict[str, int] = {}

    for i in range(config.num_merchants):
        cat = assigned_cats[i]
        tier = assigned_tiers[i]

        # Generate name
        cat_counters.setdefault(cat, 0)
        cat_counters[cat] += 1
        prefixes = _NAME_PREFIXES.get(cat, ["Shop"])
        prefix = prefixes[cat_counters[cat] % len(prefixes)]
        name = f"{prefix}_{cat_counters[cat]:04d}"

        # Merchant-specific AOV with variation
        aov = max(50.0, rng.normal(cat_aov[cat], cat_aov_std[cat] * 0.3))
        aov_std = max(20.0, rng.normal(cat_aov_std[cat], cat_aov_std[cat] * 0.2))

        # Daily volume = base × tier multiplier × individual variation
        daily_base = cat_daily_base[cat] * tier_vol_mult[tier]
        daily_txn = max(1, int(rng.normal(daily_base, daily_base * 0.3)))

        created_at = config.sim_start + timedelta(days=float(creation_days[i]))

        merchants.append({
            "id": i + 1,
            "name": name,
            "category": cat,
            "created_at": created_at,
            "typical_order_value": round(aov, 2),
            "typical_order_value_std": round(aov_std, 2),
            "expected_daily_transactions": daily_txn,
            "tier": tier,
        })

    return merchants
