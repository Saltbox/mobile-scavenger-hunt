console.log('loading main.js');

$(document).ready(function() {
  var itemCount = 0;  // no. maybe make a class or something.
  var participantCount = 0;

  var tdCheckbox = function(index) {
    return "<td><input type='checkbox' id='item" + index + "' onclick='toggleRequired(" + index + ")'></td>";
  };

  var tdItem = function(item_name) {
    return "<td>" + item_name + "</td>";
  };

  var createName = function(itemCount) {
    return 'items-' + itemCount + '-name';
  };

  var addInput = function(fieldType, count) {
    var fieldName = createName(count);
    var fieldInput = $('input#' + fieldType + '-template');
    var fieldValue = fieldInput.val();

    //  note for monday or saturday or whenever. names aren't being submitted to participant or item. i think it's count related


    if (fieldValue) {
      // find smarter way to do this
      if (fieldType == 'items') {
        $('#item-tbody').append(
          "<tr>" + tdCheckbox(itemCount) + tdItem(fieldValue) + "</tr>"
        );
        var newField = '<input type="hidden" name="items-' + itemCount +'-name" value="' + fieldValue +'">';
        $('#participants-group .input-group').append(newField);
        itemCount += 1;
      }
      else {
        var validEmailRegex = /[\w-]+@([\w-]+\.)+[\w-]+/;
        if (validEmailRegex.test(fieldValue)) {
          $('#participant-names').append(
            '<span class="participant-list-item">' + fieldValue + '</span>'
          );
          var newField = '<input type="hidden" name="participants-' + participantCount +'-email" value="' + fieldValue +'">';
          $('#items-group .input-group').append(newField);
          participantCount += 1;
        }
        else {
          // do some sort of error display
        }
      }
      fieldInput.val('');
    }
  };

  // add item to table and list for later submission
  $("#add-item").on("click", (function() {
      addInput('items');
  }));

  $('input#items-template').keydown(function(event) {
    if (event.keyCode == 13) {
      event.preventDefault();
      addInput('items');
    }
  });

  // add participant to table and list for later submission
  $("#add-participant").on("click", (function() {
      addInput('participants');
  }));

  $('input#participants-template').keydown(function(event) {
    if (event.keyCode == 13) {
      event.preventDefault();
      addInput('participants');
    }
  });

  $("td.requireditem :checkbox").change(function (t, e) {
    console.log('t e', t, e);
  });


});