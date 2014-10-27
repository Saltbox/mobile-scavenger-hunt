console.log('loading main.js');

var itemCount = 0;
var participantCount = 0;

// functions for manipulating data

var validEmail = function(email) {
  var validEmailRegex = /[\w-]+@([\w-]+\.)+[\w-]+/;
  return validEmailRegex.test(email);
};

var addParticipantsToFormData = function(formData) {
  $('input[name=participant]').each(function(i, e) {
    formData['participants-' + i + '-email'] = $(e).val();
  });
  return formData;
};

var addItemsToFormData = function(allRequired, formData) {
  $('input[name=item]').each(function(i, e) {
    formData['items-' + i + '-name'] = $(e).val();

    if (allRequired) {
      formData['items-' + i + '-required'] = true;
    }
    else {
      var tableTd = $($(e)).parent();
      var input = $(tableTd.siblings().find('input[type=checkbox]'));
      var checked = input.prop('checked');
      formData['items-' + i + '-required'] = checked;
    }
  });
  return formData;
};

var tooManyRequiredItems = function(formData) {
  return formData.num_required > formData.num_items;
};

var missingRequiredFields = function(formData) {
  // minimally the form needs to have 3 field values:
  // hunt name, participant_rule, an item
  var required = ['name', 'items-0-name', 'participant_rule'];
  for (var ii in required) {
    if (!(required[ii] in formData)) {
      return true;
    }
  }
  return false;
};

var getFormData = function() {
  var participationRule = $('input[name=participant_rule][checked=on]');
  participationRule.prop('checked', 'on');
  var allRequired = $('input[name=all_required]').prop('checked');

  var formData = {
    'name': $('input#name').val(),
    'all_required': allRequired,
    'num_required': parseInt($('input[name=num_required]').val()),
    'num_items': $('input[name=item]').length,
    'participant_rule': participationRule.val(),
    'domain': $('input[name=domain]').val(),
    'welcome_message': $('textarea[name=welcome_message]').val(),
    'congratulations_message': $('textarea[name=congratulations_message]').val(),
  };
  // num_items isn't actually used on backend, this is just for validating

  formData = addItemsToFormData(allRequired, formData);
  formData = addParticipantsToFormData(formData);

  return formData;
}

var validateFormData = function(formData) {
  var errors = 0;
  if (missingRequiredFields(formData)) {
    $('#missing-fields').show();
    errors += 1;
  }
  if (!formData.name || formData.name.length < 4) {
    $('#short_hunt_name').show();
    errors += 1;
  }
  if (!formData.allRequired && tooManyRequiredItems(formData)) {
    $('#too-many-required').show();
    errors += 1;
  }
  var numItemsMarkedRequired = $('input[name=item-required]:checked').length;
  if (formData['num_required'] < numItemsMarkedRequired) {
    $('#too-many-marked-required').show();
    errors += 1;
  }
  if (errors) {
    return false;
  }
  return formData;
}

var submitForm = function(formData) {
  $('.error').hide();
  var validFormData = validateFormData(formData);
  if (validFormData) {
    $.ajax({
      url: '/new_hunt',
      method: 'POST',
      data: validFormData,
      async: false
    })
    .success(function(data) {
      window.location.replace("/hunts/" + data['hunt_id']);
    })
    .error(function(xhr, status) {
        var formErrors = JSON.parse(xhr.responseText);
        for (model in formErrors) {
          modelErrorsList = formErrors[model];
          for (index in modelErrorsList) {
            modelError = modelErrorsList[index]
            for (modelProperty in modelError) {
              propErrorsList = modelError[modelProperty];
              for (errIndex in propErrorsList) {
                var errorMsg = 'invalid ' + modelProperty + ' in ' + model + ': ' + propErrorsList[errIndex];
                $('.errors').append('<li class="error">' + errorMsg + '</li>');
              }
            }
          }
        }
    });
  }
};


// functions for making/manipulating dom bits

var huntId = function() {
  return $('form[hunt_id]').attr('hunt_id');
};

