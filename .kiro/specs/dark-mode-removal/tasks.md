# Implementation Plan: Dark Mode Removal

## Overview

This document outlines the implementation tasks for removing all non-functional dark mode code from the PaperAIzer codebase. The workflow follows the bug condition methodology: first explore and verify the bug exists, then preserve light mode behavior, then implement the fix.

---

## Phase 1: Exploration - Verify Dark Mode Code Exists

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Dark Mode Code Detection
  - **CRITICAL**: This test MUST PASS on unfixed code - passing confirms the bug exists
  - **GOAL**: Surface counterexamples that demonstrate dark mode code is present in the codebase
  - **Scoped PBT Approach**: Search for specific dark mode code patterns in known locations
  - Test that searches for dark mode code blocks in styles.css, home.html, and dashboard.html find matches (from Bug Condition in design)
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test PASSES (this confirms dark mode code exists - the bug is present)
  - Document counterexamples found:
    - Commented-out dark mode CSS block in styles.css (lines 1464-1623)
    - @media (prefers-color-scheme: dark) query in home.html (lines 16-19)
    - @media (prefers-color-scheme: dark) query in dashboard.html (lines 11-14+)
  - Mark task complete when test is written, run, and passing on unfixed code
  - _Requirements: 1.1, 1.2, 1.3_

---

## Phase 2: Preservation - Verify Light Mode Styling Integrity

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Light Mode Styling Integrity
  - **IMPORTANT**: Follow observation-first methodology
  - Observe: All light mode CSS variables in :root selector are functional on unfixed code
  - Observe: All pages (home, dashboard, upload, result, library) render correctly in light mode on unfixed code
  - Observe: Responsive design media queries for mobile/tablet breakpoints work correctly on unfixed code
  - Observe: All components (navbar, cards, buttons, forms) display correctly in light mode on unfixed code
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements in design:
    - CSS variables preservation: All :root variables (--bg-primary, --text-primary, --border-color, etc.) remain unchanged and functional
    - Component styling preservation: Navbar, cards, buttons, forms display correctly in light mode
    - Responsive design preservation: Media queries for mobile and tablet breakpoints function correctly
    - Page rendering preservation: All pages render correctly in light mode
    - Animation preservation: All animations and transitions continue to work
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline light mode behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

---

## Phase 3: Implementation - Remove Dark Mode Code

- [ ] 3. Fix for dark mode removal

  - [ ] 3.1 Remove commented-out dark mode CSS from styles.css
    - Locate the commented-out dark mode CSS block in static/css/styles.css (lines 1464-1623 approximately)
    - Delete the entire block starting with `/* ============ DARK MODE` and ending with the closing of the @media query
    - Verify the file ends cleanly after light mode CSS without any dark mode remnants
    - Verify file size is reduced after removal
    - _Bug_Condition: isBugCondition(codeElement) where codeElement contains "/* ============ DARK MODE" in styles.css_
    - _Expected_Behavior: Dark mode CSS block is completely removed from styles.css_
    - _Preservation: All light mode CSS variables and styling in :root selector remain unchanged_
    - _Requirements: 2.1, 3.1, 3.3_

  - [ ] 3.2 Remove dark mode media query from home.html
    - Locate the @media (prefers-color-scheme: dark) query in templates/analyzer/home.html (lines 16-19 approximately)
    - Delete the entire @media block containing dark mode overrides for .hero-subtitle and .hero-badge
    - Verify the template contains only light mode styles
    - _Bug_Condition: isBugCondition(codeElement) where codeElement contains "@media (prefers-color-scheme: dark)" in home.html_
    - _Expected_Behavior: Dark mode media query is completely removed from home.html_
    - _Preservation: All light mode styles in home.html remain unchanged_
    - _Requirements: 2.2, 3.2_

  - [ ] 3.3 Remove dark mode media query from dashboard.html
    - Locate the @media (prefers-color-scheme: dark) query in templates/analyzer/dashboard.html (lines 11-14+ approximately)
    - Delete the entire @media block containing dark mode variable overrides for :root and other elements
    - Verify the template contains only light mode styles
    - _Bug_Condition: isBugCondition(codeElement) where codeElement contains "@media (prefers-color-scheme: dark)" in dashboard.html_
    - _Expected_Behavior: Dark mode media query is completely removed from dashboard.html_
    - _Preservation: All light mode styles in dashboard.html remain unchanged_
    - _Requirements: 2.2, 3.2_

  - [ ] 3.4 Search for and remove any other dark mode code
    - Search all template files in templates/analyzer/ for any remaining @media (prefers-color-scheme: dark) queries
    - Search for any remaining dark mode-related comments or CSS
    - Remove any additional dark mode code found
    - Verify no other dark mode code exists in the codebase
    - _Bug_Condition: isBugCondition(codeElement) where codeElement contains dark mode code in any template_
    - _Expected_Behavior: All dark mode code is completely removed from all templates_
    - _Preservation: All light mode styles in all templates remain unchanged_
    - _Requirements: 2.3, 3.2_

  - [ ] 3.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Dark Mode Code Removal Verification
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 searches for dark mode code - it should now find NOTHING
    - When this test passes (finds no dark mode code), it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms dark mode code is completely removed)
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 3.6 Verify preservation tests still pass
    - **Property 2: Preservation** - Light Mode Styling Integrity Verification
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in light mode styling)
    - Confirm all light mode styling, CSS variables, responsive design, and animations continue to work correctly
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

---

## Phase 4: Checkpoint

- [ ] 4. Checkpoint - Ensure all tests pass
  - Verify bug condition exploration test passes (dark mode code is removed)
  - Verify preservation tests pass (light mode styling is intact)
  - Run full test suite to ensure no regressions
  - Verify all pages load correctly in light mode
  - Verify no console errors or warnings
  - Ask the user if questions arise
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4_

