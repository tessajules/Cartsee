$(document).ajaxStart(function() {
  NProgress.configure({showSpinner: false})
  NProgress.start();
})


$(document).ajaxStop(function() {
  NProgress.done();
})

$(document).ready(function () {
    $('#date-input').datepicker({dateFormat:'mm/dd/yy', minDate:1, maxDate:10});
    }
);

$(document).ready(function () {
    $('#min-date').datepicker({dateFormat:'mm/dd/yy'});
    }
);

$(document).ready(function () {
    $('#max-date').datepicker({dateFormat:'mm/dd/yy'});
    $('#area-date').datepicker({dateFormat:'mm/dd/yy'});
    }
);



$('#date-input').on('change', function () {
  $('#predict-submit').removeAttr('disabled');
});

var socket = io.connect('http://' + document.domain + ':' + location.port + '/loads');

socket.on('connect', function() {
    socket.emit('start_loading', {data: 'proceed'});
});

socket.on('my response', function(data) {
var numOrderString = "<p class='loading-data'>" + data.num_orders + "</p>";
var numItemString = "<p class='loading-data'>" + data.quantity + "</p>";
var orderTotalString = "<p class='loading-data'>$" + (data.order_total/100).toFixed(2) + "</p>";
var percentComplete = (data.num_orders/data.total_num_orders * 100).toFixed(2)
var fetchingString = ("<p id='fetching'> Fetching order " + data.num_orders + "/" + data.total_num_orders + "</p>")
var progressBar = '<div class="progress-bar progress-bar-success" role="progressbar" aria-valuenow="40" aria-valuemin="0" aria-valuemax="100" style="width:'+ percentComplete + '%">'


  $("#fetching").html(fetchingString);
  $("#numorders-display").html(numOrderString);
  $("#quantity-display").html(numItemString);
  $("#total-display").html(orderTotalString);
  $("#percent-display").html(progressBar)

    if (data.status === "done") {
      var numOrderString = "<p class='loaded-data'>" + data.num_orders + "</p>";
      var numItemString = "<p class='loaded-data'>" + data.quantity + "</p>";
      var orderTotalString = "<p class='loaded-data'>$" + (data.order_total/100).toFixed(2) + "</p>";


      $("#numorders-loaded").html(numOrderString);
      $("#quantity-loaded").html(numItemString);
      $("#total-loaded").html(orderTotalString);




      listOrders();
      showAreaChart('/orders_over_time');
      showBubbleChart('/items_by_qty');
      showHistogram();
      showSavedCart();
      $(".loading-display").removeClass("show");
      $(".data-display").addClass("show");
      $(".display-div").hide();
      $("#bubble-display").show();
      // $("#carts").addClass("show");
      $(".predict").hide();
      $("#carts").show();
      $("#recommended").removeClass("show");

    }
});

    function showSavedCart() {



      $.get('/saved_cart', function(json) {
        if (json.saved_cart.length === 0) {
          $("#predict-display").empty();
          $("#saved-table").empty();
          $("#predict-table").empty();
          $(".keep-saved").hide();



        $("#saved-table").append("<h3>You currently have no saved items in your cart.</h3>")
        } else {
          $("#saved-table").empty();
          $(".keep-saved").show();
          $("#predict-title").html("<h3>Your current saved items:</h3>");

        $("#saved-table").append(
          "<thead><tr><th>Item description</th><th>Unit price</th><th></th><th></th></tr></thead>");

          var saved_cart = json.saved_cart;

            $.each(saved_cart, function(i, item) {
              var $tr = $('#saved-table').append(
                $('<tr>').addClass('item').attr('id', item.item_id).attr('data-item_id', item.item_id).append(
                  $('<td class="description-td">').text(item.description),
                  $('<td class="price-td">').text("$" + (item.unit_price/100).toFixed(2)),
                  $('<td class="del-td">').html("<button class='del-primary' id='del-" + item.item_id
                                 + "' onClick='delete_item(" + item.item_id + ")'>Delete</button>"),
                 $('<td class="amazon">').html("<a href='https://fresh.amazon.com/Search?input=" + encodeURIComponent(item.description) + "' target='_blank'>"
                                + "<img src='http://g-ec2.images-amazon.com/images/G/01/omaha/images/badges/af-badge-160x50.png' height=20px alt='AmazonFresh button'>"
                                + "</a>")
            ));});}});}

    function showPredictedCart(evt) {



      $(".cart-button").removeClass("show");

        evt.preventDefault();

        $("#control-table").empty();
        $("#saved-table").empty();


        $.get('/saved_cart', function(json) {

          var keep_saved = $("#keep-saved").val();



            $("#predict-title").html("<h3>Predicted Items:</h3>");
            $("#saved-table").append(

              "<tr><th>Item description</th><th>Unit price</th><th></th><th></th></tr>");

              if ($("#keep-saved").prop("checked")) {

              var saved_cart = json.saved_cart;

                $.each(saved_cart, function(i, item) {
                  var $tr = $('#saved-table').append(
                    $('<tr>').addClass('item').attr('id', item.item_id).attr('data-item_id', item.item_id).append(
                      $('<td class="description-td">').text(item.description),
                      $('<td class="price-td">').text("$" + (item.unit_price/100).toFixed(2)),
                      $('<td class="del-td">').html("<button class='del-primary' id='del-" + item.item_id
                                     + "' onClick='delete_item(" + item.item_id + ")'>Delete</button>"),
                     $('<td class="amazon">').html("<a href='https://fresh.amazon.com/Search?input=" + encodeURIComponent(item.description) + "' target='_blank'>"
                                    + "<img src='http://g-ec2.images-amazon.com/images/G/01/omaha/images/badges/af-badge-160x50.png' height=20px alt='AmazonFresh button'>"
                                    + "</a>")
                ));});

          }});

          var url = "/predict_cart?" + $("#date-form").serialize();


          $.get(url, function(json) {

            var primary_cart = json.primary_cart; // [{"description": "blah", "unit_price": 500}, ...]
            var backup_cart = json.backup_cart;
            var prediction_tree = json.prediction_tree;

            showPredictionTree(prediction_tree);

                $.each(primary_cart, function(i, item) {
                    var $tr = $('#saved-table').append(
                        $('<tr>').addClass('item-new').attr('id', item.item_id).attr('data-item_id', item.item_id).append(
                        $('<td class="description-td">').text(item.description),
                        $('<td class="price-td">').text("$" + (item.unit_price/100).toFixed(2)),
                        $('<td class="price-td">').html("<button class='del-primary' id='del-" + item.item_id
                                       + "' onClick='delete_item(" + item.item_id + ")'>Delete</button>"),
                        $('<td class="amazon">').html("<a href='https://fresh.amazon.com/Search?input=" + encodeURIComponent(item.description) + "' target='_blank'>"
                                       + "<img src='http://g-ec2.images-amazon.com/images/G/01/omaha/images/badges/af-badge-160x50.png' height=20px alt='AmazonFresh button'>"
                                       + "</a>")
                      )
                    );
                });
            $(".recommended-header-div").empty();
            $("#tree-button-div").empty();
            $("#tree-button-div").append('<button class="btn btn-link tree-button" id="view-tree">View prediction tree</button>');
            $("#recommended-title").append('<h4>More recommended items</h4>');
            $("#recommended-search").append('<div class="@@rec-search"><input type="text" class="backup-search" id="backup-search" placeholder="Search recommended items"></div>');
            $("#control-table").append("<tr><th>Item description</th><th>Unit price</th><th></th></tr>");
            $.each(backup_cart, function(i, item) {
                var $tr = $('#control-table').append(
                    $('<tr>').attr('id', item.item_id).append(
                    $('<td class="description-td">').text(item.description),
                    $('<td class="price-td">').text("$" + (item.unit_price/100).toFixed(2)),
                    $('<td class="add-td">').html("<button class='add-backup' id='add-" + item.item_id
                            + "' data-item_id='" + item.item_id + "'"
                            + "' data-description='" + item.description + "'"
                            + "' data-unit_price='" + item.unit_price + "'"
                            + "' onClick='add_item(" + item.item_id + ")'>Add</button>")
                  )
                );
            });
            // $(".in-cart-control").removeClass("show");
            $("#recommended").addClass("show");
            });


            }


      $("#date-form").on('submit', showPredictedCart)



