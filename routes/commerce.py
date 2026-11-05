"""Buyer-only native forms plus immediate Add-to-cart badge updates."""
from functools import wraps
import hmac
import secrets
from flask import Blueprint,current_app,flash,g,jsonify,redirect,render_template,request,session,url_for
from mysql.connector import Error
from services import commerce
from services.profiles import get_buyer_profile
from services.products import get_product_by_id

shop_bp=Blueprint('shop',__name__)


def problem(message,status=400):
    if request.accept_mimetypes.best=='application/json': return jsonify(error=message),status
    return render_template('commerce/message.html',message=message),status


def buyer_required(view):
    @wraps(view)
    def wrapped(*args,**kwargs):
        if g.user is None:
            if request.accept_mimetypes.best=='application/json': return jsonify(error='Log in with a buyer account to shop.'),401
            flash('Log in with a buyer account to shop through CultureLink.','info')
            return redirect(url_for('auth.login'),code=303 if request.method=='POST' else 302)
        if g.user['role']=='pending': return redirect(url_for('onboarding.choose_role'),code=303 if request.method=='POST' else 302)
        if g.user['role']!='customer': return problem('Shopping is available with a buyer account.',403)
        try:
            g.shopping_profile=get_buyer_profile(g.user['user_id'])
            if g.shopping_profile is None: return redirect(url_for('onboarding.buyer_profile'),code=303 if request.method=='POST' else 302)
            return view(*args,**kwargs)
        except commerce.ShoppingError as error: return problem(str(error),error.status)
        except Error:
            current_app.logger.warning('Could not load or save the current buyer shopping workspace.')
            return problem("We couldn't save or load this page. Your saved cart and orders are preserved. Please try again.",503)
    return wrapped


@shop_bp.app_context_processor
def shopping_helpers():
    def money(value):
        from decimal import Decimal
        return f'{Decimal(str(value)):,.2f}'
    def count():
        if not g.user or g.user['role']!='customer': return 0
        if not hasattr(g,'_shopping_count'):
            try: g._shopping_count=commerce.cart_count(g.user['user_id'])
            except Error:
                current_app.logger.warning('Could not read the buyer cart count.'); g._shopping_count=None
        return g._shopping_count
    return {'shopping_money':money,'purchase_options':commerce.purchase_options,'shopping_cart_count':count}


@shop_bp.route('/cart')
@buyer_required
def cart(): return render_template('commerce/cart.html',cart=commerce.cart_for(g.user['user_id']))


@shop_bp.route('/cart/count')
@buyer_required
def count(): return jsonify(count=commerce.cart_count(g.user['user_id']))


def added(message):
    if request.accept_mimetypes.best=='application/json':
        return jsonify(count=commerce.cart_count(g.user['user_id']),message=message)
    flash(message,'success'); return redirect(url_for('products.shop.cart'),code=303)


@shop_bp.route('/cart/add/<int:product_id>',methods=['POST'])
@buyer_required
def add(product_id):
    commerce.add_product(g.user['user_id'],product_id,request.form.get('size',''))
    return added('Your piece is in the cart. You can change its quantity there.')


@shop_bp.route('/cart/lines/<int:line_id>/update',methods=['POST'])
@buyer_required
def update(line_id):
    commerce.update_line(g.user['user_id'],line_id,request.form.get('quantity',''),request.form.get('size',''),request.form.get('version',''))
    flash('Your cart is updated.','success'); return redirect(url_for('products.shop.cart'),code=303)


@shop_bp.route('/cart/lines/<int:line_id>/remove',methods=['POST'])
@buyer_required
def remove(line_id):
    commerce.remove_line(g.user['user_id'],line_id)
    flash('The piece is removed from your cart.','success'); return redirect(url_for('products.shop.cart'),code=303)


