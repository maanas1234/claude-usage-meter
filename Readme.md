# Claude Usage Meter

A small Windows tray app that shows your Claude.ai chat usage: how much of your
**5-hour session limit** and **weekly (7-day) limit** you've used, and when each
resets.

## How it works

- The app keeps a hidden, persistent browser session signed in to claude.ai
  (just like the official Claude desktop app).
- It periodically calls the same `/api/organizations/{orgId}/usage` endpoint
  that claude.ai's own UI and extensions like Tally use, from that session.
- Nothing is sent to any third-party server — everything stays on your machine.

**Note:** this uses an undocumented Anthropic endpoint. If Anthropic changes
it, the app may need an update.

## Run it

```
npm install
npm start
```

On first run, a "Sign in to Claude" window will pop up — log in the same way
you would on claude.ai. After that, it stays signed in and the window stays
hidden; only the small usage widget is shown.

The widget sits in the bottom-right corner of your screen and also adds a tray
icon. Click the tray icon to show/hide the widget, refresh, or sign in again.

## Build a Windows installer

```
npm run dist
```

This produces an NSIS installer (`.exe`) in `dist/`.