function delete_item(clicked_id) {
  $("#" + clicked_id).children('td, th')
    .animate({ padding: 0 })
    .wrapInner('<div class="collapse" />')
    .children()
    .slideUp(function() { $(this).closest('tr').remove(); });
        $.ajax({
            url: '/delete_item',
            type: 'POST',
            data: { json: JSON.stringify(clicked_id)},
            dataType: 'json'
        });
}

function add_item(clicked_id) {

  var item_id = $("#add-" + clicked_id).data("item_id");
  var description = $("#add-" + clicked_id).data("description");
  var unit_price = $("#add-" + clicked_id).data("unit_price");

  $("#" + clicked_id).children('td, th')
    .animate({ padding: 0 })
    .wrapInner('<div class="collapse" />')
    .children()
    .slideUp(function() { $(this).closest('tr').remove(); });

            $('#saved-table').append(
            $('<tr>').addClass('item').attr('id', item_id).attr('data-item_id', item_id).append(
            $('<td class="description-td">').text(description),
            $('<td class="price-td">').text("$" + (unit_price/100).toFixed(2)),
            $('<td class="del-td">').html("<button class='del-primary' id='del-" + item_id
                           + "' onClick='delete_item(" + item_id + ")'>Delete</button>"),
            $('<td class="amazon">').html("<a href='https://fresh.amazon.com/Search?input=" + encodeURIComponent(description) + "' target='_blank'>"
                           + "<img src='http://g-ec2.images-amazon.com/images/G/01/omaha/images/badges/af-badge-160x50.png' height=20px alt='AmazonFresh button'>"
                           + "</a>")
          )
        );


    $("#" + item_id)
    .animate({ padding: 0 })
    .find('td')
    .wrapInner('<div style="border: none; display: none;" />')
    .parent()
    .find('td > div')
    .slideDown()

    $.ajax({
        url: '/add_item',
        type: 'POST',
        data: { json: JSON.stringify(item_id)},
        dataType: 'json'
    });
}
// function showSavedMessage () {
// $("#saved-message").fadeIn(function() {
//     setTimeout(function() {
//         $("#saved-message").fadeOut(1000);
//     }, 3000);
// });
// }


