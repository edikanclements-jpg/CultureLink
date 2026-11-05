"""The nine Indian menswear listings selected for the demonstration catalog."""

SELLERS = {1: "Anita Dongre", 2: "Anu Attires", 5: "The India Craft House"}
SELLER_ALIASES = {1: "House of Anita Dongre", 2: "AnuAttires", 5: "India Craft House"}
ASSET_ROOT = "static/catalog/indian-menswear/"
PRICE_NOTES = "USD boutique listing price recorded for the CultureLink demo."

_ANITA_SIZES = "38, 40, 42, 44, 46, 48"
_ANU_SIZES = "36, 38, 40, 42, 44, 46"

ITEMS = (
    {
        "key": "2026-11-anita-arman-black",
        "seller_id": 1,
        "asset": "anita-arman.jpg",
        "name": "Arman Black Bandhgala",
        "description": (
            "Formal menswear jacket in a black cotton-linen blend with a standing collar, "
            "gold-tone buttons, and a front pocket. The jacket is the listed piece."
        ),
        "category": "Bandhgala",
        "price": 690,
        "colors": "Black",
        "size": _ANITA_SIZES,
        "occasions": ("Wedding", "Formal"),
    },
    {
        "key": "2026-11-anita-smyan-powder-blue",
        "seller_id": 1,
        "asset": "anita-smyan-blue.jpg",
        "name": "Smyan Powder Blue Silk Kurta",
        "description": (
            "Powder blue silk menswear kurta with a button placket, stand collar, and side pockets. "
            "Shown with ivory trousers. The kurta is the listed piece."
        ),
        "category": "Kurta",
        "price": 350,
        "colors": "Blue, Powder Blue",
        "size": _ANITA_SIZES,
        "occasions": ("Wedding", "Festival"),
    },
    {
        "key": "2026-11-anita-smyan-pink",
        "seller_id": 1,
        "asset": "anita-smyan-pink.jpg",
        "name": "Smyan Pink Silk Kurta",
        "description": (
            "Soft pink silk menswear kurta with a button placket, stand collar, and side pockets. "
            "Shown with ivory trousers. The kurta is the listed piece."
        ),
        "category": "Kurta",
        "price": 350,
        "colors": "Pink",
        "size": _ANITA_SIZES,
        "occasions": ("Wedding", "Festival"),
    },
    {
        "key": "2026-11-anu-kurta-off-white",
        "seller_id": 2,
        "asset": "anu-off-white.jpg",
        "name": "Off-White Kurta set",
        "description": (
            "Off-white cotton menswear kurta set with embroidery along the collar and placket, "
            "styled with beige trousers."
        ),
        "category": "Kurta Set",
        "price": 86,
        "colors": "Off White, Beige",
        "size": _ANU_SIZES,
        "occasions": ("Wedding", "Festival"),
    },
    {
        "key": "2026-11-anu-kurta-mustard",
        "seller_id": 2,
        "asset": "anu-mustard.jpg",
        "name": "Mustard Kurta set",
        "description": (
            "Mustard yellow cotton menswear kurta set with decorative stitching down the front, "
            "styled with beige trousers."
        ),
        "category": "Kurta Set",
        "price": 86,
        "colors": "Yellow, Mustard, Beige",
        "size": _ANU_SIZES,
        "occasions": ("Wedding", "Festival"),
    },
    {
        "key": "2026-11-anu-kurta-green",
        "seller_id": 2,
        "asset": "anu-green.jpg",
        "name": "Green Kurta set",
        "description": (
            "Light green silk-cotton menswear kurta set with tonal embroidery at the neckline "
            "and placket, styled with beige trousers."
        ),
        "category": "Kurta Set",
        "price": 86,
        "colors": "Green, Beige",
        "size": _ANU_SIZES,
        "occasions": ("Wedding", "Festival"),
    },
    {
        "key": "2026-11-craft-house-olive-bands",
        "seller_id": 5,
        "asset": "craft-olive.jpg",
        "name": "Light & Warm Himachal Stole - Olive Bands",
        "description": (
            "Handwoven olive wool stole with red and rust Kinnauri bands and fringed ends. "
            "This Himachali menswear accessory measures 2 m long by 0.75 m wide."
        ),
        "category": "Stole",
        "price": 38,
        "colors": "Green, Olive, Red, Orange",
        "size": "One Size",
        "occasions": ("Formal", "Festival"),
    },
    {
        "key": "2026-11-craft-house-autumn-tones",
        "seller_id": 5,
        "asset": "craft-autumn.jpg",
        "name": "Light & Warm Merino Wool Stole - Autumn Tones",
        "description": (
            "Merino wool menswear stole woven in blocks of green, rust, teal, and olive, "
            "with hand-knotted fringe. Measures 2 m long by 0.30 m wide."
        ),
        "category": "Stole",
        "price": 35,
        "colors": "Green, Olive, Teal, Orange",
        "size": "One Size",
        "occasions": ("Formal", "Festival"),
    },
    {
        "key": "2026-11-craft-house-night-shore",
        "seller_id": 5,
        "asset": "craft-night.jpg",
        "name": "Light & Warm Merino Wool Muffler - Night Shore",
        "description": (
            "Navy merino wool menswear muffler with pale and red stripes and fringed ends. "
            "Measures 2 m long by 0.30 m wide."
        ),
        "category": "Muffler",
        "price": 20,
        "colors": "Blue, Navy, White, Red",
        "size": "One Size",
        "occasions": ("Formal", "Festival"),
    },
)

IMAGE_URLS = frozenset("/" + ASSET_ROOT + item["asset"] for item in ITEMS)
