"""Models and database functions for Fresh Look"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy

class Order(db.Model):
    """Amazon Fresh Order"""

    __tablename__ = "orders"

    amazon_fresh_order_id = db.Column(db.String(30), primary_key=True)
    delivery_date = db.Column(db.DateTime, nullable=False)
    delivery_day_of_week = db.Column(db.String(10), nullable=False)
    delivery_time = db.Column(db.String(30), nullable=False)
    user_gmail = db.Column(db.String(64), db.ForeignKey('users.user_gmail'), nullable=False)

    user = db.relationship("User", backref=backref("orders", order_by=amazon_fresh_order_id)


    def __repr__(self):
        """Representation string"""

        return "<Order amazon_fresh_order_id=%s>" % self.amazon_fresh_order_id

class OrderLineItem(db.Model):
    """Line item from actual Amazon Fresh Order"""

    ___tablename__ = "order_line_items"

    order_line_item_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    amazon_fresh_order_id = db.Column(db.String(30), db.ForeignKey('orders.amazon_fresh_order_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.item_id'), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", backref=backref("order_line_items", order_by=order_line_item_id))
    item = db.relationsip("Item", backref=backref("items", order_by=item_id))


    def __repr__(self):
        """Representation string"""

        return "<OrderLineItem order_line_item_id=%d unit_price=%f qty=%d>" %   (self.order_line_item_id,
                                                                                self.unit_price,
                                                                                self.quantity)

class Item(db.Model):
    """Item that can be in an Amazon Fresh Order"""

    __tablename__ = "items"

    item_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    description = db.Column(db.String(150), nullable=False)

    saved_carts = db.relationship("SavedCarts", secondary=SavedCartItem, backref="items")

    def __repr__(self):
        """Representation string"""

        return "<Item item_id=%d description=%s>" % (self.item_id, self.description)

class SavedCartItem(db.Model):
    """Association between Item and SavedCart"""

    ___tablename__ = "saved_carts_items"

    saved_cart_item = db.Column(db.Integer, autoincrement=True, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.item_id"), nullable=False)
    saved_cart_id = db.Column(db.Integer, db.ForeignKey("saved_carts.saved_cart_id"), nullable=False)

class SavedCart(db.Model):
    """Cart saved by User"""

    __tablename__ = "saved_carts"

    saved_cart_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_gmail = db.Column(db.String(64), db.ForeignKey("users.user_gmail"), nullable=False)

    user = db.relationship("User", backref=backref("saved_carts", order_by=saved_cart_id))

class User(db.Model):
    """Amazon Fresh user whose orders are being pulled in from Gmail"""

    ___tablename__ = "users"

    user_gmail = db.Column(db.String(64), primary_key=True)
    access_token = db.Column(db.String(150), nullable=False)
    saved_cart_id = db.Column(db.Integer, db.ForeignKey("saved_carts.saved_cart_id"), nullable=True)
    
