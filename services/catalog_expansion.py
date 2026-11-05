"""Add curated pieces once, without replacing existing catalog rows."""
from threading import Lock

from flask import current_app
from mysql.connector import Error
from database import get_db_connection
from services import indian_menswear


SELLERS = {6: 'Klothouse', 7: 'Olis Collections', 8: 'Priscer Luxe'}
ASSET_ROOT = 'static/catalog/nigerian/'
PRICE_NOTES = 'Price to be determined. Custom sizing and final pricing will be confirmed together. Exact set contents and accessories are confirmed with the quote.'

ITEMS = (
    {'key': '2026-11-klothouse-pink', 'seller_id': 6, 'asset': '6-pink.png',
     'source': 'Klothouse Pink.png', 'name': 'Klothouse Blush Pink Beaded Gown',
     'description': 'Blush pink fitted gown with a structured sweetheart bodice, long sheer embellished sleeves and flared cuffs. Sparkling silver patterns run down the long skirt. Shown with a coordinating headwrap and fan.',
     'category': 'Dress', 'colors': 'Pink, Silver', 'occasions': ('Wedding', 'Formal')},
    {'key': '2026-11-klothouse-purple', 'seller_id': 6, 'asset': '6-purple.png',
     'source': 'Klothouse Purple.png', 'name': 'Klothouse Purple Floral-Embellished Gown',
     'description': 'Purple gown with a shaped sweetheart bodice, draped off-the-shoulder straps and a long skirt covered in pink and green floral patterns. A high front opening reveals the lower leg. Shown with a matching purple headwrap.',
     'category': 'Dress', 'colors': 'Purple, Pink, Green', 'occasions': ('Wedding', 'Formal')},
    {'key': '2026-11-klothouse-red', 'seller_id': 6, 'asset': '6-red.png',
     'source': 'Klothouse Red.png', 'name': 'Klothouse Red One-Shoulder Mermaid Gown',
     'description': 'Red fitted evening gown with a one-shoulder neckline, dark sparkling beadwork and floral ruffles along one side. The flared mermaid hem extends into a trailing train.',
     'category': 'Dress', 'colors': 'Red, Black', 'occasions': ('Wedding', 'Formal')},
    {'key': '2026-11-olis-rust-bridal', 'seller_id': 7, 'asset': '7-orange-bridal.png',
     'source': 'Olis COllections Bridal.png', 'name': 'Olis Collections Rust Embellished Bridal Outfit',
     'description': 'Rust-orange bridal outfit with a structured neckline, long embellished sleeves and sculpted shoulder details. Silver and purple-toned decorative patterns cover the bodice. The supplied photograph is a closer view of the outfit, shown with a coordinating headwrap.',
     'category': 'Bridal Outfit', 'colors': 'Rust Orange, Silver, Purple', 'occasions': ('Wedding', 'Formal')},
    {'key': '2026-11-olis-peach-bridal', 'seller_id': 7, 'asset': '7-peach-bridal.png',
     'source': 'Olis COllections Bride.png', 'name': 'Olis Collections Peach Beaded Bridal Gown',
     'description': 'Peach bridal gown with a sweetheart neckline, a fitted structured bodice and long sheer sleeves. Dense sparkling beadwork continues into the flared lower skirt and small train. Shown with a coordinating headwrap.',
     'category': 'Bridal Gown', 'colors': 'Peach, Gold, Silver', 'occasions': ('Wedding', 'Formal')},
    {'key': '2026-11-olis-ivory-mens', 'seller_id': 7, 'asset': '7-ivory-mens.png',
     'source': 'Olis COllections Mens 2 (1).png', 'name': 'Olis Collections Ivory Embroidered Agbada Set',
     'description': "Ivory men's traditional look with a wide agbada-style outer robe, silver-toned embroidery and a coordinating cap. This listing refers to the men's ivory outfit on the right of the couple photograph. The peach bridal outfit is a separate listing.",
     'category': 'Menswear Set', 'colors': 'Ivory, Silver', 'occasions': ('Wedding', 'Formal', 'Festival')},
    {'key': '2026-11-olis-rust-mens', 'seller_id': 7, 'asset': '7-orange-mens.png',
     'source': 'Olis COllections Mens.png', 'name': 'Olis Collections Rust Embroidered Agbada Set',
     'description': "Rust-orange men's traditional look with an agbada-style outer robe, decorative embroidery and a coordinating cap. This listing refers to the men's rust outfit on the right of the couple photograph. The accompanying bridal outfit is separate; pictured jewelry is styling context.",
     'category': 'Menswear Set', 'colors': 'Rust Orange, Gold', 'occasions': ('Wedding', 'Formal', 'Festival')},
    {'key': '2026-11-priscer-orange', 'seller_id': 8, 'asset': '8-orange.png',
     'source': 'Priscer Luxe Orange.png', 'name': 'Priscer Luxe Orange Puff-Sleeve Printed Gown',
     'description': 'Orange and black patterned gown with a fitted bodice, large gathered puff sleeves and a long shaped skirt. Contrasting red and yellow geometric panels continue down the front and sides.',
     'category': 'Dress', 'colors': 'Orange, Black, Red, Yellow', 'occasions': ('Wedding', 'Formal', 'Festival')},
    {'key': '2026-11-priscer-pink', 'seller_id': 8, 'asset': '8-pink.png',
     'source': 'Priscer Luxe Pink.png', 'name': 'Priscer Luxe Pink Off-Shoulder Printed Gown',
     'description': 'Pink, black and cream patterned gown with narrow off-the-shoulder straps and a structured fitted bodice. Curving decorative motifs continue through the long skirt to its floor-length hem.',
     'category': 'Dress', 'colors': 'Pink, Black, Cream', 'occasions': ('Wedding', 'Formal', 'Festival')},
    {'key': '2026-11-priscer-purple', 'seller_id': 8, 'asset': '8-purple.png',
     'source': 'Priscer Luxe purple.png', 'name': 'Priscer Luxe Purple Floral Midi Dress',
     'description': 'Purple floral-print dress with an off-the-shoulder neckline, gathered elbow-length sleeves and a fitted bodice. White and pink floral patterns decorate the below-knee skirt.',
     'category': 'Dress', 'colors': 'Purple, White, Pink', 'occasions': ('Wedding', 'Formal', 'Festival')},
)

