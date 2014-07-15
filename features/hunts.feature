@browser
Feature: Hunts

    @need_admin
    Scenario: Create new hunt
    Given I am logged in
      And I am on the hunts page
     When clicking the "Create Hunt" button
     Then I should be directed to the "new_hunt" page
     When filling out the "name" field
      And entering 2 participant emails
     Then the email(s) should appear on the page
     When clicking the "all_required" radio button with value "true"
      And entering 2 item names
     Then the item should appear on the page
     When clicking the "messagetoggle" radio button with value "default"
     Then the "welcome_message" textarea should be displayed
     When clicking the "congratulationstoggle" radio button with value "default"
     Then the "congratulations_message" textarea should be displayed
     When clicking the "Submit Hunt" button
     Then I should be directed to the "/hunts" page
      And the text, "New scavenger hunt added", appears
      And the hunt name should appear on the page

    @need_admin @wip
    Scenario: Show and edit hunt - Add values
    Given I am logged in
      And a hunt
      And I am on the "hunts" page
     When clicking the hunt's name
     Then I should be directed to the "hunts/1" page
     When adding a participant
      And adding an item
      And changing the welcome message
     #  And adding a congratulations message
      And revisiting the "hunts/1" page
     Then the added data should appear on the page
