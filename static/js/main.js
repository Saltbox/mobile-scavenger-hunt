console.log('loading main.js');

$(document).ready(function() {
  var itemCount = $('.hunt-items').length;
  var participantCount = 0;

  var huntId = function() {
    return $('form[hunt_id]').attr('hunt_id');
  };

  // show checkmarks for selected participant rule
  var participant_rule_el = $('input[name=participant_rule][checked=on]');
  if (participant_rule_el) {
    $(participant_rule_el).siblings().show();
  }

  // toggle for whether or not an item is required
  // parent needed to help detect dynamically added content
  var $parent = $('#items-group .table.table-condensed');
  $($parent).on("change", ".hunt-items", function(e) {
    // if value is in target, it's been set to "on". toggling removes value.
    if ('value' in e.currentTarget) {
      $($('input[name=all_required]')[1]).prop('checked', true);
      formData['all_required'] = true;
    }
  });

  // create input name for item required that works with wtforms
  var itemRequiredName = function(index) {
    return "items-" + index + "-required";
  };

  // make new item checkbox
  var tdCheckbox = function(index, checked) {
    if (checked) {
      return "<td><input type='checkbox' checked='on' class='hunt-items' name='" + itemRequiredName(index) + "'> Required</td>";
    }
    return "<td><input type='checkbox' class='hunt-items' name='" + itemRequiredName(index) + "'> Required</td>";
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
  var itemDelete = function() {
    return '<td class="item-delete"><span class="glyphicon glyphicon-remove"></span></td>';
  };

  // add tr to item table
  var addItemRow = function(itemCount, fieldValue) {
    var checked = $("input[name=all_required]").prop('checked');
    var row = "<tr>" + tdItem(fieldValue) + tdCheckbox(itemCount, checked) + itemDelete() + "</tr>";
    $('#items-table tbody').append(row);
  };

  // toggle if all items are required for success
  $("input[name=all_required]").change(function() {
    var allItemsRequired = $(this).prop('checked');
    if (allItemsRequired) {
      $('input.hunt-items').prop('checked', true);
      $('#num-items-group').hide('slow');
    }
    else {
      $('#num-items-group').show('slow');
    }
  });

  var validEmail = function(email) {
    var validEmailRegex = /[\w-]+@([\w-]+\.)+[\w-]+/;
    return validEmailRegex.test(email);
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
        formData['items-' + itemCount + "-name"] = fieldValue;

        itemCount = incrementCount('items', count);
      }
      else {
        if (validEmail(fieldValue)) {
          addParticipantRow(fieldValue, true);
          formData['participants-' + participantCount + '-email'] = fieldValue;

          participantCount = incrementCount('participants', count);
        }
        else {
          $('#participant-error').show('slow');
        }
      }
      fieldInput.val('');
    }
  };

  // add input on enter
  var addInputByKeydown = function(event, type, count) {
    if (event.keyCode == 13) {
      event.preventDefault();
      addInput(type, count);
    }
  };

  // updates count and makes item/participant table appear with the first added row
  var incrementCount = function(countType, count) {
    if (count < 1) {
      $('#' + countType + '-table').show('slide', {'direction': 'up'}, 'fast');
    }
    count += 1;
    return count;
  };

  // updates count and makes item/participant table disappear on the last item deleted
  var decrementCount = function(countType, count) {
    count -= 1;
    if (count < 1) {
      $('#' + countType + '-table').hide('slow');
    }
    return count;
  };

  // helper for addInput that displays each added participant email
  var addParticipantRow = function(email, registered) {
    var emailTd = "<td>" + email + "</td>";
    var checkmark;
    var listRow = "<tr>" + emailTd + "<td></td></tr>";
    $('#participants-table').append(listRow);
  };

  // add participant to list for later submission via button
  $("#add-participant").on("click", (function() {
    addInput('participants', participantCount);
  }));

  // add participant to list for later submission via "enter" on keyboard
  $('#participants-template').keydown(function(event) {
    $('#participant-error').hide('slow');
    addInputByKeydown(event, 'participants', participantCount);
  });

  // add item to table for later submission via button
  $("#add-item").on("click", (function() {
    addInput('items', itemCount);
  }));

  // add item to table for later submission via "enter" on keyboard
  $('input#items-template').keydown(function(event) {
    addInputByKeydown(event, 'items', itemCount);
  });

  // remove item from list and delete on backend
  $('#items-table tbody').on('click', 'td.item-delete', function() {
    $(this).parents('tr').remove();
    itemCount = decrementCount('items', itemCount);
  });

  // time formatter
  $('.uglytime').each(function(index, e) {
    var currentTime = $(e).html();
    var prettyTime = moment(currentTime).format("MM-DD-YYYY");
    $(e).text(prettyTime);
  });

  // various events for updating ui upon participant rule selection
  $('#participant-rules .panel-rect').on({
    click: function(e) {
      $(this).css('opacity', 1).siblings().css('opacity', 0.7);
      $('.glyphicon-ok').hide('slow');
      $($(this).find('.glyphicon-ok')).show();

      var selectedRule = $(this).find($('input[name=participant_rule]'));
      selectedRule.prop('checked', 'on');
      if (selectedRule.val() == 'by_whitelist') {
        $('#participants-group').show('slide', {'direction': 'up'}, 'slow');
      }
      else {
        $('#participants-group').hide('slide', {'direction': 'up'}, 'slow');
      }
      formData['participant_rule'] = selectedRule.val();
    },
    mouseenter: function() {
      $(this).addClass('panel-rect-hover');
    },
    mouseleave: function() {
      $(this).removeClass('panel-rect-hover');
    }
  });

  var formValid = function(selector, formData) {
    var form = $(selector).find('input');
    console.log(form);

  };

  var formData = {};
  var submitForm = function() {
    if (formValid('form[name=new_hunt]', formData)) {
      $('.missingfields').show();
    }
    else {
      formData['name'] = $('input#name').val();
      formData['welcome_message'] = $(
        'textarea[name=welcome_message]').val();
      formData['congratulations_message'] = $(
        'textarea[name=congratulations_message]').val();

      $('.hunt-items').each(function(i, e) {
        var checked = $(e).prop('checked');
        var name = $(e).prop('name');
        if (name) {
          formData[name] = checked;
          console.log('name', name);
        }
      });

      $.ajax({
        url: '/new_hunt',
        method: 'POST',
        data: formData
      })
      .success(function() {
        console.log('submit success');
        // window.location.replace("/hunts");
      })
      .error(function() {
        console.log('fail');
      });
    }
  };

  $('#submit-hunt-btn').on('click', function(e) {
    e.preventDefault();
    submitForm();
  });
});