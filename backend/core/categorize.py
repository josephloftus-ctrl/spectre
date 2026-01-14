"""
Inventory Item Categorization

Automatically categorizes inventory items into storage locations based on
item descriptions. Used for smart sorting during inventory counts.

Locations (in walking order):
1. Freezer
2. Walk In Cooler
3. Beverage Room
4. Dry Storage Food
5. Dry Storage Supplies
6. Chemical Locker

Special:
- NEVER INVENTORY: Items that should be skipped (fresh produce, dry seasonings)
- UNASSIGNED: Items needing manual review
"""

from typing import Dict, Optional, Tuple

# Fallback walking order (used if no plugin loaded)
_DEFAULT_LOCATION_ORDER = {
    'Freezer': 1,
    'Walk In Cooler': 2,
    'Beverage Room': 3,
    'Dry Storage Food': 4,
    'Dry Storage Supplies': 5,
    'Chemical Locker': 6,
    'NEVER INVENTORY': 99,
    'UNASSIGNED': 100,
}


def _get_location_order() -> Dict[str, int]:
    """Get location order from plugin or use defaults."""
    try:
        from backend.core.plugins import PluginLoader
        loader = PluginLoader.get()
        if loader.has_plugins():
            plugin_order = loader.get_location_order()
            if plugin_order:
                return plugin_order
    except ImportError:
        pass
    return _DEFAULT_LOCATION_ORDER


# For backwards compatibility
LOCATION_ORDER = _DEFAULT_LOCATION_ORDER


