# Extension Setup Guide

## Step 1 — Google Cloud Console

1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. Go to APIs & Services → Credentials
4. Click "Create Credentials" → OAuth 2.0 Client ID
5. Application type: **Chrome Extension**
6. Add your Extension ID (you get this in Step 2)
7. Copy the Client ID

## Step 2 — Load Extension in Chrome

1. Open Chrome → go to `chrome://extensions`
2. Enable "Developer mode" (top right toggle)
3. Click "Load unpacked"
4. Select the `extension/` folder
5. Copy your Extension ID shown on the card

## Step 3 — Update Config

In `background.js`, replace:
```
const CLIENT_ID = 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com';
const BACKEND_URL = 'https://your-backend.railway.app';
```

With your actual values.

## Step 4 — Deploy Backend

1. Push the `backend/` folder to a new GitHub repo
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Add environment variable: `GROQ_API_KEY=your_key`
4. Copy the deployed URL → paste into `BACKEND_URL` in background.js

## Step 5 — Reload Extension

After updating background.js, go to chrome://extensions and click the refresh icon on your extension.

## Icons

Add PNG icon files to the `icons/` folder:
- icon16.png  (16x16)
- icon48.png  (48x48)
- icon128.png (128x128)

You can create these at https://favicon.io or use any image editor.
