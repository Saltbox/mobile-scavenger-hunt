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

  // make new item checkbox
  var tdCheckbox = function(index, checked) {
    if (checked) {
      return "<td><input type='checkbox' class='hunt-items' name='item-required' checked='on'> Required</td>";
    }
    return "<td><input type='checkbox' class='hunt-items' name='item-required'> Required</td>";
  };

  // gives admin something to delete items
  var deleteIconTd = function(type) {
    var glyphiconRemove = '<span class="glyphicon glyphicon-remove"></span>';
    return '<td class="'+ type + '-delete">' + glyphiconRemove + '</td>';
  };

  // add tr to item table
  var addItemRow = function(itemCount, fieldValue) {
    var checked = $("input[name=all_required]").prop('checked');
    var tdInput = "<td>" + "<input type='text' value=" + fieldValue + " name='item' class='form-control'>" + "</td>";
    var row = "<tr>" + tdInput + tdCheckbox(itemCount, checked) + deleteIconTd('item') + "</tr>";
    $('#items-table tbody').append(row);
  };

  // add tr to participant table
  var addParticipantRow = function(email, registered) {
    var emailTd = "<td><input type='email' value=" + email + " name=participant class='form-control'></td>";
    var listRow = "<tr>" + emailTd + deleteIconTd('participant') + "</tr>";
    $('#participants-table').append(listRow);
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

  // add item or participant to respective table
  var addInput = function(fieldType, count) {
    var fieldInput = $('input#' + fieldType + '-template');
    var fieldValue = fieldInput.val();

    if (fieldValue) {
      // find smarter way to do this
      if (fieldType == 'items') {
        addItemRow(itemCount, fieldValue);
        itemCount = incrementCount('items', count);
      }
      else {
        if (validEmail(fieldValue)) {
          addParticipantRow(fieldValue, true);
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
  $('#participants-table tbody').on('click', 'td.participant-delete', function() {
    $(this).parents('tr').remove();
    participantCount = decrementCount('participants', participantCount);
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

  var formIncomplete = function(selector, formData) {
    var form = $(selector).find('input');
    return $.isEmptyObject(formData);
  };

  var addItemsToForm = function() {
    $('input[name=item]').each(function(i, e) {
      formData['items-' + i + '-name'] = $(e).val();
      var checked = $($($(e)).parent().siblings().find('input')).prop('checked');
      formData['items-' + i + '-required'] = checked;
    });
  };

  var addParticipantsToForm = function() {
    $('input[name=participant]').each(function(i, e) {
      formData['participants-' + i + '-email'] = $(e).val();
    });
  };

  var formData = {};
  var submitForm = function() {
    if (formIncomplete('form[name=new_hunt]', formData)) {
      $('.missingfields').show();
    }
    else {
      formData['name'] = $('input#name').val();
      formData['welcome_message'] = $(
        'textarea[name=welcome_message]').val();
      formData['congratulations_message'] = $(
        'textarea[name=congratulations_message]').val();

      addItemsToForm();
      addParticipantsToForm();

      $.ajax({
        url: '/new_hunt',
        method: 'POST',
        data: formData
      })
      .success(function() {
        console.log('formdata', formData);
        window.location.replace("/hunts");
      })
      .error(function() {
        window.location.replace("/new_hunt");
      });
    }
  };

  $('#submit-hunt-btn').on('click', function(e) {
    e.preventDefault();
    submitForm();
  });

  $('#printqr').on('click', function(e) {
    // thanks! http://stackoverflow.com/questions/12997123/print-specific-part-of-webpage
    var codes = document.getElementById("qrcodes");
    var sectionPrint = window.open('', '', 'letf=0,top=0,width=800,height=900,toolbar=0,scrollbars=0,status=0');
    sectionPrint.document.write(codes.innerHTML);
    sectionPrint.document.close();
    sectionPrint.focus();
    sectionPrint.print();
  });
});