// make new item checkbox
var tdCheckbox = function(checked) {
  var checkbox = checked ? "checked='on'" : '';
  return "<td class='td-with-input'><input type='checkbox' class='hunt-items' name='item-required'" + checkbox + "> Required</td>";
};

var tdGlyphOkRequired = function() {
  return "<td class='td-with-span'><span class='glyphicon glyphicon-ok'></span> Required</td>";
};

// gives admin something to delete items
var deleteIconTd = function(type) {
  var glyphiconRemove = '<span class="glyphicon glyphicon-remove"></span>';
  return '<td class="'+ type + '-delete">' + glyphiconRemove + '</td>';
};

// add tr to item table
var addItemRow = function(allRequired, itemCount, fieldValue) {
  var tdInput = "<td><input type='text' value='" + fieldValue + "' name='item' class='form-control'></td>";
  var itemRequired = allRequired ? tdGlyphOkRequired() : tdCheckbox(allRequired);
  var row = "<tr>" + tdInput + itemRequired + deleteIconTd('item') + "</tr>";
  $('#items-table tbody').append(row);
};

// add tr to participant table
var addParticipantRow = function(email, registered) {
  var emailTd = "<td><input type='email' value=" + email + " name=participant class='form-control'></td>";
  var listRow = "<tr>" + emailTd + deleteIconTd('participant') + "</tr>";
  $('#participants-table').append(listRow);
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

// add item or participant to respective table
var addInput = function(fieldType, count) {
  var fieldInput = $('input#' + fieldType + '-template');
  var fieldValue = fieldInput.val();
  var allRequired = $("input[name=all_required]").prop('checked');

  if (fieldValue) {
    // find smarter way to do this
    if (fieldType == 'items') {
      addItemRow(allRequired, count, fieldValue);
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

// time formatter
$('.uglytime').each(function(index, e) {
  var currentTime = $(e).html();
  var prettyTime = moment(currentTime).fromNow();
  $(e).text(prettyTime);
});

var toggleParticipantTable = function(participantRule) {
  if (participantRule == 'by_whitelist') {
    $('#participants-group').show('slide', {'direction': 'up'}, 'slow');
  }
  else {
    $('#participants-group').hide('slide', {'direction': 'up'}, 'slow');
  }
};


$(document).ready(function() {
  // show checkmarks for selected participant rule
  var participantRuleEl = $('input[name=participant_rule][checked=on]');
  if (participantRuleEl) {
    $(participantRuleEl).siblings().show();
  }

  // toggle if all items are required for success
  $("input[name=all_required]").change(function() {
    var allItemsRequired = $(this).prop('checked');
    if (allItemsRequired) {
      $('input.hunt-items').prop('checked', true);
      $('#num-items-group').hide('slow');
      $('.td-with-input').replaceWith(tdGlyphOkRequired());
    }
    else {
      $('#num-items-group').show('slow');
      $('.td-with-span').replaceWith(tdCheckbox(false));
    }
  });

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

  // remove item from list
  $('#participants-table tbody').on('click', 'td.participant-delete', function() {
    $(this).parents('tr').remove();
    participantCount = decrementCount('participants', participantCount);
  });

  // remove item from list and delete on backend
  $('#items-table tbody').on('click', 'td.item-delete', function() {
    $(this).parents('tr').remove();
    itemCount = decrementCount('items', itemCount);
  });

  $('#participant-rules .panel-rect.anyone button.btn-primary').focus();
  // various events for updating ui upon participant rule selection
  $('#participant-rules .panel-rect').on({
    click: function(e) {
      $('.panel-rect .btn').removeClass('active');
      $(this).find('.btn').addClass('active');
      $('.explanation div').hide();

      if ($(this).hasClass('by_domain')) {
        $('#domain').show();
        $('.explanation .by_domain').show();
      }
      else {
        $('#domain').hide();
        if ($(this).hasClass('anyone')) {
          $('.explanation .anyone').show();
        }
        else {
          $('.explanation .by_whitelist').show();
        }
      }

      var selectedRule = $(this).find($('input[name=participant_rule]'));
      selectedRule.attr('checked', 'on');
      toggleParticipantTable(selectedRule.val());
    },
    mouseenter: function() {
      if (!$(this).find('active')) {
        $(this).addClass('panel-rect-hover');
      }
    },
    mouseleave: function() {
      $(this).removeClass('panel-rect-hover');
    }
  });

  var showAdminRegistration = function() {
    $('#login-form').hide();
    $('#registration-form').show();
    $('input[name=email]').focus();
  };

  $('#register-here').on('click', function(e) {
    e.preventDefault();
    showAdminRegistration();
  });

  $('#login-here').on('click', function(e) {
    e.preventDefault();
    $('#login-form').show();
    $('#registration-form').hide();
    $('input[name=email]').focus();
  });

  $('#submit-hunt-btn').on('click', function(e) {
    e.preventDefault();
    var formData = getFormData();
    submitForm(formData);
  });

  $('.credentials .form-group input[name=login]').on('keyup', function(e) {
    $('.not-email-error').hide();
    var input = $(this).val();
    if (input.indexOf('@') != -1) {
      $('.not-email-error').show();
    }
  });

  $('#printqr').on('click', function(e) {
    // thanks! http://stackoverflow.com/questions/12997123/print-specific-part-of-webpage
    var codes = document.getElementById("qrcodes");
    var sectionPrint = window.open(
      '', '', 'letf=0,top=0,width=800,height=900,toolbar=0,scrollbars=0,status=0');
    sectionPrint.document.write(codes.innerHTML);
    sectionPrint.document.close();
    sectionPrint.focus();
    sectionPrint.print();
  });

  $('#hunts-table .glyphicon-remove').on('click', function(e) {
    $(this).siblings('.btn-group').show();
    $(this).hide();
  });

  $('#hunts-table .btn-default').on('click', function() {
    $(this).parent('.btn-group').hide().siblings('.glyphicon-remove').show();
  });

  $('#items-table').on('change', 'input[name=item-required]', function() {
      var numItemsMarkedAsRequired = $('input[name=item-required]:checked').length;
      if ($('input[name=num_required]').val() < numItemsMarkedAsRequired) {
        $('input[name=num_required]').val(numItemsMarkedAsRequired);
      }
  });

  var huntNamePrompt = "What's your hunt's name?";
  $('#name').on({
    keyup: function() {
      var newValue = $('#name').val();
      if (!newValue) {
        newValue = huntNamePrompt;
      }
      $('.form-group h3').text(newValue);
    },
    keydown: function(e) {
      // backspace or delete
      if (e.keyCode == 46 || e.keyCode == 8) {
        var newValue = $('#name').val().slice(0, -1);
        if (newValue.length == 0) {
          newValue = huntNamePrompt;
        }
        $('.form-group h3').text(newValue);
      }
    }
  });

  $('#domain').on({
    keyup: function() {
      var newValue = $(this).val();
      $('.explanation .by_domain span span').text(newValue);
    },
    keydown: function(e) {
      // backspace or delete
      if (e.keyCode == 46 || e.keyCode == 8) {
        var newValue = $('#domain').val().slice(0, -1);
        $('.explanation .by_domain span span').text(newValue);
      }
    }
  });

  $('#userinfo-form input').on('keyup', function(e) {
    // disable submitting form with enter
    if (e.keyCode == 13) {
      e.preventDefault();
      $('#confirm-email').click();
    }
  });

  $('#confirm-email').on('click', function(e) {
    var email = $('#email').val();
    if (email) {
      $(this).hide();
      $('.form-group').hide();
      $('.userinfo div:first-child').hide();
      $('#confirm-email-msg span').text(email);
      $('#confirm-email-msg').show();
      $('button[type=submit]').show();
      $('button#wrong-email').show();
      $('button#confirm-email').hide();
    }
  });

  $('#wrong-email').on('click', function(e) {
    $(this).hide();
    $('.form-group').show();
    $('.userinfo div:first-child').show();
    $('#confirm-email-msg').hide();
    $('button[type=submit]').hide();
    $('button#wrong-email').hide();
    $('button#confirm-email').show();
  });
});