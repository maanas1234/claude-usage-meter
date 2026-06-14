const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('claudeUsage', {
  onUpdate: (callback) => ipcRenderer.on('usage-update', (_event, data) => callback(data)),
  refresh: () => ipcRenderer.invoke('request-refresh'),
  login: () => ipcRenderer.invoke('request-login'),
  getLastResult: () => ipcRenderer.invoke('get-last-result')
});