function showPredictionTree(pred_tree) {

  $("#tree-display").empty();

  var margin = {top: 20, right: 120, bottom: 20, left: 120},
      width = 960 - margin.right - margin.left,
      height = 800 - margin.top - margin.bottom;

  var i = 0,
      duration = 750,
      root;

  var tree = d3.layout.tree()
      .size([height, width]);

  var diagonal = d3.svg.diagonal()
      .projection(function(d) { return [d.y, d.x]; });

  var svg = d3.select("#tree-display").append("svg")
      .attr("width", width + margin.right + margin.left)
      .attr("height", height + margin.top + margin.bottom)
    .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  // d3.json("/test", function(error, flare) {
    root = pred_tree;
    root.x0 = height / 2;
    root.y0 = 0;

    function collapse(d) {
      if (d.children) {
        d._children = d.children;
        d._children.forEach(collapse);
        d.children = null;
      }
    }

    root.children.forEach(collapse);
    update(root);
  // });

  d3.select(self.frameElement).style("height", "800px");

  function update(source) {

    // Compute the new tree layout.
    var nodes = tree.nodes(root).reverse(),
        links = tree.links(nodes);

    // Normalize for fixed-depth.
    nodes.forEach(function(d) { d.y = d.depth * 100; });

    // Update the nodes…
    var node = svg.selectAll("g.node")
        .data(nodes, function(d) { return d.id || (d.id = ++i); });

    // Enter any new nodes at the parent's previous position.
    var nodeEnter = node.enter().append("g")
        .attr("class", "node")
        .attr("transform", function(d) { return "translate(" + source.y0 + "," + source.x0 + ")"; })
        .on("click", click);

    nodeEnter.append("circle")
        .attr("r", 1e-6)
        .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; });

    nodeEnter.append("text")
        .attr("x", function(d) { return d.children || d._children ? -10 : 10; })
        .attr("dy", ".35em")
        .attr("text-anchor", function(d) { return d.children || d._children ? "end" : "start"; })
        .text(function(d) { return d.name; })
        .style("fill-opacity", 1e-6);

    // Transition nodes to their new position.
    var nodeUpdate = node.transition()
        .duration(duration)
        .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; });

    nodeUpdate.select("circle")
        .attr("r", 4.5)
        .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; });

    nodeUpdate.select("text")
        .style("fill-opacity", 1);

    // Transition exiting nodes to the parent's new position.
    var nodeExit = node.exit().transition()
        .duration(duration)
        .attr("transform", function(d) { return "translate(" + source.y + "," + source.x + ")"; })
        .remove();

    nodeExit.select("circle")
        .attr("r", 1e-6);

    nodeExit.select("text")
        .style("fill-opacity", 1e-6);

    // Update the links…
    var link = svg.selectAll("path.link")
        .data(links, function(d) { return d.target.id; });

    // Enter any new links at the parent's previous position.
    link.enter().insert("path", "g")
        .attr("class", "link")
        .attr("d", function(d) {
          var o = {x: source.x0, y: source.y0};
          return diagonal({source: o, target: o});
        });

    // Transition links to their new position.
    link.transition()
        .duration(duration)
        .attr("d", diagonal);

    // Transition exiting nodes to the parent's new position.
    link.exit().transition()
        .duration(duration)
        .attr("d", function(d) {
          var o = {x: source.x, y: source.y};
          return diagonal({source: o, target: o});
        })
        .remove();

    // Stash the old positions for transition.
    nodes.forEach(function(d) {
      d.x0 = d.x;
      d.y0 = d.y;
    });
  }

  // Toggle children on click.
  function click(d) {
    if (d.children) {
      d._children = d.children;
      d.children = null;
    } else {
      d.children = d._children;
      d._children = null;
    }
    update(d);
  }

}


