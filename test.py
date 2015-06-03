import unittest

from model import Order, Item, OrderLineItem, User
from model import db

from server import app, connect_to_db

from datetime import datetime


class OrderTestCase(unittest.TestCase):
    def setUp(self):

        test_gmail = "test1@gmail.com"
        date_string = "16 November 2014"
        delivery_date = datetime.strptime(date_string, "%d %B %Y")
        amazon_fresh_order_id = "test1"

        self.user = User(user_gmail=test_gmail, access_token="test_token")

        db.session.add(self.user)


        self.order = Order(amazon_fresh_order_id=amazon_fresh_order_id,
                           delivery_date=delivery_date,
                           delivery_day_of_week="Sunday",
                           delivery_time="10:00am - 1:00pm",
                           user_gmail=test_gmail)

        db.session.add(self.order)


        self.item = Item(description="Test item",
                         description_key="testitem")

        db.session.add(self.item)
        db.session.flush()

        self.order_line_item = OrderLineItem(amazon_fresh_order_id=amazon_fresh_order_id,
                                             item_id=self.item.item_id,
                                             unit_price_cents=100,
                                             quantity=1)

        db.session.add(self.order_line_item)

        db.session.flush()

    def tearDown(self):
        db.session.rollback()
        # db.session.remove() will work as well.



    def test_calc_order_total(self):
        order = Order.query.filter_by(amazon_fresh_order_id="test1").one()
        self.assertEqual(order.calc_order_total(), 100)

    def test_calc_order_quantity(self):
        order = Order.query.filter_by(amazon_fresh_order_id="test1").one()
        self.assertEqual(order.calc_order_quantity(), 1)




if __name__ == "__main__":
    connect_to_db(app, db, "freshstats.db")
    unittest.main()
