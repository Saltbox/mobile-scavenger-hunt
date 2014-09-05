(function() {
  'use strict';
  describe('New Hunt', function() {
    describe('validEmail', function() {
      it('returns true for valid email', function() {
        var email = 'valid@example.com';
        var valid = validEmail(email);
        assert.equal(valid, true);
      })

      it('returns false for valid email', function() {
        var email = 'invalid.example.com';
        var valid = validEmail(email);
        assert.equal(valid, false);
      })
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
  });
})();