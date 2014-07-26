console.log('loading main.js');

$(document).ready(function() {
  var itemCount = 0;  // no. maybe make a class or something.
  var participantCount = 0;

  // toggle if all items are required for success
  var allItemsRequired = $("input[name=all_required]").val();
  $("input[name=all_required]").change(function() {
    allItemsRequired = $("input[name=all_required]").val();
    if (allItemsRequired) {
      $('input.hunt-items').prop('checked', true);
    }
  });

  // toggle for whether or not an item is required
  // parent needed to help detect dynamically added content
  var $parent = $('#items-group .table.table-condensed');
  $($parent).on("change", ".hunt-items", function(e) {
    // if value is in target, it's been set to "on". toggling removes value.
    if ('value' in e.currentTarget) {
      $($('input[name=all_required]')[1]).prop('checked', true);
    }
  });

  // create input name for item required that works with wtforms
  var itemRequiredName = function(index) {
    return "items-" + index + "-required";
  };

  // make new item checkbox
  var tdCheckbox = function(index) {
    if (allItemsRequired) {
      return "<td><input type='checkbox' checked='on' class='hunt-items' name='" + itemRequiredName(index) + "'></td>";
    }
    return "<td><input type='checkbox' class='hunt-items' name='" + itemRequiredName(index) + "'></td>";
  };

  // since jquery wrap doesn't seem to work
  var tdItem = function(item_name) {
    return "<td class='item-required'>" + item_name + "</td>";
  };

  // create input name property that works with wtforms
  var itemName = function(itemCount) {
    return 'items-' + itemCount + '-name';
  };

  // add tr to item table
  var addItemRow = function(itemCount, fieldValue) {
    var row = "<tr>" + tdCheckbox(itemCount) + tdItem(fieldValue) + "</tr>";
    $('#item-tbody').append(row);
  };

  // helper for addInput that displays each added participant email
  var addParticipantLi = function(fieldValue) {
    $('#participant-emails').append('<li>' + fieldValue + '</li>');
  };

  // helper for addInput
  var addNewField = function(fieldType, name, fieldValue) {
    var newField = $('<input type="hidden">').attr('name', name)
                                             .attr('value', fieldValue);
    $('#' + fieldType + '-group .input-group').append(newField);
  };

  // add item or participant hidden input field that works with wtforms
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

  // hide participant email error message when typing
  $("#participants-template").keypress(function() {
    $('#participant-error').hide();
  });

  // add item to table for later submission via button
  $("#add-item").on("click", (function() {
      addInput('items');
  }));

  // add item to table for later submission via "enter" on keyboard
  $('input#items-template').keydown(function(event) {
    if (event.keyCode == 13) {
      event.preventDefault();
      addInput('items');
    }
  });

  // add participant to list for later submission via button
  $("#add-participant").on("click", (function() {
      addInput('participants');
  }));

  // add participant to list for later submission via "enter" on keyboard
  $('input#participants-template').keydown(function(event) {
    if (event.keyCode == 13) {
      event.preventDefault();
      addInput('participants');
    }
  });

  // helper function for message and congratulations toggling
  var toggleTextarea = function(textareaSelector, defaultMsg) {
    if ($(textareaSelector).is(':hidden')) {
      $(textareaSelector).show(500);
    }
    if (event.target.value == 'default') {
      $(textareaSelector).val(defaultMsg);
    }
    else {
      $(textareaSelector).val('');
    }
  };

  // toggle default/custom welcome message
  $('input[name=messagetoggle]').change(function(event) {
    toggleTextarea(
      "textarea[name=welcome_message]",
      "Welcome! You are about to participate in the (your scavenger hunt name). If you don't think you're supposed to do this, tap on 'Oops'. Otherwise, tap on 'Get Started'."
    );
  });

  // toggle default/custom congratulations message
  $('input[name=congratulationstoggle]').change(function(event) {
    toggleTextarea(
      'textarea[name=congratulations_message]',
      "Congratulations! You have successfully completed the scavenger hunt."
    );
  });

  // time formatter
  $('.uglytime').each(function(index, e) {
    var currentTime = $(e).html();
    var prettyTime = moment(currentTime).format("MM-DD-YYYY");
    $(e).text(prettyTime);
  });

  // add new participant from hunt page
  $('#more-participants-btn').click(function() {
    var newParticipantEmail = $('input#more-participants').val();
    $.ajax({
      url: '/new_participant',
      method: 'POST',
      data: {'email': newParticipantEmail, 'hunt_id': hunt_id} // hunt_id is a var in the html
    })
    .success(function() {
      console.log('success new part.');
      $('#participants-table').append(
        "<tr><td></td><td>" + newParticipantEmail + "</td></tr>");
    })
    .error(function() {
      console.log('fail new part.');
    });
  });

  // add new item from hunt page
  $('#more-items-btn').click(function() {
    var newItemName = $('input#more-items').val();
    var itemRequired = $('input[name=item-required]').prop('checked');
    console.log("item required", itemRequired);
    $.ajax({
      url: '/new_item',
      method: 'POST',
      data: {'name': newItemName, 'required': itemRequired, 'hunt_id': hunt_id} // hunt_id is a var in the html
    })
    .success(function() {
      console.log('item!');
      $('#items-table').append(
        "<tr><td></td><td>" + newItemName + "</td></tr>");
    })
    .error(function() {
      console.log('fail new item');
    });
  });

  $('.panel.welcome').click(function(event) {
    event.stopPropagation();
    var el = $('#welcome-msg');
    var welcome = el.html();
    el.hide();
    $('#update-welcome').val(welcome).show().focus();
  });

  var updateWelcome = function(msg) {
    $.ajax({
      url: '/update_welcome',
      method: 'POST',
      data: {'welcome_message': msg, 'hunt_id': hunt_id}
    })
    .success(function() {
      console.log('updated welcome');
    })
    .error(function() {
      console.log('fail update welcome');
    });
  };

  var oldWelcome = currentWelcome = $('#welcome-msg').html();
  $('#update-welcome').blur(function() {
    currentWelcome = $('#update-welcome').val();
    if (oldWelcome != currentWelcome) {
      updateWelcome(currentWelcome);
      oldWelcome = currentWelcome;
    }
    $('#welcome-msg').show().html(currentWelcome);
    $('#update-welcome').hide();
  });

  $('.panel.welcome .panel-body').hover(
    function() { $('#welcome-msg').css('color', 'lightgray'); },
    function() { $('#welcome-msg').css('color', 'white'); }
  );

  $('.panel.congratulations').click(function(event) {
    event.stopPropagation();
    var el = $('#congratulations-msg');
    var congratulations = el.html();
    el.hide();
    $('#update-congratulations').val(congratulations).show().focus();
  });

  var updatecongratulations = function(msg) {
    $.ajax({
      url: '/update_congratulations',
      method: 'POST',
      data: {'congratulations_message': msg, 'hunt_id': hunt_id}
    })
    .success(function() {
      console.log('updated congratulations');
    })
    .error(function() {
      console.log('fail update congratulations');
    });
  };

  var oldCongratulations = currentCongratulations = $('#congratulations-msg').html();
  $('#update-congratulations').blur(function() {
    currentCongratulations = $('#update-congratulations').val();
    if (oldCongratulations != currentCongratulations) {
      updatecongratulations(currentCongratulations);
      oldCongratulations = currentCongratulations;
    }
    $('#congratulations-msg').show().html(currentCongratulations);
    $('#update-congratulations').hide();
  });

  $('.panel.congratulations .panel-body').hover(
    function() { $('#congratulations-msg').css('color', 'lightgray'); },
    function() { $('#congratulations-msg').css('color', 'white'); }
  );

  // $('table.panel-default').bind({
  $('#participant-rules .panel-rect').bind({
    click: function(e) {
      console.log('e', e);
      $(this).css('opacity', 1).siblings().css('opacity', 0.7);
      $('.glyphicon-ok').hide();
      $($(this).find('.glyphicon-ok')).show();
    },
    mouseenter: function() {
      if ($(this).attr('opacity') != 0.7) {
        $(this).css('opacity', 0.7);
      }
    },
    mouseleave: function() {
      $(this).css('opacity', 1.0);
    }
  });
});