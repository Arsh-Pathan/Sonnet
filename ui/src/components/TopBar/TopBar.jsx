import React from 'react'
import './TopBar.css'

export default function TopBar({
  activeTab,
  onTabChange,
  isConnected,
  modelReady = true,
  isProcessing = false,
  onOpenUpload,
  onFileSelected,
  onOpenExport,
  onOpenHistory,
}) {
  const fileInputRef = React.useRef(null)

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file && onFileSelected) {
      onFileSelected(file)
    }
    e.target.value = ''
  }

  const modelStatusLabel = !isConnected
    ? 'MODEL DISCONNECTED'
    : isProcessing
    ? 'INFERENCE IN PROGRESS'
    : modelReady
    ? 'YOLOv11s READY'
    : 'MODEL LOADING'

  return (
    <header className="topbar">
      {/* Brand */}
      <div className="topbar__brand">
        <svg className="topbar__logo-icon" width="20" height="20" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9.5" stroke="#3b82f6" strokeWidth="1.5" strokeOpacity="0.6" />
          <circle cx="12" cy="12" r="5.5" stroke="#3b82f6" strokeWidth="1.5" />
          <circle cx="12" cy="12" r="2" fill="#3b82f6" />
          <path d="M12 2.5v19M2.5 12h19" stroke="#3b82f6" strokeWidth="1" strokeOpacity="0.4" />
        </svg>
        <div className="topbar__brand-text">
          <span className="topbar__brand-name">SONNET</span>
          <span className="topbar__brand-sub">SONAR ANALYSIS</span>
        </div>
      </div>

      {/* Nav tabs */}
      <nav className="topbar__tabs" role="tablist" aria-label="Main navigation">
        <button
          role="tab"
          type="button"
          aria-selected={activeTab === 'LIVE'}
          className={`topbar__tab ${activeTab === 'LIVE' ? 'topbar__tab--active' : ''}`}
          onClick={() => onTabChange('LIVE')}
        >
          ANALYSIS WORKSPACE
        </button>
        <button
          role="tab"
          type="button"
          aria-selected={activeTab === 'ANALYSIS'}
          className={`topbar__tab ${activeTab === 'ANALYSIS' ? 'topbar__tab--active' : ''}`}
          onClick={() => onTabChange('ANALYSIS')}
        >
          ANALYTICS &amp; SUMMARY
        </button>
        <button
          role="tab"
          type="button"
          className="topbar__tab"
          onClick={onOpenExport}
        >
          EXPORT REPORT
        </button>
        <button
          role="tab"
          type="button"
          className="topbar__tab"
          onClick={onOpenHistory}
        >
          SESSION HISTORY
        </button>
      </nav>

      {/* Right side functional status & action */}
      <div className="topbar__right">
        {/* Backend health status */}
        <div className={`topbar__status-badge ${isConnected ? 'topbar__status-badge--online' : 'topbar__status-badge--offline'}`}>
          <span className="topbar__status-dot" />
          <span className="topbar__status-text">{isConnected ? 'SERVER ONLINE' : 'SERVER OFFLINE'}</span>
        </div>

        {/* Model status */}
        <div className={`topbar__status-badge ${isConnected && modelReady ? 'topbar__status-badge--model-ready' : 'topbar__status-badge--model-wait'}`}>
          <span className="topbar__status-dot" />
          <span className="topbar__status-text">{modelStatusLabel}</span>
        </div>

        {/* Primary Action Button: Process File */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".png,.jpg,.jpeg,.tiff,.xtf,.jsf"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <button
          type="button"
          className="topbar__action-btn"
          onClick={() => {
            if (onFileSelected) {
              fileInputRef.current?.click()
            } else {
              onOpenUpload()
            }
          }}
          title="Upload side-scan sonar image (.png, .jpg, .tiff) or raw survey log (.xtf, .jsf) to run YOLO detection"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          UPLOAD &amp; ANALYZE
        </button>
      </div>
    </header>
  )
}