// $("#view_tree").on("click", function () {
//   $(".predict").removeClass("show");
//   $("#tree").addClass("show");
//   $(".control-div").removeClass("show");
//
// });

function listOrders() {

  $("#deliv").attr("disabled", true);

    $(".main-display-div").removeClass("show");

    $.get('/list_orders', function(user_orders_json) {

      $.each(user_orders_json.orders, function(i, order) {

          $("#delivery-display").append(
            $('<div class="cartsee-table order" id="order-' + i + '">').append($('<table id="header-wrap" class="table">').append(
              $('<tr class="row header" id="header-' + i + '" onClick="get_id(' + i + ')">').append(
                $("<td class='col-md-4 order-row number'>").text(order.amazon_fresh_order_id),
                $("<td class='col-md-3 order-row deliv-date'>").text(order.delivery_date),
                $("<td class='col-md-3 order-row delivery-time'>").text(order.delivery_time),
                $("<td class='col-md-2 order-row order-total'>").text("$" + (order.order_total/100).toFixed(2))
                )),
              $("<div class='items-div' id='items-div-" + i + "'>").append(
                $("<table class='table items-table'>").attr("cellspacing", "0").attr("width", "100%").append(
                  $("<thead>").append(
                    $("<tr class='header-row'>").append(
                      $("<th class='header-descript'>").text("Item Description"),
                      $("<th  class='header-price'>").text("Unit Price"),
                      $("<th class='header-quantity'>").text("Unit Quantity")
                     )
                   ),
                  $("<tbody id='body-" + i + "'>")
                 )
               )
             )
           );

          $.each(order.order_line_items_serialized, function (j, item) {

            $('#body-' + i).append(
              $('<tr>').addClass('items-row').append(
                $('<td class="row-descript">').text(item.description),
                $('<td class="row-price">').text("$" + (item.unit_price/100).toFixed(2)),
                $('<td class="row-quantity">').text(item.quantity)
               )
             );


            });

  });

});

$("#delivery-display").addClass("show");
$("#deliv-control").addClass("show");
}



