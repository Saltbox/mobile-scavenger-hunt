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

