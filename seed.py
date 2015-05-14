"""Utility file to seed freshlook database from parsed email message data"""

from model import Order, OrderLineItem, SavedCartItem, Item, SavedCart, User, connect_to_db, db
from server import app

def store_user():
    """Stores authenticated gmail user"""

    
