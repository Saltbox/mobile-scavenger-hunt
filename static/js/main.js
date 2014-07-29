console.log('loading main.js');

$(document).ready(function() {
  var itemCount = 0;  // no. maybe make a class or something.
  var participantCount = 0;

  // toggle if all items are required for success
  $("input[name=all_required]").change(function() {
    var allItemsRequired = $("input[name=all_required]").prop('checked');
    if (allItemsRequired) {
      $('input.hunt-items').prop('checked', true);
      $('#num-items-group').hide('slow');
    }
    else {
      $('#num-items-group').show('slow');
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
  var tdCheckbox = function(index, checked) {
    if (checked) {
      return "<td><input type='checkbox' checked='on' class='hunt-items' name='" + itemRequiredName(index) + "'></td>";
    }
    return "<td><input type='checkbox' class='hunt-items' name='" + itemRequiredName(index) + "'></td>";
  };

  // since jquery wrap doesn't seem to work
  var tdItem = function(nameOfItem) {
    return "<td class='item-required'>" + nameOfItem + "</td>";
  };

  // create input name property that works with wtforms
  var itemName = function(itemCount) {
    return 'items-' + itemCount + '-name';
  };

  // gives admin something to delete items
  var itemDelete = function(itemCount) {
    return '<td class="item-delete"><span class="glyphicon glyphicon-remove"></span></td>';
  };

  // add tr to item table
  var addItemRow = function(itemCount, fieldValue) {
    var checked = $("input[name=all_required]").prop('checked');
    var row = "<tr>" + tdCheckbox(itemCount, checked) + tdItem(fieldValue) + itemDelete(itemCount) + "</tr>";
    $('#items-table tbody').append(row);
  };


  // helper for addInput that displays each added participant email
  var addParticipantRow = function(email, registered) {
    var emailTd = "<td>" + email + "</td>";
    var checkmark;
    //add logic for show vs new view later
    if (registered) {
      checkmark = "<td><span class='glyphicon glyphicon-ok'></span></td>";
    }
    else {
      checkmark = '<td></td>';
    }
    var listRow = "<tr>" + emailTd + checkmark + "</tr>";
    $('#participants-table').append(listRow);
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

    if (fieldValue) {
      // find smarter way to do this
      if (fieldType == 'items') {
        addItemRow(itemCount, fieldValue);
        addNewField('items', 'items-' + itemCount + "-name", fieldValue);

        incrementCount('items', count);
      }
      else {
        var validEmailRegex = /[\w-]+@([\w-]+\.)+[\w-]+/;
        if (validEmailRegex.test(fieldValue)) {
          addParticipantRow(fieldValue, true);
          addNewField(
            'participants', 'participants-' + participantCount + '-email', fieldValue);

          incrementCount('participants', count);
        }
        else {
          $('#participant-error').show('slow');
        }
      }
      fieldInput.val('');
    }
  };

  var incrementCount = function(countType, count) {
    if (count < 1) {
      $('#' + countType + '-table').show('slide', {'direction': 'up'}, 'fast');
    }
    count += 1;
  };

  var decrementCount = function(countType, count) {
    count -= 1;
    if (count < 1) {
      $('#' + countType + '-table').hide('slow');
    }
  };

  // hide participant email error message when typing
  $("#participants-template").keypress(function() {
    $('#participant-error').hide('slow');
  });

  // add item to table for later submission via button
  $("#add-item").on("click", (function() {
      addInput('items', itemCount);
  }));

  // add item to table for later submission via "enter" on keyboard
  $('input#items-template').keydown(function(event) {
    if (event.keyCode == 13) {
      event.preventDefault();
      addInput('items', itemCount);
    }
  });

  // add participant to list for later submission via button
  $("#add-participant").on("click", (function() {
      addInput('participants', participantCount);
  }));

  // add participant to list for later submission via "enter" on keyboard
  $('input#participants-template').keydown(function(event) {
    if (event.keyCode == 13) {
      event.preventDefault();
      addInput('participants', participantCount);
    }
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
    el.hide('slow');
    $('#update-welcome').val(welcome).show('slow').focus();
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

  var oldWelcome, currentWelcome = $('#welcome-msg').html();
  $('#update-welcome').blur(function() {
    currentWelcome = $('#update-welcome').val();
    if (oldWelcome != currentWelcome) {
      updateWelcome(currentWelcome);
      oldWelcome = currentWelcome;
    }
    $('#welcome-msg').show('slow').html(currentWelcome);
    $('#update-welcome').hide('slow');
  });

  $('.panel.welcome .panel-body').hover(
    function() { $('#welcome-msg').css('color', 'lightgray'); },
    function() { $('#welcome-msg').css('color', 'white'); }
  );

  $('.panel.congratulations').click(function(event) {
    event.stopPropagation();
    var el = $('#congratulations-msg');
    var congratulations = el.html();
    el.hide('slow');
    $('#update-congratulations').val(congratulations).show('slow').focus();
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

  var oldCongratulations, currentCongratulations = $('#congratulations-msg').html();
  $('#update-congratulations').blur(function() {
    currentCongratulations = $('#update-congratulations').val();
    if (oldCongratulations != currentCongratulations) {
      updatecongratulations(currentCongratulations);
      oldCongratulations = currentCongratulations;
    }
    $('#congratulations-msg').show('slow').html(currentCongratulations);
    $('#update-congratulations').hide('slow');
  });

  $('.panel.congratulations .panel-body').hover(
    function() { $('#congratulations-msg').css('color', 'lightgray'); },
    function() { $('#congratulations-msg').css('color', 'white'); }
  );

  $('#participant-rules .panel-rect').on({
    click: function(e) {
      $(this).css('opacity', 1).siblings().css('opacity', 0.7);
      $('.glyphicon-ok').hide('slow');
      $($(this).find('.glyphicon-ok')).show();

      var selectedRule = $(this).find($('input[name=participant_rule]'));
      selectedRule.prop('checked', 'on');
      if (selectedRule.val() == 'by_whitelist') {
        $('#whitelist').show('slow');
      }
      else {
        $('#whitelist').hide();
      }
    },
    mouseenter: function() {
      $(this).addClass('panel-rect-hover');
    },
    mouseleave: function() {
      $(this).removeClass('panel-rect-hover');
    }
  });

  $('#items-table tbody').on('click', 'td.item-delete', function() {
    $(this).parents('tr').remove();
    decrementCount('items', itemCount);
  });
});