def categorize_item(item_desc: str, brand: str = '', pack: str = '') -> Tuple[str, bool]:
    """
    Categorize an inventory item based on its description.

    Args:
        item_desc: Item description text
        brand: Brand name (optional, for better matching)
        pack: Pack type (optional)

    Returns:
        Tuple of (location, never_count)
        - location: Storage location name
        - never_count: True if item should be skipped during counts
    """
    item_upper = str(item_desc).upper().strip()
    brand_upper = str(brand).upper().strip() if brand else ''

    # ========================================================================
    # NEVER INVENTORY - Fresh produce, dry seasonings, fresh bread
    # These items are too perishable or variable to count accurately
    # ========================================================================
    never_inventory_keywords = [
        # Fresh produce (not processed/prepared)
        'LETTUCE', 'TOMATO BULK', 'TOMATO GRAPE FRSH', 'TOMATO SLI FRSH',
        'TOMATO FRESH', 'CUCUMBER FRESH', 'CUCUMBER ENGLISH',
        'SPINACH BABY FRSH', 'SPINACH CLIPPED FRESH', 'SPINACH FRESH',
        'MUSHROOM SLCD FRESH', 'MUSHROOM FRESH', 'CABBAGE DICED',
        'GRAPE RED SDLS FRESH', 'STRAWBERRY FRESH', 'BERRY FRESH',
        'BANANA FRESH', 'APPLE FRESH', 'ORANGE FRESH', 'MELON FRESH',
        'AVOCADO', 'CILANTRO', 'PARSLEY FRESH', 'BASIL FRESH',

        # Dry seasonings (not sauces or prepared items)
        'SEASONING CAJUN', 'SEASONING CARIBBEAN', 'SEASONING CHICKEN MONTREAL',
        'SEASONING RUB OLD BAY', 'SEASONING STEAK MONTREAL', 'SEASONING TACO',
        'SPICE GARLIC PWDR', 'SPICE PEPPER BLK TABLE', 'SPICE CINNAMON',
        'SPICE PAPRIKA', 'SPICE OREGANO', 'SPICE CUMIN', 'HERB DRIED',

        # Fresh bread from daily delivery
        'TOAST FRENCH STICK', 'DANISH ASST IW', 'BREAD FRESH',
        'BAGEL FRESH', 'ROLL FRESH', 'CROISSANT FRESH', 'MUFFIN FRESH',
    ]

    for keyword in never_inventory_keywords:
        if keyword in item_upper:
            return ('NEVER INVENTORY', True)

    # ========================================================================
    # FREEZER - Frozen items, appetizers, frozen entrees
    # ========================================================================
    freezer_keywords = [
        # Frozen indicators
        'FROZ', 'FROZEN', 'IQF',

        # Appetizers
        'APTZR', 'APPETIZER', 'PIEROG', 'PIZZA', 'MOZZ STICK',
        'EGG ROLL', 'SPRING ROLL', 'WONTON',

        # Frozen potatoes
        'FRY', 'FRIES', 'TATER TOT', 'HASH BRN', 'HASHBROWN',
        'POTATO WEDGE', 'CURLY FRY', 'WAFFLE FRY',

        # Frozen vegetables
        'BEAN GREEN WHL', 'BEAN LIMA', 'BROCCOLI FLORET', 'CORN WHL KERNEL',
        'PEA & CARROT', 'PEA GREEN', 'VEGETABLE BLEND', 'VEGETABLE MIX',
        'MIXED VEGETABLE', 'STIR FRY VEG',

        # Frozen proteins/entrees
        'CRAB CAKE', 'FISH STICK', 'FISH FILLET FROZ',
        'WING', 'NUGGET', 'TENDER', 'POPCORN CHICKEN',
        'ENTREE', 'MEATLOAF FROZ', 'SALISBURY', 'MACARONI & CHEESE FROZ',
        'FRENCH STICK HT&SRV', 'STEAK PHILLY', 'PATTY FROZ',

        # Ice cream / frozen desserts
        'ICE CREAM', 'GELATO', 'SORBET', 'FROZEN YOGURT',
        'POPSICLE', 'ICE BAR',
    ]

    # Special case: potato items with FRY/HASH/TATER go to freezer
    if 'POTATO' in item_upper and any(kw in item_upper for kw in ['FRY', 'HASH', 'TATER', 'WEDGE']):
        return ('Freezer', False)

    for keyword in freezer_keywords:
        if keyword in item_upper:
            return ('Freezer', False)

    # ========================================================================
    # WALK-IN COOLER - Dairy, meat, eggs, prepared produce, juice
    # ========================================================================
    cooler_keywords = [
        # Dairy
        'MILK', 'CHEESE', 'BUTTER', 'CREAM', 'YOGURT', 'SOUR CREAM',
        'COTTAGE', 'RICOTTA', 'MOZZARELLA', 'CHEDDAR', 'PARMESAN',

        # Eggs
        'EGG WHOLE', 'EGG LIQ', 'EGG SCRAMBLED', 'EGG PATTY',

        # Meat/Protein (refrigerated, not frozen)
        'CHICKEN BREAST', 'CHICKEN THIGH', 'BEEF GROUND', 'BEEF SLICED',
        'PORK LOIN', 'PORK CHOP', 'TURKEY BREAST', 'TURKEY GROUND',
        'BACON', 'HAM', 'SAUSAGE LINK', 'SAUSAGE PATTY',
        'FRANK', 'HOT DOG', 'MEATBALL', 'SCRAPPLE',
        'DELI MEAT', 'SALAMI', 'PEPPERONI', 'BOLOGNA',

        # Seafood (refrigerated)
        'CRAB IMIT', 'SHRIMP COOKED', 'SALMON', 'TUNA FRESH',

        # Deli/Prepared
        'DELI', 'TOPPING WHPD', 'RAVIOLI FRESH', 'PASTA SHELL STFD',
        'TORTELLINI', 'GNOCCHI',

        # Refrigerated sauces/condiments
        'JUICE', 'SALSA FRESH', 'HUMMUS', 'CREAMER', 'GUACAMOLE',
        'GRAVY REFRIG', 'SAUCE CHEESE REFRIG', 'PESTO',

        # Prepared produce (DO count these - they're prepped)
        'ONION RING', 'ONION SLICED', 'ONION DICED', 'ONION YELLOW DICED',
        'PEPPER ROASTED', 'PEPPER GREEN DICED', 'PEPPER RED DICED',
        'COLESLAW', 'POTATO SALAD', 'MACARONI SALAD',
    ]

    # Check for refrigerated indicators
    if any(kw in item_upper for kw in ['REFRIG', 'FRESH CUT', 'PREPPED']):
        return ('Walk In Cooler', False)

    for keyword in cooler_keywords:
        if keyword in item_upper:
            return ('Walk In Cooler', False)

    # ========================================================================
    # BEVERAGE ROOM - Drinks, coffee, tea, bottled beverages
    # ========================================================================
    # Note: Be careful with generic terms like 'SODA' which can match 'BAKING SODA'
    beverage_keywords = [
        'DRINK ENERGY', 'ENERGY DRINK', 'MONSTER', 'RED BULL',
        'COFFEE GRND', 'COFFEE BEAN', 'COFFEE RTD', 'STARBUCKS',
        'TEA HOT', 'TEA BAG', 'TEA ICED',
        'WATER SPRING', 'WATER BOTTLED', 'SPARKLING WATER',
        'SODA CAN', 'SODA BOTTLE', 'SODA 2L', 'SODA 20OZ', 'SODA 12OZ',
        'COLA', 'PEPSI', 'COKE', 'SPRITE', 'GINGER ALE', 'DR PEPPER',
        'MOUNTAIN DEW', 'FANTA', 'LEMONADE', 'GATORADE', 'POWERADE',
        'SPORTS DRINK', 'JUICE BOX', 'JUICE BOTTLE',
        'APPLE JUICE', 'ORANGE JUICE', 'NITRO',
    ]

    # Exclude baking items from beverage matching
    if 'BAKING' not in item_upper:
        for keyword in beverage_keywords:
            if keyword in item_upper:
                return ('Beverage Room', False)

    # ========================================================================
    # DRY STORAGE - FOOD
    # ========================================================================
    dry_food_keywords = [
        # Oils & cooking basics
        'OIL VEG', 'OIL OLIVE', 'OIL CANOLA', 'SHORTENING',
        'PAN COATING', 'COOKING SPRAY', 'EXTRACT VANILLA',

        # Pasta & grains
        'PASTA', 'SPAGHETTI', 'PENNE', 'LINGUINE', 'MACARONI DRY',
        'RICE', 'QUINOA', 'COUSCOUS',
        'CEREAL', 'GRANOLA', 'OATMEAL', 'GRITS',

        # Canned goods
        'BEAN REFRIED', 'BEAN BLACK CAN', 'BEAN KIDNEY',
        'CHILI', 'TUNA CAN', 'SOUP CAN', 'BROTH', 'STOCK',
        'TOMATO SAUCE', 'TOMATO PASTE', 'TOMATO DICED CAN',

        # Snacks
        'CHIP', 'CRACKER', 'COOKIE', 'DOUGH COOKIE',
        'PRETZEL', 'POPCORN', 'NUT MIX', 'TRAIL MIX',

        # Condiments & sauces (shelf stable)
        'SAUCE BBQ', 'SAUCE SOY', 'SAUCE HOT', 'SAUCE TERIYAKI',
        'KETCHUP', 'MUSTARD', 'MAYO', 'MAYONNAISE',
        'DRESSING', 'VINEGAR', 'RELISH',
        'PUDDING', 'JELLY', 'JAM', 'SYRUP', 'HONEY',
        'PEANUT BUTTER',

        # Baking
        'FLOUR', 'SUGAR', 'BAKING POWDER', 'BAKING SODA',
        'CORNSTARCH', 'BREADCRUMB', 'PANKO',

        # Other dry goods
        'CROUTON', 'SAUERKRAUT', 'CRANBERRY DRIED', 'CRAISINS',
        'RAISIN', 'FRUIT DRIED',

        # Shelf-stable potatoes
        'POTATO WHL CAN', 'POTATO SWEET CAN', 'POTATO FLAKE',
        'POTATO AU GRATIN MIX', 'POTATO CHIP',
    ]

    for keyword in dry_food_keywords:
        if keyword in item_upper:
            return ('Dry Storage Food', False)

    # ========================================================================
    # DRY STORAGE - SUPPLIES
    # ========================================================================
    supply_keywords = [
        # Gloves & PPE
        'GLOVE', 'APRON', 'HAIRNET', 'BEARD NET',

        # Paper products
        'NAPKIN', 'TOWEL PAPER', 'TISSUE', 'TOILET PAPER',

        # Wraps & storage
        'FILM PLASTIC', 'FOIL ALUMINUM', 'WRAP PLASTIC', 'WRAP FOIL',
        'BAG TRASH', 'BAG STORAGE', 'BAG SANDWICH', 'BAG PRODUCE',

        # Containers & serviceware
        'CONTAINER', 'CUP PLASTIC', 'CUP PAPER', 'CUP FOAM',
        'LID', 'PLATE', 'BOWL', 'TRAY', 'CLAMSHELL',

        # Utensils
        'FORK', 'KNIFE PLASTIC', 'SPOON', 'SPORK', 'STRAW',

        # Liners & misc
        'LINER PAN', 'LINER CAN', 'PARCHMENT',
        'TOOTHPICK', 'SKEWER',
    ]

    for keyword in supply_keywords:
        if keyword in item_upper:
            return ('Dry Storage Supplies', False)

    # ========================================================================
    # CHEMICAL LOCKER
    # ========================================================================
    chemical_keywords = [
        'CLEAN', 'SANITIZ', 'DETERGENT', 'SOAP', 'DEGREASER',
        'DESCALER', 'BLEACH', 'DISINFECT', 'QUATERNARY',
        'HAND WASH', 'DISH SOAP', 'FLOOR CLEAN',
    ]

    for keyword in chemical_keywords:
        if keyword in item_upper:
            return ('Chemical Locker', False)

    # ========================================================================
    # FALLBACK MATCHING - Try to infer from common patterns
    # ========================================================================

    # Frozen indicators anywhere
    if 'FROZ' in item_upper or 'IQF' in item_upper:
        return ('Freezer', False)

    # Refrigerated/cold indicators
    if 'REFRIG' in item_upper or 'COLD' in item_upper:
        return ('Walk In Cooler', False)

    # Pack size hints (CS usually means case of shelf-stable goods)
    if pack and 'CS' in str(pack).upper():
        # Large case packs are often dry storage
        return ('Dry Storage Food', False)

    # If we get here, item needs manual categorization
    return ('UNASSIGNED', False)


def get_location_sort_key(location: str) -> int:
    """Get sort order for a location (for walking path optimization)."""
    location_order = _get_location_order()
    return location_order.get(location, 50)


def sort_items_by_location(items: list, location_key: str = 'location') -> list:
    """
    Sort items by location in walking order.

    Args:
        items: List of item dicts
        location_key: Key name for location field in items

    Returns:
        Sorted list of items
    """
    return sorted(
        items,
        key=lambda x: (
            get_location_sort_key(x.get(location_key, 'UNASSIGNED')),
            x.get('description', '').upper()
        )
    )