function get_id(clicked) {

  $("#items-div-" + clicked).slideToggle(500);

  // if ($("#header-" + clicked).find("#expand-" + clicked).text() == "+") {
  //     $("#header-" + clicked).find("#expand-" + clicked).text("-");
  //   } else {
  //     $("#header-" + clicked).find("#expand-" + clicked).text("+");
  //   }

  }


$('#search').keyup(function (e) {


  var val = $.trim($(this).val()).toLowerCase();

  var $rows = $('.items-table tr');

if (val.length > 2 || val.length === 0) {
  $rows.show().filter(function () {
    var text = $(this).text().toLowerCase();

    if (text.includes(val) && val.length > 2) {
      $(this).parent().parent().parent().stop(true, true).delay(1000).slideDown();
    }

    if (val.length === 0 && e.keyCode === 8) { // keycode for Macs, not sure about PCs...need to figure out
      $(this).parent().parent().parent().stop(true, true).slideUp();
    }


    return !~text.indexOf(val);

  }).hide();
}
});


$(document).on('keyup', '#backup-search', function(e) {


  var val = $.trim($(this).val()).toLowerCase();

  var $rows = $('#control-table tr');

if (val.length > 2) {
  $rows.show().filter(function () {
    var text = $(this).text().toLowerCase();

    return !~text.indexOf(val);

  }).hide();
}

if (val.length === 0 ) {
  $rows.show()
}

});

// D3 AREA CHART BELOW
//http://stackoverflow.com/questions/19901738/d3-area-chart-using-json-object
//http://bl.ocks.org/mohamed-ali/ed4772df6dca7a48f678

function timestamp(str){
    return new Date(str).getTime();
}

function showAreaChart(url) {
  $("#area-chart").empty();

  $.get(url, function(json) {


        data = json["data"]

        if (data === "stop") {
          $("#area-display").text("Sorry, no orders at that range");
          return;
          }

    $("#area-info").html("<h3 class='table-title'>Spending history over time</h3>" +
                            "<p>Your earliest order was on " + json.min_date + "</p>" +
                            "<p>Your most recent order was on " + json.max_date + "</p>" +
                            "<p>The most you spent on an order was $" + (json.max_total/100).toFixed(2) + "</p>" +
                            "<p>The least you spent on an order was $" + (json.min_total/100).toFixed(2) + "</p>");



    var min_date = timestamp(json.min_date);
    var max_date = timestamp(json.max_date);

      var areaDateSlider = $("#area-date").bootstrapSlider({ min: min_date,
                                                          max: max_date,
                                                          value: [min_date, max_date],
                                                          focus:true,
                                                          formatter: function(value) {
                                                            var min_date = (new Date(value[0]));
                                                            min_date = moment(min_date).format('MM/DD/YY');
                                                            var max_date = (new Date(value[1]));
                                                            max_date = moment(max_date).format('MM/DD/YY');
                                                           return [min_date, max_date];
                                                         }});


    $("#min-date").text(json.min_date);

    $("#max-date").text(json.max_date);

  var margin = {top: 20, right: 20, bottom: 30, left: 50},
      width = 960 - margin.left - margin.right,
      height = 500 - margin.top - margin.bottom;


      var parseDate = d3.time.format("%B %d, %Y").parse;
      var formatTime = d3.time.format("%e %b");

  var x = d3.time.scale()
      .range([0, width]);

  var y = d3.scale.linear()
      .range([height, 0]);

  var xAxis = d3.svg.axis()
      .scale(x)
      .orient("bottom");

  var yAxis = d3.svg.axis()
      .scale(y)
      .orient("left");

  var area = d3.svg.area()
      .x(function(d) { return x(d.date); })
      .y0(height)
      .y1(function(d) { return y(d.close); });

  var svg = d3.select("#area-chart").append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
    .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

      var div = d3.select("#area-chart").append("div")
    .attr("class", "tooltips")
    .style("opacity", 0);


    data.forEach(function(d) {
      d.date = parseDate(d.date);
      d.close = (d.close/100).toFixed(2)
      d.close = +d.close;
    });

    x.domain(d3.extent(data, function(d) { return d.date; }));
    y.domain([0, d3.max(data, function(d) { return d.close; })]);

    svg.append("path")
        .datum(data)
        .attr("class", "area")
        .attr("d", area);

    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
      .append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", 6)
        .attr("dy", ".71em")
        .style("text-anchor", "end")
        .text("Price ($)");

svg.selectAll("dot")
        .data(data)
    .enter().append("circle")
        .attr("r", 5)
        .attr("cx", function(d) { return x(d.date); })
        .attr("cy", function(d) { return y(d.close); })
        .on("mouseover", function(d) {
            div.transition()
                .duration(200)
                .style("opacity", .9);
            div .html(formatTime(d.date) + "<br/>"  + d.close)
                .style("left", (d3.event.pageX) + "px")
                .style("top", (d3.event.pageY - 28) + "px");


            })
        .on("mouseout", function(d) {
            div.transition()
                .duration(500)
                .style("opacity", 0);
        });

        function transition() {
  d3.selectAll("path")
      .data(function() {
        var d = layers1;
        layers1 = layers0;
        return layers0 = d;
      })
    .transition()
      .duration(2500)
      .attr("d", area);
}
});}


