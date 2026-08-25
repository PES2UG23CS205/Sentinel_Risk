export default function LiveFeed() {
  return (
    <>
      <div className="sr-page-header">
        <h1 className="sr-page-title">Live Risk Feed</h1>
        <p className="sr-page-description">
          Real-time transaction risk events and alerts
        </p>
      </div>

      <div className="sr-card">
        <div className="sr-empty-state">
          <div className="sr-empty-icon">◉</div>
          <h2 className="sr-empty-title">No live events yet</h2>
          <p className="sr-empty-description">
            The live risk feed will display real-time transaction scoring events
            once the ML pipeline and event simulator are connected.
          </p>
          <div className="sr-empty-badge">Available in Stage 2+</div>
        </div>
      </div>
    </>
  );
}
