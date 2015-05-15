function showVisualization() {

    $.get('/visualization', function(user_orders_json) {
      $("#display-div").append(
        user_orders_json["user_gmail"]);
        for (var i = 0; i < user_orders_json["orders"].length; i++)  {
          $("#display-div").append(
          user_orders_json["orders"][i]["amazon_fresh_order_id"]);
          }

      }

    );

  }

showVisualization()
