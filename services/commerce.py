"""Private carts, custom sample quotes and simulated orders. No payment or mail."""
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import hmac
import json
import re
from threading import Lock
from flask import current_app
from mysql.connector import Error
from database import get_db_connection
from services.catalog_rules import CUSTOM_SIZE, SELLER_LOCATION_SQL, size_labels
from services.products import format_product
from services.seller_review_schema import PUBLIC_SELLER_SQL

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS buyer_cart_state (
        user_id INT UNSIGNED NOT NULL, version INT UNSIGNED NOT NULL DEFAULT 1,
        PRIMARY KEY (user_id),
        CONSTRAINT fk_demo_cart_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
    """CREATE TABLE IF NOT EXISTS buyer_quotes (
        quote_id INT UNSIGNED NOT NULL AUTO_INCREMENT, user_id INT UNSIGNED NOT NULL,
        product_id INT UNSIGNED NOT NULL, request_key CHAR(32) NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'requested', measurements TEXT NOT NULL,
        notes TEXT NOT NULL, product_json TEXT NOT NULL, product_signature CHAR(64) NOT NULL,
        amount DECIMAL(12,2) DEFAULT NULL, currency CHAR(3) NOT NULL DEFAULT '',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (quote_id), UNIQUE KEY uq_demo_quote_request (user_id, request_key),
        CONSTRAINT fk_demo_quote_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
    """CREATE TABLE IF NOT EXISTS buyer_cart_lines (
        line_id INT UNSIGNED NOT NULL AUTO_INCREMENT, user_id INT UNSIGNED NOT NULL,
        product_id INT UNSIGNED NOT NULL, line_key CHAR(64) NOT NULL,
        quote_id INT UNSIGNED NOT NULL DEFAULT 0, size_choice VARCHAR(100) NOT NULL,
        quantity INT UNSIGNED NOT NULL DEFAULT 1, unit_price DECIMAL(12,2) NOT NULL,
        currency CHAR(3) NOT NULL, product_signature CHAR(64) NOT NULL,
        PRIMARY KEY (line_id), UNIQUE KEY uq_demo_cart_line (user_id, line_key),
        CONSTRAINT fk_demo_line_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
    """CREATE TABLE IF NOT EXISTS buyer_demo_orders (
        order_id INT UNSIGNED NOT NULL AUTO_INCREMENT, user_id INT UNSIGNED NOT NULL,
        request_key CHAR(48) NOT NULL, receipt_json MEDIUMTEXT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (order_id), UNIQUE KEY uq_demo_order_request (user_id, request_key),
        CONSTRAINT fk_demo_order_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
)
TABLES = ('buyer_cart_state','buyer_quotes','buyer_cart_lines','buyer_demo_orders')
MAX_LINES, MAX_QUANTITY = 40, 10
# Verified ECB information-only snapshot, 3 November 2026. EUR 1 = USD
# 1.1179 and INR 105.9155. The dated snapshot works without an API or key.
FX_SNAPSHOT = {'date':'2026-11-03','label':'Nov 3, 2026','source':'European Central Bank',
    'source_url':'https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html',
    'usd_per_inr':str(Decimal('1.1179') / Decimal('105.9155'))}
_schema_lock = Lock()


class ShoppingError(ValueError): status = 400
class ShoppingAccess(ShoppingError): status = 403
class ShoppingNotFound(ShoppingError): status = 404
class ShoppingConflict(ShoppingError): status = 409


def ensure_schema():
    if current_app.extensions.get('culturelink_commerce_ready'): return
    with _schema_lock:
        if current_app.extensions.get('culturelink_commerce_ready'): return
        connection = get_db_connection(); cursor = None
        try:
            cursor = connection.cursor(dictionary=True)
            try:
                for table in TABLES:
                    cursor.execute('SELECT * FROM '+table+' LIMIT 0'); cursor.fetchall()
            except Error as error:
                if error.errno != 1146: raise
                # DDL implicitly commits in MySQL: use an isolated connection.
                for statement in SCHEMA: cursor.execute(statement)
                connection.commit()
            current_app.extensions['culturelink_commerce_ready'] = True
        finally:
            if cursor is not None: cursor.close()
            connection.close()


@contextmanager
def database(write=False):
    ensure_schema(); connection = get_db_connection(); cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        yield connection, cursor
    except Exception:
        if write: connection.rollback()
        raise
    finally:
        if cursor is not None: cursor.close()
        connection.close()


def _json(value): return json.dumps(value,sort_keys=True,ensure_ascii=False,default=str,separators=(',',':'))
def _digest(value): return hashlib.sha256(_json(value).encode()).hexdigest()


def _number(value, label, maximum=4294967295):
    text = str(value)
    if not re.fullmatch(r'[0-9]{1,10}',text) or not 1 <= int(text) <= maximum:
        raise ShoppingError('Choose a valid '+label+'.')
    return int(text)


def _key(value,length):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{'+str(length)+'}',value):
        raise ShoppingError('Refresh this form before submitting again.')
    return value


def usd_amount(amount,currency):
    if currency not in {'USD','INR'}: raise ShoppingError('Confirm the currency before checkout.')
    rate = Decimal(FX_SNAPSHOT['usd_per_inr']) if currency == 'INR' else Decimal('1')
    return (Decimal(str(amount))*rate).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)


def _lock_buyer(cursor,user_id):
    cursor.execute('SELECT role FROM users WHERE user_id=%s FOR UPDATE',(user_id,)); user=cursor.fetchone()
    if not user or user['role'] != 'customer': raise ShoppingAccess('Use a buyer account to shop.')
    cursor.execute('SELECT user_id FROM buyer_profiles WHERE user_id=%s FOR UPDATE',(user_id,))
    if cursor.fetchone() is None: raise ShoppingConflict('Finish your buyer profile before shopping.')


def _state(cursor,user_id,create=False):
    cursor.execute('SELECT version FROM buyer_cart_state WHERE user_id=%s'+(' FOR UPDATE' if create else ''),(user_id,)); row=cursor.fetchone()
    if row: return row['version']
    if create: cursor.execute('INSERT INTO buyer_cart_state (user_id) VALUES (%s)',(user_id,))
    return 1


def _touch(cursor,user_id): cursor.execute('UPDATE buyer_cart_state SET version=version+1 WHERE user_id=%s',(user_id,))


def _product(cursor,product_id,lock=False):
    product_id=_number(product_id,'piece')
    if lock:
        cursor.execute('SELECT seller_id FROM items WHERE item_id=%s FOR UPDATE',(product_id,)); item=cursor.fetchone()
        if item:
            cursor.execute('SELECT verification_status FROM seller_profiles WHERE seller_id=%s FOR UPDATE',(item['seller_id'],)); owner=cursor.fetchone()
            if owner and owner['verification_status'] != 'approved': raise ShoppingNotFound('This piece is unavailable.')
    cursor.execute(f"""SELECT i.item_id AS product_id,i.item_name AS product_name,i.description,
        i.category AS clothing_type,i.price,i.price_notes,i.image_url,i.color,i.size,
        i.seller_id AS boutique_id,s.seller_name AS boutique_name,{SELLER_LOCATION_SQL} AS seller_location,
        c.culture_name AS culture,'' AS occasion FROM items i JOIN sellers s ON s.seller_id=i.seller_id
        JOIN cultures c ON c.culture_id=i.culture_id WHERE i.item_id=%s AND {PUBLIC_SELLER_SQL}"""+(' FOR UPDATE' if lock else ''),(product_id,))
    product=cursor.fetchone()
    if product is None: raise ShoppingNotFound('This piece is no longer available in the catalog.')
    return format_product(product)


def purchase_options(product):
    sizes=[s for s in size_labels(product.get('size')) if s != CUSTOM_SIZE]
    return {'sizes':sizes,'requires_quote':bool(product.get('custom_size') or not sizes or not product.get('price')
        or product['price'] <= 0 or product.get('price_currency') not in {'USD','INR'})}


def _signature(product):
    return _digest({key:product.get(key) for key in ('product_id','product_name','boutique_id','size','color','price','price_currency','custom_size')})


def _summary(product):
    return {key:product.get(key) for key in ('product_id','product_name','boutique_id','boutique_name',
        'image_url','color','culture','display_size','display_production_time','display_shipping_time','display_total_time')}


def _quote(cursor,user_id,quote_id,lock=False):
    cursor.execute('SELECT * FROM buyer_quotes WHERE quote_id=%s AND user_id=%s'+(' FOR UPDATE' if lock else ''),(_number(quote_id,'quote'),user_id))
    quote=cursor.fetchone()
    if quote is None: raise ShoppingNotFound('This quote is not available in your account.')
    quote['product']=json.loads(quote['product_json']); quote['measurements']=json.loads(quote['measurements'])
    return quote


def _cart(cursor,user_id,lock=False):
    version=_state(cursor,user_id,create=lock)
    cursor.execute('SELECT * FROM buyer_cart_lines WHERE user_id=%s ORDER BY line_id'+(' FOR UPDATE' if lock else ''),(user_id,))
    rows=cursor.fetchall(); lines=[]; total=Decimal('0.00'); has_conversion=False
    for line in rows:
        line['problem']=''; line['sizes']=[]
        try:
            product=_product(cursor,line['product_id'],lock)
            line['product']=_summary(product); line['sizes']=purchase_options(product)['sizes']
            if line['product_signature'] != _signature(product): line['problem']='Details changed. Update or remove this piece before checkout.'
            if line['quote_id']:
                quote=_quote(cursor,user_id,line['quote_id'],lock)
                if (quote['status'] != 'offered' or quote['product_id'] != line['product_id'] or
                    quote['product_signature'] != _signature(product) or line['quantity'] != 1 or
                    Decimal(str(quote['amount'] or 0)) != Decimal(str(line['unit_price'])) or quote['currency'] != line['currency']):
                    line['problem']='This sample quote is no longer available. Request a new quote.'
                line['measurements']=quote['measurements']
            elif purchase_options(product)['requires_quote'] or line['size_choice'] not in line['sizes']:
                line['problem']='Confirm the size or request a quote before checkout.'
            elif Decimal(str(line['unit_price'])) != Decimal(str(product['price'])) or line['currency'] != product['price_currency']:
                line['problem']='The price changed. Update this piece to review its current price.'
        except ShoppingNotFound:
            line['product']={'product_id':line['product_id'],'product_name':'Unavailable piece','image_url':'','boutique_name':''}
            line['problem']='This piece is unavailable. Remove it before checkout.'
        unit=usd_amount(line['unit_price'],line['currency'])
        line['unit_label']=f'USD {unit:,.2f}'; line['total_label']=f"USD {unit*line['quantity']:,.2f}"
        line['original_label']=f"{line['currency']} {Decimal(str(line['unit_price'])):,.2f} each" if line['currency'] != 'USD' else ''
        has_conversion=has_conversion or line['currency'] != 'USD'
        if not line['problem']: total+=unit*line['quantity']
        lines.append(line)
    fx=dict(FX_SNAPSHOT) if has_conversion else None
    payload=[{k:line.get(k) for k in ('line_id','quantity','size_choice','unit_price','currency','product_signature','quote_id','problem')} for line in lines]
    return {'version':version,'lines':lines,'usd_total':total,'fx':fx,
        'piece_count':sum(l['quantity'] for l in lines),'blocked':not lines or any(l['problem'] for l in lines),
        'digest':_digest({'version':version,'lines':payload,'fx':fx})}


def cart_for(user_id):
    with database() as (_,cursor): return _cart(cursor,user_id)


def cart_count(user_id):
    with database() as (_,cursor):
        cursor.execute('SELECT COALESCE(SUM(quantity),0) AS piece_count FROM buyer_cart_lines WHERE user_id=%s',(user_id,))
        return int(cursor.fetchone()['piece_count'])


def _add_line(cursor,user_id,product,size,amount,currency,quote_id=0):
    key=_digest([product['product_id'],size,quote_id])
    cursor.execute('SELECT line_id FROM buyer_cart_lines WHERE user_id=%s AND line_key=%s',(user_id,key))
    if cursor.fetchone(): return  # Duplicate Add never doubles the quantity.
    cursor.execute('SELECT COUNT(*) AS count FROM buyer_cart_lines WHERE user_id=%s',(user_id,))
    if cursor.fetchone()['count'] >= MAX_LINES: raise ShoppingError('Your cart can hold up to 40 different pieces.')
    cursor.execute('''INSERT INTO buyer_cart_lines
        (user_id,product_id,line_key,quote_id,size_choice,unit_price,currency,product_signature)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',(user_id,product['product_id'],key,quote_id,size,amount,currency,_signature(product)))
    _touch(cursor,user_id)


def add_product(user_id,product_id,size):
    with database(True) as (connection,cursor):
        _lock_buyer(cursor,user_id); _state(cursor,user_id,True); product=_product(cursor,product_id,True)
        options=purchase_options(product)
        if options['requires_quote']: raise ShoppingError('Request a quote before adding this piece to your cart.')
        if size not in options['sizes']: raise ShoppingError('Choose an available size for this piece.')
        _add_line(cursor,user_id,product,size,product['price'],product['price_currency']); connection.commit()


def update_line(user_id,line_id,quantity,size,version):
    quantity=_number(quantity,'quantity from 1 to 10',MAX_QUANTITY); version=_number(version,'cart version')
    with database(True) as (connection,cursor):
        _lock_buyer(cursor,user_id)
        if _state(cursor,user_id,True) != version: raise ShoppingConflict('Your cart changed in another tab. Refresh it before updating.')
        cursor.execute('SELECT * FROM buyer_cart_lines WHERE line_id=%s AND user_id=%s FOR UPDATE',(line_id,user_id)); line=cursor.fetchone()
        if line is None: raise ShoppingNotFound('This piece is not in your cart.')
        if line['quote_id']: raise ShoppingError('A custom quote covers one measured piece. Request a new quote to change it.')
        product=_product(cursor,line['product_id'],True); options=purchase_options(product)
        if options['requires_quote'] or size not in options['sizes']: raise ShoppingError('Choose an available size or request a quote.')
        key=_digest([product['product_id'],size,0])
        cursor.execute('SELECT line_id FROM buyer_cart_lines WHERE user_id=%s AND line_key=%s',(user_id,key)); other=cursor.fetchone()
        if other and other['line_id'] != line_id: raise ShoppingError('That size is already in your cart. Update its quantity there.')
        cursor.execute('''UPDATE buyer_cart_lines SET quantity=%s,size_choice=%s,line_key=%s,unit_price=%s,
            currency=%s,product_signature=%s WHERE line_id=%s AND user_id=%s''',
            (quantity,size,key,product['price'],product['price_currency'],_signature(product),line_id,user_id))
        _touch(cursor,user_id); connection.commit()


def remove_line(user_id,line_id):
    with database(True) as (connection,cursor):
        _lock_buyer(cursor,user_id); _state(cursor,user_id,True)
        cursor.execute('DELETE FROM buyer_cart_lines WHERE line_id=%s AND user_id=%s',(line_id,user_id))
        _touch(cursor,user_id); connection.commit()


def validate_measurements(values):
    unit=values.get('measurement_unit','in')
    if unit not in {'in','cm'}: raise ShoppingError('Choose inches or centimeters.')
    result={'measurement_unit':unit}
    for name in ('chest','waist','hips','height'):
        text=str(values.get(name,'')).strip()
        if not re.fullmatch(r'[0-9]{1,3}(?:\.[0-9]{1,2})?',text) or not 0 < Decimal(text) <= (200 if unit == 'in' else 500):
            raise ShoppingError('Add positive chest, waist, hips and height values in the selected unit, with up to two decimal places.')
        result[name]=str(Decimal(text))
    return result


def create_quote(user_id,product_id,key,values):
    key=_key(key,32); measurements=validate_measurements(values); notes=values.get('notes','').strip()
    if len(notes)>1500: raise ShoppingError('Keep notes within 1,500 characters.')
    with database(True) as (connection,cursor):
        _lock_buyer(cursor,user_id)
        cursor.execute('SELECT quote_id,product_id FROM buyer_quotes WHERE user_id=%s AND request_key=%s',(user_id,key)); old=cursor.fetchone()
        if old:
            if old['product_id'] != int(product_id): raise ShoppingConflict('Open a new quote form for this piece.')
            connection.commit(); return old['quote_id']
        product=_product(cursor,product_id,True)
        if not purchase_options(product)['requires_quote']: raise ShoppingError('This piece has listed sizes and a price. Add it directly to your cart.')
        cursor.execute("SELECT COUNT(*) AS count FROM buyer_quotes WHERE user_id=%s AND status <> 'purchased'",(user_id,))
        if cursor.fetchone()['count']>=100: raise ShoppingError('Your account already has 100 open sample requests.')
        cursor.execute('''INSERT INTO buyer_quotes (user_id,product_id,request_key,measurements,notes,product_json,product_signature)
            VALUES (%s,%s,%s,%s,%s,%s,%s)''',(user_id,product['product_id'],key,_json(measurements),notes,_json(_summary(product)),_signature(product)))
        quote_id=cursor.lastrowid; connection.commit(); return quote_id


def quote_for(user_id,quote_id):
    with database() as (_,cursor): return _quote(cursor,user_id,quote_id)


def preview_quote(user_id,quote_id):
    with database(True) as (connection,cursor):
        _lock_buyer(cursor,user_id); quote=_quote(cursor,user_id,quote_id,True); product=_product(cursor,quote['product_id'],True)
        if quote['product_signature'] != _signature(product): raise ShoppingConflict('This piece changed. Request a new quote.')
        if quote['status']=='purchased': raise ShoppingConflict('This sample quote has already been used.')
        if quote['status']=='requested':
            # Invented classroom examples, explicitly labeled in the UI.
            amount = Decimal(product["sample_quote_usd"] or 150 + (quote["product_id"] % 9) * 25)
            cursor.execute("UPDATE buyer_quotes SET status='offered',amount=%s,currency='USD' WHERE quote_id=%s AND user_id=%s",(amount,quote_id,user_id))
        connection.commit()


def accept_quote(user_id,quote_id):
    with database(True) as (connection,cursor):
        _lock_buyer(cursor,user_id); _state(cursor,user_id,True); quote=_quote(cursor,user_id,quote_id,True)
        product=_product(cursor,quote['product_id'],True)
        if quote['status']!='offered' or quote['product_signature']!=_signature(product): raise ShoppingConflict('Preview an available sample quote before accepting it.')
        _add_line(cursor,user_id,product,CUSTOM_SIZE,quote['amount'],quote['currency'],quote_id); connection.commit()


DELIVERY_FIELDS={'full_name':150,'address_line1':255,'address_line2':255,'city':100,'state':100,'postal_code':30,'country':100,'phone':40}


def validate_delivery(values):
    result={name:str(values.get(name,'')).strip() for name in DELIVERY_FIELDS}
    for name,maximum in DELIVERY_FIELDS.items():
        if len(result[name])>maximum or any(ord(c)<32 for c in result[name]): raise ShoppingError('Check your delivery details and field lengths.')
    if any(not result[name] for name in ('full_name','address_line1','city','postal_code','country')): raise ShoppingError('Add your name, street address, city, postal code and country.')
    if values.get('demo_acknowledged')!='yes': raise ShoppingError('Confirm that this is a simulated order with no payment or shipping.')
    return result


def place_order(user_id,key,version,digest,values):
    key=_key(key,48); version=_number(version,'cart version'); digest=_key(digest,64); delivery=validate_delivery(values)
    with database(True) as (connection,cursor):
        _lock_buyer(cursor,user_id)
        cursor.execute('SELECT order_id FROM buyer_demo_orders WHERE user_id=%s AND request_key=%s',(user_id,key)); old=cursor.fetchone()
        if old: connection.commit(); return old['order_id']
        cart=_cart(cursor,user_id,True)
        if cart['blocked'] or cart['version']!=version or not hmac.compare_digest(cart['digest'],digest): raise ShoppingConflict('Your cart or a piece changed. Review your cart before placing a demo order.')
        receipt={'delivery':delivery,'placed_at':datetime.now().strftime('%b %d, %Y at %I:%M %p'),
            'usd_total':str(cart['usd_total']),'fx':cart['fx'],'lines':[
                {k:line.get(k) for k in ('product','quantity','size_choice','quote_id','unit_label','total_label','original_label','measurements')} for line in cart['lines']]}
        cursor.execute('INSERT INTO buyer_demo_orders (user_id,request_key,receipt_json) VALUES (%s,%s,%s)',(user_id,key,_json(receipt)))
        order_id=cursor.lastrowid
        for line in cart['lines']:
            if line['quote_id']: cursor.execute("UPDATE buyer_quotes SET status='purchased' WHERE quote_id=%s AND user_id=%s",(line['quote_id'],user_id))
        cursor.execute('DELETE FROM buyer_cart_lines WHERE user_id=%s',(user_id,)); _touch(cursor,user_id)
        connection.commit(); return order_id


def order_for(user_id,order_id):
    with database() as (_,cursor):
        cursor.execute('SELECT * FROM buyer_demo_orders WHERE order_id=%s AND user_id=%s',(order_id,user_id)); order=cursor.fetchone()
        if order is None: raise ShoppingNotFound('This order is not available in your account.')
        order['receipt']=json.loads(order['receipt_json']); order['reference']=f"CL-DEMO-{order['order_id']:06d}"
        return order


def history_for(user_id):
    with database() as (_,cursor):
        cursor.execute('SELECT order_id,created_at FROM buyer_demo_orders WHERE user_id=%s ORDER BY order_id DESC LIMIT 50',(user_id,)); orders=cursor.fetchall()
        cursor.execute('SELECT quote_id,product_json,status,created_at FROM buyer_quotes WHERE user_id=%s ORDER BY quote_id DESC LIMIT 100',(user_id,)); quotes=cursor.fetchall()
    for order in orders: order['reference']=f"CL-DEMO-{order['order_id']:06d}"
    for quote in quotes: quote['product']=json.loads(quote['product_json'])
    return orders,quotes
