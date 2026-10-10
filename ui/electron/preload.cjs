const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  },
  checkBackend: () => ipcRenderer.invoke('check-backend'),
  restartBackend: () => ipcRenderer.invoke('restart-backend'),
})
