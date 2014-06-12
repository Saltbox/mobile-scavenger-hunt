$(document).ready(function() {
  var items = [];

  var tdCheckbox = function(index) {
    var input = "<input type='checkbox' id='item" + index + "' onclick='toggleRequired(" + index + ")'>";
    var wrapped = input.wrap("<td></td>");
  };

  var tdItem = function(item_name) {
    return "<td>" + item_name + "</td>";
  };

  // add item to table and list for later submission
  $("#add-item").on("click", (function() {
    var item_name = $('input[name=item]').val();
    if (item_name) {
      $('tbody').append(
        "<tr>" + tdCheckbox(items.length) + tdItem(item_name) + "</tr>"
      );
      $('input[name=item]').val('');
      items.push({
        'name': item_name
      });
    }
  }));

  $("td.requireditem :checkbox").change(function (t, e) {
    console.log('t e', t, e);
  });
});