var areaDateSlider = $("#area-date");

areaDateSlider.on('slideStop', function () {
  var dates = $(this).bootstrapSlider('getValue'); //dates are in milliseconds format

  var bottom_date = dates[0];
  var top_date = dates[1];

  // convert milliseconds to Date string in '01/01/1900' format:
  var bottom_date = (new Date(dates[0]))
  bottom_date = moment(bottom_date).format('MM/DD/YYYY')
  var top_date = (new Date(dates[1]))
  top_date = moment(top_date).format('MM/DD/YYYY')
  console.log(top_date)
  var url = '/orders_over_time?' + 'bottom_date=' + bottom_date + '&top_date=' + top_date;

    showAreaChart(url);

});





/// Bubble chart below

function showBubbleChart(url) {


 $("#bubble-chart").empty();

  $.get(url, function(json) {

    if (json === "stop") {
      $("#bubble-chart").text("Sorry, no items at those ranges");
      return;
      }

    $("#bubble-info").html("<h2>Your items bought from Amazon Fresh</h2>" +
                              "<p>Items are clustered by price; size is reflective of quantity</p>" +
                              "<p>Your most expensive item is:  " + json.max_price_description + " at $" + json.max_price + "</p>" +
                              "<p>The item you bought the most of was:  " + json.max_qty_description + ", quantity: " + json.max_qty + "</p>");



    var bubblePriceSlider = $("#bubble-price").bootstrapSlider({ min: 0,
                                                        max: json.max_price,
                                                        value: [0, json.max_price],
                                                        focus:true});

        bubblePriceSlider.attr('data-min_value', 0);
        bubblePriceSlider.attr('data-max_value', json.max_price);


    $("#max-price").text("   $" + json.max_price);


    var bubbleQtySlider = $("#bubble-quantity").bootstrapSlider({ min: 0,
                                                                  max: json.max_qty,
                                                                  value: [0, json.max_qty],
                                                                  focus:true});

        bubbleQtySlider.attr('data-min_value', 0);
        bubbleQtySlider.attr('data-max_value', json.max_qty);

        $(".slider").removeClass("show");
        $("#bubble-slider-div").addClass("show");

    $("#max-qty").text(json.max_qty);

  var diameter = 960,
    format = d3.format(",d"),
    color = d3.scale.category20c();

var bubble = d3.layout.pack()
    .sort(null)
    .size([diameter, diameter])
    .padding(1.5);

var svg = d3.select("#bubble-chart").append("svg")
    .attr("width", diameter)
    .attr("height", diameter)
    .attr("class", "bubble");

  var root = json


  var node = svg.selectAll(".node")
      .data(bubble.nodes(classes(root))
      .filter(function(d) { return !d.children; }))
    .enter().append("g")
      .attr("class", "node")
      .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

  node.append("title")
      .text(function(d) { return d.className + ": " + format(d.value); });

  node.append("circle")
      .attr("r", function(d) { return d.r; })
      .style("fill", function(d) { return color(d.packageName); });

  node.append("text")
      .attr("dy", ".3em")
      .style("text-anchor", "middle")
      .text(function(d) { return d.className.substring(0, d.r / 3); });

// Returns a flattened hierarchy containing all leaf nodes under the root.
function classes(root) {
  var classes = [];

  function recurse(name, node) {
    if (node.children) node.children.forEach(function(child) { recurse(node.name, child); });
    else classes.push({packageName: name, className: node.name, value: node.quantity});
  }

  recurse(null, root);
  return {children: classes};
}

d3.select(self.frameElement).style("height", diameter + "px");

});
}

