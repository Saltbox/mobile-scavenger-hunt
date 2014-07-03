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

  var itemName = function(itemCount) {
    return 'items-' + itemCount + '-name';
  };

  var addItemRow = function(itemCount, fieldValue) {
    $('#item-tbody').append(
      "<tr>" + tdCheckbox(itemCount) + tdItem(fieldValue) + "</tr>"
    );
  };

  var addParticipantLi = function(fieldValue) {
    $('#participant-emails').append('<li>' + fieldValue + '</li>');
  };

  var addNewField = function(fieldType, name, fieldValue) {
    var newField = $('<input type="hidden">').attr('name', name)
                                             .attr('value', fieldValue);
    $('#' + fieldType + '-group .input-group').append(newField);
  };

  var addInput = function(fieldType, count) {
    var fieldName = itemName(count);
    var fieldInput = $('input#' + fieldType + '-template');
    var fieldValue = fieldInput.val();
    var newField;

    if (fieldValue) {
      // find smarter way to do this
      if (fieldType == 'items') {
        addItemRow(itemCount, fieldValue);
        addNewField('items', 'items-' + itemCount + "-name", fieldValue);

        itemCount += 1;
      }
      else {
        var validEmailRegex = /[\w-]+@([\w-]+\.)+[\w-]+/;
        if (validEmailRegex.test(fieldValue)) {
          addParticipantLi(fieldValue);
          addNewField('participants', 'participants-' + participantCount + '-email', fieldValue);

          participantCount += 1;
        }
        else {
          $('#participant-error').show();
        }
      }
      fieldInput.val('');
    }
  };

  $("#participants-template").keypress(function() {
    $('#participant-error').hide();
  });

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