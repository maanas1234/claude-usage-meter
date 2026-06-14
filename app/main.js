const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, screen } = require('electron');
const path = require('path');

const POLL_INTERVAL_MS = 60 * 1000;

let authWindow = null;
let widgetWindow = null;
let tray = null;
let pollTimer = null;
let lastResult = null;

const FETCH_SCRIPT = `
(async () => {
  try {
    const orgsRes = await fetch('/api/organizations', { credentials: 'include' });
    if (!orgsRes.ok) return { status: 'login-required' };
    const orgs = await orgsRes.json();
    if (!Array.isArray(orgs) || orgs.length === 0) return { status: 'no-orgs' };

    let org = orgs[0];
    try {
      const match = document.cookie.split('; ').find(c => c.startsWith('lastActiveOrg='));
      if (match) {
        const id = decodeURIComponent(match.split('=')[1]);
        const found = orgs.find(o => o.uuid === id);
        if (found) org = found;
      }
    } catch {}

    const usageRes = await fetch('/api/organizations/' + org.uuid + '/usage', { credentials: 'include' });
    if (!usageRes.ok) return { status: 'login-required' };
    const usage = await usageRes.json();
    return { status: 'ok', orgId: org.uuid, orgName: org.name, usage };
  } catch (e) {
    return { status: 'error', message: String(e && e.message || e) };
  }
})();
`;

function createAuthWindow() {
  authWindow = new BrowserWindow({
    width: 1000,
    height: 800,
    show: false,
    title: 'Sign in to Claude',
    webPreferences: {
      partition: 'persist:claude-usage-meter',
      contextIsolation: true
    }
  });
  authWindow.loadURL('https://claude.ai');

  authWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      authWindow.hide();
    }
  });
}

function createWidgetWindow() {
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;
  const winWidth = 320;
  const winHeight = 280;

  widgetWindow = new BrowserWindow({
    width: winWidth,
    height: winHeight,
    x: screenWidth - winWidth - 16,
    y: screenHeight - winHeight - 16,
    resizable: false,
    fullscreenable: false,
    maximizable: false,
    title: 'Claude Usage',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true
    }
  });
  widgetWindow.setMenuBarVisibility(false);
  widgetWindow.loadFile(path.join(__dirname, 'widget.html'));

  widgetWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      widgetWindow.hide();
    }
  });
}

function createTray() {
  const icon = nativeImage.createFromPath(path.join(__dirname, 'assets', 'icon.png'));
  tray = new Tray(icon.isEmpty() ? nativeImage.createEmpty() : icon);
  tray.setToolTip('Claude Usage Meter');

  const menu = Menu.buildFromTemplate([
    {
      label: 'Show usage',
      click: () => {
        widgetWindow.show();
        widgetWindow.focus();
      }
    },
    {
      label: 'Refresh now',
      click: () => fetchUsage()
    },
    {
      label: 'Sign in to Claude',
      click: () => {
        authWindow.show();
        authWindow.focus();
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);
  tray.setContextMenu(menu);
  tray.on('click', () => {
    if (widgetWindow.isVisible()) {
      widgetWindow.hide();
    } else {
      widgetWindow.show();
      widgetWindow.focus();
    }
  });
}

async function fetchUsage() {
  if (!authWindow) return;
  try {
    const result = await authWindow.webContents.executeJavaScript(FETCH_SCRIPT, true);
    lastResult = { ...result, fetchedAt: Date.now() };
  } catch (e) {
    lastResult = { status: 'error', message: String(e && e.message || e), fetchedAt: Date.now() };
  }
  console.log('[fetchUsage]', JSON.stringify(lastResult));

  if (lastResult.status === 'login-required' && authWindow.isVisible() === false) {
    authWindow.show();
    authWindow.focus();
  }
  if (lastResult.status === 'ok' && authWindow.isVisible()) {
    authWindow.hide();
  }

  if (widgetWindow) {
    widgetWindow.webContents.send('usage-update', lastResult);
  }
}

app.whenReady().then(() => {
  createAuthWindow();
  createWidgetWindow();
  createTray();

  // Wait briefly for claude.ai to load before first check
  setTimeout(fetchUsage, 3000);
  pollTimer = setInterval(fetchUsage, POLL_INTERVAL_MS);

  ipcMain.handle('request-refresh', () => fetchUsage());
  ipcMain.handle('request-login', () => {
    authWindow.show();
    authWindow.focus();
  });
  ipcMain.handle('get-last-result', () => lastResult);
});

app.on('window-all-closed', (e) => {
  // Keep running in tray
  e?.preventDefault?.();
});

app.on('before-quit', () => {
  app.isQuitting = true;
  if (pollTimer) clearInterval(pollTimer);
});
