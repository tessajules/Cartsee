function showVisualization() {

      console.log("showVisualization ran")

    $.get('/visualization', function(result) {
      $("#display-div").html(
        result
        );
      }

    );

  }

showVisualization()
