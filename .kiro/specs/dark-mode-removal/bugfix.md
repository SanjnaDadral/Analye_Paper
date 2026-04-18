# Bugfix Requirements Document: Dark Mode Removal

## Introduction

The PaperAIzer website contains non-functional dark mode implementation that creates technical debt and confusion. The dark mode CSS is commented out in the main stylesheet, and incomplete dark mode media queries are scattered across multiple templates. This bugfix removes all dark mode-related code to clean up the codebase and ensure the website operates cleanly in light mode only.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the website is loaded THEN the styles.css file contains a large block of commented-out dark mode CSS at the end of the file that serves no functional purpose

1.2 WHEN templates are rendered (home.html, dashboard.html, contact.html) THEN they contain incomplete @media (prefers-color-scheme: dark) queries with dark mode variable overrides that are never applied

1.3 WHEN the codebase is reviewed THEN dark mode-related CSS variables and styles are present but non-functional, creating confusion about the intended design system

### Expected Behavior (Correct)

2.1 WHEN the website is loaded THEN the styles.css file SHALL NOT contain any commented-out dark mode CSS code

2.2 WHEN templates are rendered THEN they SHALL NOT contain any @media (prefers-color-scheme: dark) queries or dark mode-related style overrides

2.3 WHEN the codebase is reviewed THEN all dark mode-related CSS code SHALL be completely removed from the repository

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the website is accessed in light mode THEN all visual styling, colors, and layouts SHALL CONTINUE TO display correctly without any changes to appearance or functionality

3.2 WHEN pages are rendered (home, dashboard, contact, upload, etc.) THEN all light mode styles SHALL CONTINUE TO apply correctly and consistently

3.3 WHEN CSS variables are used throughout the codebase THEN the light mode color scheme (--bg-primary, --text-primary, etc.) SHALL CONTINUE TO work as defined in the :root selector

3.4 WHEN responsive design is applied THEN all media queries for mobile and tablet breakpoints SHALL CONTINUE TO function correctly