SCHEMA = """CREATE TABLE IF NOT EXISTS curated_catalog_items (
    catalog_key VARCHAR(80) NOT NULL,
    item_id INT UNSIGNED DEFAULT NULL,
    PRIMARY KEY (catalog_key),
    UNIQUE KEY uq_curated_catalog_item (item_id),
    CONSTRAINT fk_curated_catalog_item FOREIGN KEY (item_id)
        REFERENCES items (item_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci"""
_import_lock = Lock()
_READY = 'culturelink_curated_catalog_2026_11'


def _ensure_table():
    # MySQL DDL implicitly commits. Never create the mapping table on the
    # connection holding catalog changes or any account/order transaction.
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute('SELECT catalog_key, item_id FROM curated_catalog_items LIMIT 0')
            cursor.fetchall()
        except Error as error:
            if error.errno != 1146:
                raise
            cursor.execute(SCHEMA)
            connection.commit()
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def ensure_catalog():
    """Import on the first catalog read. Repeat starts never duplicate pieces.

    Existing products are not updated. A stored mapping with a null item ID
    preserves an intentional later deletion instead of recreating that piece.
    """
    if current_app.extensions.get(_READY):
        return
    with _import_lock:
        if current_app.extensions.get(_READY):
            return
        _ensure_table()
        connection = get_db_connection()
        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)
            # Match the selected boutiques by name, then lock the candidate
            # rows in the same order for each worker.
            menswear_names = {
                identifier: {name.casefold(), indian_menswear.SELLER_ALIASES[identifier].casefold()}
                for identifier, name in indian_menswear.SELLERS.items()
            }
            names = sorted(set().union(*menswear_names.values()))
            placeholders = ','.join(['%s'] * len(names))
            cursor.execute(
                'SELECT s.seller_id, s.seller_name, EXISTS ('
                'SELECT 1 FROM seller_profiles p WHERE p.seller_id = s.seller_id'
                ') AS account_owned FROM sellers s WHERE s.seller_id IN (%s,%s,%s) '
                f'OR LOWER(TRIM(s.seller_name)) IN ({placeholders}) ORDER BY s.seller_id FOR UPDATE',
                (*sorted(SELLERS), *names),
            )
            seller_rows = cursor.fetchall()
            sellers = {
                row['seller_id']: str(row['seller_name']).strip().casefold()
                for row in seller_rows
            }
            if any(sellers.get(identifier) != name.casefold() for identifier, name in SELLERS.items()):
                raise Error(msg='The curated boutique records do not match this catalog update. Existing catalog rows were preserved.')
            cursor.execute('SELECT culture_id, culture_name FROM cultures')
            cultures = {row['culture_name'].strip().casefold(): row['culture_id'] for row in cursor.fetchall()}
            cursor.execute('SELECT occasion_id, occasion_name FROM occasions')
            occasions = {row['occasion_name'].strip().casefold(): row['occasion_id'] for row in cursor.fetchall()}
            if 'nigerian' not in cultures or not {'wedding', 'formal', 'festival'} <= occasions.keys():
                raise Error(msg='Required culture or occasion records are missing. Existing catalog rows were preserved.')
            menswear_sellers = {}
            if 'indian' not in cultures:
                current_app.logger.warning('Indian menswear needs the Indian culture record in MySQL.')
            else:
                # A similarly named seller account is separate from the demo boutique.
                curated_sellers = {row['seller_id'] for row in seller_rows if not row['account_owned']}
                for identifier, known_names in menswear_names.items():
                    matches = [seller_id for seller_id in curated_sellers if sellers[seller_id] in known_names]
                    if identifier in matches:
                        menswear_sellers[identifier] = identifier
                    elif len(matches) == 1:
                        menswear_sellers[identifier] = matches[0]
                    else:
                        current_app.logger.warning(
                            'Indian menswear could not match a unique seller record for %s.',
                            indian_menswear.SELLERS[identifier],
                        )
            menswear_items = [
                {**item, 'seller_id': menswear_sellers[item['seller_id']]}
                for item in indian_menswear.ITEMS if item['seller_id'] in menswear_sellers
            ]
            cursor.execute('SELECT catalog_key, item_id FROM curated_catalog_items FOR UPDATE')
            existing = {row['catalog_key']: row['item_id'] for row in cursor.fetchall()}
            batches = (
                ('nigerian', ASSET_ROOT, PRICE_NOTES, ITEMS),
                ('indian', indian_menswear.ASSET_ROOT, indian_menswear.PRICE_NOTES, menswear_items),
            )
            for culture, asset_root, price_notes, items in batches:
                for item in items:
                    if item['key'] in existing:
                        continue
                    image_url = '/' + asset_root + item['asset']
                    # Adopt a previously installed asset if its mapping was lost.
                    cursor.execute('SELECT item_id, seller_id FROM items WHERE image_url = %s FOR UPDATE', (image_url,))
                    matches = cursor.fetchall()
                    if len(matches) > 1 or (matches and matches[0]['seller_id'] != item['seller_id']):
                        raise Error(msg='A catalog photo has conflicting item records. Existing rows were preserved.')
                    if matches:
                        item_id = matches[0]['item_id']
                    else:
                        cursor.execute('''INSERT INTO items
                            (seller_id,culture_id,item_name,description,category,price,image_url,purchase_url,price_notes,color,size)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                            (item['seller_id'], cultures[culture], item['name'], item['description'],
                             item['category'], item.get('price', 0), image_url, None, price_notes,
                             item['colors'], item.get('size', 'Custom Sizes')))
                        item_id = cursor.lastrowid
                        for occasion in item['occasions']:
                            cursor.execute('INSERT INTO itemoccasions (item_id,occasion_id) VALUES (%s,%s)', (item_id, occasions[occasion.casefold()]))
                    cursor.execute('INSERT INTO curated_catalog_items (catalog_key,item_id) VALUES (%s,%s)', (item['key'], item_id))
            connection.commit()
            current_app.extensions[_READY] = True
        except Exception:
            connection.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()