// range selectors for bubble chart


var bubblePriceSlider = $("#bubble-price");
var bubbleQtySlider = $("#bubble-quantity");


bubblePriceSlider.on('slideStop', function () {
  var price_value = $(this).bootstrapSlider('getValue');
  $(this).data('min_value', price_value[0]);
  $(this).data('max_value', price_value[1]);
  var qty_value = [bubbleQtySlider.data('min_value'),bubbleQtySlider.data('max_value')];

  var url = '/items_by_qty?' + 'bottom_price=' + price_value[0] + '&top_price=' + price_value[1] + '&bottom_qty=' + qty_value[0] + '&top_qty=' + qty_value[1];

    showBubbleChart(url);

});


bubbleQtySlider.on('slideStop', function () {
  var qty_value = $(this).bootstrapSlider('getValue');
  $(this).data('min_value', qty_value[0]);
  $(this).data('max_value', qty_value[1]);

  var price_value = [bubblePriceSlider.data('min_value'), bubblePriceSlider.data('max_value')];


  console.log(qty_value, price_value)
  var url = '/items_by_qty?' + 'bottom_price=' + price_value[0] + '&top_price=' + price_value[1] + '&bottom_qty=' + qty_value[0] + '&top_qty=' + qty_value[1];

    showBubbleChart(url);

});








// histogram

// Generate a Bates distribution of 10 random variables.

function showHistogram() {
//http://bl.ocks.org/Caged/6476579

$("#bar-info").html("<h2>Deliveries by day of week</h2>");


  var margin = {top: 40, right: 20, bottom: 30, left: 40},
      width = 960 - margin.left - margin.right,
      height = 500 - margin.top - margin.bottom;

  // var formatPercent = d3.format(".0%");

  var x = d3.scale.ordinal()
      .rangeRoundBands([0, width], .1);

  var y = d3.scale.linear()
      .range([height, 0]);

  var xAxis = d3.svg.axis()
      .scale(x)
      .orient("bottom");

  var yAxis = d3.svg.axis()
      .scale(y)
      .orient("left")
      // .tickFormat(formatPercent);

  var tip = d3.tip()
    .attr('class', 'd3-tip')
    .offset([-10, 0])
    .html(function(d) {
      return "<strong>Deliveries:</strong> <span style='color:red'>" + d.deliveries + "</span>";
    })

  var svg = d3.select("#bar-display").append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
    .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  svg.call(tip);

  d3.json("/delivery_days", function(error, data) {
    data = data["data"]
    x.domain(data.map(function(d) { return d.day; }));
    y.domain([0, d3.max(data, function(d) { return d.deliveries; })]);
    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
      .append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", 6)
        .attr("dy", ".71em")
        .style("text-anchor", "end")
        .text("Deliveries");

    svg.selectAll(".bar")
        .data(data)
      .enter().append("rect")
        .attr("class", "bar")
        .attr("x", function(d) { return x(d.day); })
        .attr("width", x.rangeBand())
        .attr("y", function(d) { return y(d.deliveries); })
        .attr("height", function(d) { return height - y(d.deliveries); })
        .on('mouseover', tip.show)
        .on('mouseout', tip.hide)

  });

  function type(d) {
    d.deliveries = +d.deliveries;
    return d;
  }
  }



