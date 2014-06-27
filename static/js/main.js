console.log('loading main.js');

$(document).ready(function() {
  var itemCount = 0;  // no. maybe make a class or something.

  var tdCheckbox = function(index) {
    return "<td><input type='checkbox' id='item" + index + "' onclick='toggleRequired(" + index + ")'></td>";
  };

  var tdItem = function(item_name) {
    return "<td>" + item_name + "</td>";
  };

  var createName = function(itemCount) {
    return 'items-' + itemCount + '-name';
  };

  var addInput = function() {
    var fieldName = createName(itemCount);
    itemCount += 1;

    var item_name = $('input[name=items-template]').val();
    console.log('itemname', item_name);
    if (item_name) {
      $('#item-tbody').append(
        "<tr>" + tdCheckbox(itemCount) + tdItem(item_name) + "</tr>"
      );

      $('#items-group .input-group').append(
        '<input type="hidden" name="items-' + itemCount +'-name" value="' + item_name +'">'
      );
      $('input[name=items-template]').val('');
    }
  };

  // add item to table and list for later submission
  $("#add-item").on("click", (function() {
      addInput(itemCount);
  }));

  $('input[name=items-template]').keydown(function(event) {
    if (event.keyCode == 13) {
      event.preventDefault();
      addInput(itemCount);
    }
  });

  $("td.requireditem :checkbox").change(function (t, e) {
    console.log('t e', t, e);
  });
});