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
    var newField;
    if (fieldValue) {
      // find smarter way to do this
      if (fieldType == 'items') {
        $('#item-tbody').append(
          "<tr>" + tdCheckbox(itemCount) + tdItem(fieldValue) + "</tr>"
        );
        newField = '<input type="hidden" name="items-' + itemCount +'-name" value="' + fieldValue +'">';
        $('#participants-group .input-group').append(newField);
        itemCount += 1;
      }
      else {
        var validEmailRegex = /[\w-]+@([\w-]+\.)+[\w-]+/;
        if (validEmailRegex.test(fieldValue)) {
          $('#participant-names').append(
            '<li>' + fieldValue + '</li>'
          );
          newField = '<input type="hidden" name="participants-' + participantCount +'-email" value="' + fieldValue +'">';
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

  $("td.requireditem :checkbox").change(function(t, e) {
    console.log('t e', t, e);
  });

  $('input[name=messagetoggle]').change(function(event) {
    if (event.target.value == 'default') {
      $('textarea[name=welcome_message]').val(
        "Welcome! You are about to participate in the (your scavenger hunt name). If you don't think you're supposed to do this, tap on 'Oops'. Otherwise, tap on 'Get Started'."
      );
    }
    else {
      $('textarea[name=welcome_message]').val('');
    }
  });

  $('input[name=congratulationstoggle]').change(function(event) {
    if (event.target.value == 'default') {
      $('textarea[name=congratulations_message]').val(
        "Congratulations! You have successfully completed the scavenger hunt."
      );
    }
    else {
      $('textarea[name=congratulations_message]').val('');
    }
  });
});