$("#cart").on("click", function() {
  $(".chart-button").removeAttr("disabled");
  $(".toggle-button").removeAttr("disabled");
  $("#cart").attr("disabled", true);
  // $(".predict").removeClass("show");
  // $("#carts").addClass("show");
  $(".control-div").addClass("show");
  $("#predict-control").addClass("show");
  $(".display-div").removeClass("show");
  $(".main-display-div").removeClass("show");
  $("#predict-display").addClass("show");
  $(".control-div").removeClass("show");
  $("#predict-control").addClass("show");
  $(".in-cart-control").removeClass("show");
  $("#cart-buttons").addClass("show");
  $(".control").removeClass("show");
  $("#cart-control").addClass("show");
  $("#recommended").addClass("show");

});

$("#viz").on("click", function() {
  $(".control-div").removeClass("show");
  $("#chart-control").addClass("show");
  $(".display-div").removeClass("show");
  // $("#bubble-display").addClass("show");
  $(".toggle-button").removeAttr("disabled");
  $(this).attr("disabled", true);
  $(".chart-button").removeAttr("disabled");
  $("#bubble-button").attr("disabled", true);
  $(".main-display-div").removeClass("show");
  $("#prediction-display").hide();
  $("#visualization-display").addClass("show");

  // $(".predict").removeClass("show");
  // $(".span2").bootstrapSlider("disable");
  // $(".bubble-slider").bootstrapSlider("enable");
  // $(".slider-label").addClass("dark");
  // $(".bubble-label").removeClass("dark");

});


$("#bubble-button").on("click", function() {
  //  $(".display-div").removeClass("show");
  //  $("#bubble-display").addClass("show");
  $(".display-div").hide();
  $("#bubble-display").show();
   $(".chart-button").removeAttr("disabled");
   $(this).attr("disabled", true);
   $(".slider").removeClass("show");
   $("#bubble-slider-div").addClass("show");
  //  $(".span2").bootstrapSlider("disable");
  //  $(".bubble-slider").bootstrapSlider("enable");
  //  $(".slider-label").addClass("dark");
  //  $(".bubble-label").removeClass("dark");


});


$("#area-button").on("click", function() {
  //  $(".display-div").removeClass("show");
  //  $("#area-display").addClass("show");
  $(".display-div").hide();
  $("#area-display").show();
   $(".chart-button").removeAttr("disabled");
   $(this).attr("disabled", true);
   $(".slider").removeClass("show");
   $("#area-slider-div").addClass("show");
  //  $(".span2").bootstrapSlider("disable");
  //  $(".area-slider").bootstrapSlider("enable");
  //  $(".slider-label").addClass("dark");
  //  $(".area-label").removeClass("dark");
});

$("#bar-button").on("click", function() {
  //  $(".display-div").removeClass("show");
  //  $("#bar-display").addClass("show");
  $(".display-div").hide();
  $("#bar-display").show();
   $(".chart-button").removeAttr("disabled");
   $(this).attr("disabled", true);
   $(".slider").removeClass("show");
  //  $(".span2").bootstrapSlider("disable");
  //  $(".slider-label").addClass("dark");

});

$(document).on('click', "#view-tree", function(){
  $(".controls").removeClass("show");
  $("#tree-control").addClass("show");
  $(".toggle-button").attr("disabled", true);
  $("#carts").hide();
  $("#tree").show();
});


$("#return-to-cart").on("click", function() {
  $(".predict").hide();
  $("#carts").show();
  $(".controls").removeClass("show");
  $("#cart-control").addClass("show");
  $("#viz").removeAttr("disabled");
  $("#deliv").removeAttr("disabled");

})

$("#deliv").on("click", function() {
   $(".display-div").removeClass("show");
   $(".control-div").removeClass("show");
   $(".main-display-div").removeClass("show");
   $("#delivery-display").addClass("show");
   $("#deliv-control").addClass("show");
   $(".toggle-button").removeAttr("disabled");
   $(".chart-button").removeAttr("disabled");
   $(this).attr("disabled", true);



});
