# Week 1 - Lyrics Trainer

## Overview
An interactive browser-based lyrics trainer application.

## How to Run
Open `index.html` directly in any standard browser or serve it locally. No server or API key required.

## Improvement Made
Added an active line counter indicator above the text input to track user typing progress in real time.

## Code Explanation
In `index.html`, an event listener attached to the input textarea calculates non-empty line splits and dynamically updates the DOM stats element.

## Model / Harness / App Distinction
- **Model:** The underlying LLM generating code recommendations.
- **Harness:** The execution environment/tooling providing context and running commands.
- **App:** The standalone `index.html` and assets running locally in the browser.

## Steering / Verification Example
Directed the model to add real-time line counting, verified output in local browser, and confirmed clean execution prior to final commit.