def _token(digest):
    tokens=session.get('_demo_checkout_tokens',[])
    tokens=tokens if isinstance(tokens,list) else []
    for token in tokens:
        if isinstance(token,dict) and token.get('digest')==digest: return token['key']
    key=secrets.token_hex(24); tokens.append({'key':key,'digest':digest})
    session['_demo_checkout_tokens']=tokens[-5:]; return key


def _checkout_page(cart,values,error='',status=200):
    return render_template('commerce/checkout.html',cart=cart,values=values,error=error,request_key=_token(cart['digest'])),status


@shop_bp.route('/checkout',methods=['GET','POST'])
@buyer_required
def checkout():
    user_id=g.user['user_id']
    if request.method=='POST':
        key=request.form.get('request_key',''); digest=request.form.get('cart_digest','')
        allowed=any(isinstance(t,dict) and t.get('key')==key and digest.isascii() and hmac.compare_digest(t.get('digest',''),digest)
                    for t in session.get('_demo_checkout_tokens',[]))
        if not allowed: raise commerce.ShoppingError('Open checkout from your cart before placing a demo order.')
        try: order_id=commerce.place_order(user_id,key,request.form.get('version',''),digest,request.form)
        except commerce.ShoppingError as error:
            if error.status!=400: raise
            cart=commerce.cart_for(user_id)
            if cart['blocked']: raise
            return _checkout_page(cart,request.form,str(error),400)
        return redirect(url_for('products.shop.order',order_id=order_id),code=303)
    cart=commerce.cart_for(user_id)
    if cart['blocked']:
        flash('Review your cart before starting checkout.','info'); return redirect(url_for('products.shop.cart'))
    return _checkout_page(cart,{name:g.shopping_profile.get(name) or '' for name in commerce.DELIVERY_FIELDS})


@shop_bp.route('/orders')
@buyer_required
def orders():
    orders,quotes=commerce.history_for(g.user['user_id'])
    return render_template('commerce/orders.html',orders=orders,quotes=quotes)


@shop_bp.route('/orders/<int:order_id>')
@buyer_required
def order(order_id): return render_template('commerce/order.html',order=commerce.order_for(g.user['user_id'],order_id))


@shop_bp.route('/quotes/new/<int:product_id>',methods=['GET','POST'])
@buyer_required
def quote_new(product_id):
    product=get_product_by_id(product_id)
    if product is None: raise commerce.ShoppingNotFound('This piece is no longer available.')
    if not commerce.purchase_options(product)['requires_quote']: return redirect(url_for('products.product_details',product_id=product_id))
    values={name:g.shopping_profile.get(name) or '' for name in ('chest','waist','hips','height','measurement_unit')}
    values['notes']=''; key=secrets.token_hex(16); error=''; status=200
    if request.method=='POST':
        values=request.form; key=request.form.get('request_key','')
        try: quote_id=commerce.create_quote(g.user['user_id'],product_id,key,request.form)
        except commerce.ShoppingError as failure:
            if failure.status!=400: raise
            error,status=str(failure),400
        else: return redirect(url_for('products.shop.quote',quote_id=quote_id),code=303)
    return render_template('commerce/quote_form.html',product=product,values=values,error=error,request_key=key),status


@shop_bp.route('/quotes/<int:quote_id>')
@buyer_required
def quote(quote_id): return render_template('commerce/quote.html',quote=commerce.quote_for(g.user['user_id'],quote_id))


@shop_bp.route('/quotes/<int:quote_id>/preview',methods=['POST'])
@buyer_required
def quote_preview(quote_id):
    commerce.preview_quote(g.user['user_id'],quote_id)
    return redirect(url_for('products.shop.quote',quote_id=quote_id),code=303)


@shop_bp.route('/quotes/<int:quote_id>/accept',methods=['POST'])
@buyer_required
def quote_accept(quote_id):
    commerce.accept_quote(g.user['user_id'],quote_id)
    return added('Your sample quote is accepted and the custom piece is in your cart.')
