var addItemsTable = function() {
   $('body').append('<table id="items-table"><tbody></tbody></table>');
};

(function() {
  'use strict';
  describe('New Hunt', function() {
    describe('validEmail', function() {
      it('returns true for valid email', function() {
        var email = 'valid@example.com';
        var valid = validEmail(email);
        assert.equal(valid, true);
      })

      it('returns false for email without @', function() {
        var email = 'invalid.example.com';
        var valid = validEmail(email);
        assert.equal(valid, false);
      })
    });

    describe('addParticipantRow', function() {
      before(function() {
        $('body').append('<table id="participants-table><tbody></tbody></table>');
      });

      after(function() {
        $('table').remove()
      });

      it('adds a row to the participants table', function() {
        addParticipantRow('whateveremail@example.com', true);
        should.exist($('input[name=participant]'));
      })
    });

    describe('addParticipantsToFormData', function() {
      var email = "mochaisfun@example.com";

      before(function() {
        $('body').append('<table id="participants-table"><tbody></tbody></table>');
        addParticipantRow(email, true)
      });

      after(function() {
        $('table').remove()
      });

      it('adds a participant email to formData', function() {
        var formData = addParticipantsToFormData({});
        assert.equal(formData['participants-0-email'], email);
      })
    });

    describe('addItemRow', function() {
      var allRequired = true;
      var itemCount = 0;
      var fieldValue = 'awesomest item';

      before(function() {
        $('body').append('<table><tbody id="items-table"></tbody></table>');
        addItemRow(allRequired, itemCount, fieldValue);
      });

      after(function() {
        $('table').remove();
      });

      it('adds an item to the items table', function() {
        var itemInput = $('input[value="' + fieldValue +'"]');
        should.exist(itemInput);
      });

      it('adds a checkmark icon to the item row when all items are required', function() {
        var glyphyiconOk = $('.td-with-span span.glyphicon.glyphicon-ok');
        should.exist(glyphyiconOk);
      });

      it('adds a delete icon to the item row', function() {
        var deleteIcon = $('.item-delete');
        should.exist(deleteIcon);
      });
    });

    describe('addItemsToFormData', function() {
      var allRequired = true;

      before(function() {
        addItemsTable();
      });

      beforeEach(function() {
        addItemRow(allRequired, 0, 'item1');
      })

      afterEach(function() {
        $('tr').remove();
      });

      after(function() {
        $('table').remove();
      })

      it('finds inputted item names and adds to formData when all items required', function() {
        addItemRow(allRequired, 1, 'item2');
        var formData = addItemsToFormData(allRequired, {});
        assert.equal(formData['items-0-name'], 'item1');
        assert.equal(formData['items-1-name'], 'item2');
      });

      it('marks required items as required when only some items are required', function() {
        var allRequired = false;
        addItemRow(allRequired, 1, 'item2');

        var formData = addItemsToFormData(allRequired, {});
        expect(formData['items-0-required']).to.be.undefined;
        assert.equal(formData['items-1-required'], true);
      });
    });

    describe('tooManyRequiredItems', function() {
      it('returns true when num_required is greater than number of items entered', function() {
        var formData = {
          'num_items': 5,
          'num_required': 6
        };
        var tooMany = tooManyRequiredItems(formData);
        assert.isTrue(tooMany);
      });
    });

    describe('missingRequiredFields', function() {
      it('returns false when all required fields have values', function() {
        var formData = {
          'name': 'a name',
          'items-0-name': 'awesome item',
          'participant_rule': 'anyone'
        };
        var hasMissing = missingRequiredFields(formData);
        assert.equal(hasMissing, false);
      })

      it('returns true when a required field is missing a value', function() {
        var formData = {
          'name': 'a name',
          'items-0-name': 'awesome item'
        };

        var hasMissing = missingRequiredFields(formData);
        assert.equal(hasMissing, true);

        formData = {
          'name': 'a name',
          'participant_rule': 'anyone'
        };

        hasMissing = missingRequiredFields(formData);
        assert.equal(hasMissing, true);

        formData = {
          'items-0-name': 'awesome item',
          'participant_rule': 'anyone'
        };

        hasMissing = missingRequiredFields(formData);
        assert.equal(hasMissing, true);
      })
    });

    describe('getting and sending form data', function() {
      var itemName = 'item1';
      var name = 'awesomest hunt';
      var checked = 'on';
      var all_required = true;
      var num_required = 1;
      var participant_rule = 'anyone';
      var welcome_message = 'welcome';
      var congratulations_message = 'congrats';

      before(function() {
        addItemsTable();
        addItemRow(true, 0, itemName);
        addParticipantRow('participant1@example.com', true);

        var otherInputs = [
          "<input id=name value='" + name + "'></input>",
          "<input name=all_required type=checkbox checked=" + checked + "></input>",
          "<input name=num_required value=" + num_required + "></input>",
          "<input name=participant_rule value=" + participant_rule + "></input>",
          "<textarea name=welcome_message>" + welcome_message + "</textarea>",
          "<textarea name=congratulations_message>" + congratulations_message + "</textarea>"
        ];
        for (var ii in otherInputs) {
          $('body').append(otherInputs[ii]);
        }
      });

      after(function() {
        $('table').remove();
        $('input').remove();
        $('textarea').remove();
      });

      describe('getFormData', function() {
        it('finds input values from html and puts it into formData', function() {
          var formData = getFormData();
          should.exist(formData);

          assert.equal(formData['items-0-name'], itemName);
          assert.equal(formData.name, name);
          assert.equal(formData.all_required, all_required);
          assert.equal(formData.num_required, num_required);
          assert.equal(formData.participant_rule, participant_rule);
          assert.equal(formData.welcome_message, welcome_message);
          assert.equal(formData.congratulations_message, congratulations_message);
        });
      });

      describe('validateFormData', function() {
        it('returns false when hunt name is less than 4 characters', function() {
          var formData = {'name': 'bad'};
          assert.isFalse(validateFormData(formData));
        });

        it('returns false when the all_required value is greater than items inputted', function() {
          var formData = {
            'name': 'hunt',
            'num_required': 2,
            'items-0-name': 'one'
          };
          assert.isFalse(validateFormData(formData));
        });

        it('returns false with a missing required field', function() {
          var formData = {};
          assert.isFalse(validateFormData(formData));
        });
      });

      describe('submitForm', function() {
        // maybe make this one of the integration tests
      });
    });
  });
})();