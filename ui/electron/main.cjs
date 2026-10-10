const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('node:path')
const fs = require('node:fs')
const { startBackend, stopBackend, checkBackend } = require('./backend.cjs')

const isDev = process.argv.includes('--dev')
const DEV_PORT = process.env.PORT || process.env.VITE_PORT || 5173
const DEV_URL = process.env.VITE_DEV_SERVER_URL || process.env.ELECTRON_START_URL || `http://127.0.0.1:${DEV_PORT}`
const DIST_INDEX = path.resolve(__dirname, '../dist/index.html')

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 900,
    minHeight: 650,
    title: 'SONNET - Sonar Target Detection',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      webSecurity: false,
    },
  })

  // Keep the window title fixed even if the page <title> changes.
  win.on('page-title-updated', (e) => e.preventDefault())

  win.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    console.error(`[Electron] Failed to load ${validatedURL}: ${errorDescription} (${errorCode})`)
  })

  win.webContents.on('did-finish-load', () => {
    console.log('[Electron] Page loaded successfully in window.')
  })

  if (isDev) {
    win.loadURL(DEV_URL).catch((err) => {
      console.error('[Electron] Error loading DEV_URL:', err.message)
    })
  } else {
    if (!fs.existsSync(DIST_INDEX)) {
      console.error(`[Electron] Production build not found at: ${DIST_INDEX}. Please run 'npm run build' first.`)
    }
    win.loadFile(DIST_INDEX).catch((err) => {
      console.error('[Electron] Error loading dist/index.html:', err.message)
    })
  }
}

// IPC Handlers for frontend
ipcMain.handle('check-backend', async () => {
  return await checkBackend(1200)
})

ipcMain.handle('restart-backend', async () => {
  stopBackend()
  return await startBackend()
})

app.whenReady().then(async () => {
  console.log('[Electron] Initializing integrated FastAPI backend...')
  try {
    await startBackend()
  } catch (err) {
    console.error('[Electron] Backend startup error:', err)
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('before-quit', () => {
  stopBackend()
})

app.on('will-quit', () => {
  stopBackend()
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') app.quit()
})

process.on('SIGINT', () => {
  stopBackend()
  process.exit(0)
})

process.on('SIGTERM', () => {
  stopBackend()
  process.exit(0)
})

process.on('exit', () => {
  stopBackend()
})
