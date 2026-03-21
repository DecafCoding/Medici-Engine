---
description: Switch to main branch and pull latest changes
---

# Switch to Main

## Step 1: Check for Uncommitted Changes

Run `git status --porcelain` to check for staged or unstaged changes.

If there is any output, warn the user that they have uncommitted changes and list the affected files. Ask if they want to proceed before continuing. If they decline, stop.

## Step 2: Switch to Main

Run `git checkout main`.

## Step 3: Pull Latest

Run `git pull` to get the latest changes.

## Step 4: Report to User

Confirm:
- **Now on branch:** main
- **At commit:** short SHA and commit message from HEAD
- **Pulled:** how many new commits came in (or "already up to date")
