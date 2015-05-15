function showVisualization() {

      console.log("showVisualization ran")

    $.get('/visualization', function(user_orders_json) {
      $("#display-div").html(
        user_orders_json["user_gmail"]
        // user_orders_json["orders"]
        );
      }

    );

  }

showVisualization()
