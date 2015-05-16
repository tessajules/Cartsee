function showVisualization() {

    $.get('/visualization', function(user_orders_json) {
      $("#display-div").append(
        "<h3>" + user_orders_json["user_gmail"] + "</h3>");
        $("#display-div").append("<ol>");
        for (var i = 0; i < user_orders_json["orders"].length; i++)  {
          $("#display-div").append(
          "<li>" + "Order # " +
          user_orders_json["orders"][i]["amazon_fresh_order_id"] +
            "<ul>" +
              "<li>" + "delivery date: " + user_orders_json["orders"][i]["delivery_date"] + "</li>" +
              "<li>" + "delivery time: " + user_orders_json["orders"][i]["delivery_time"] + "</li>" +
              "<li id='order_line_items" + i.toString() + "'>order line items</li>"
          + "</ul>"
        + "</li>" );
        $("#display-div").append("<ol>");

        for (var j = 0; j < user_orders_json["orders"][i]["order_line_items_serialized"].length; j++) {
          console.log(user_orders_json["orders"][i]["amazon_fresh_order_id"]);
          console.log("j equals " + j);
          $("#order_line_items" + i.toString()).append(
            user_orders_json["orders"][i]["order_line_items_serialized"][j]["amazon_fresh_order_id"]
           + "<br>"
          );
        }


          // + user_orders_json["orders"][i]["order_line_items_serialized"][0]["amazon_fresh_order_id"]
          // + "<br>"
          // + user_orders_json["orders"][i]["order_line_items_serialized"][0]["unit_price"]


          }



      }

    );

  }

showVisualization()
