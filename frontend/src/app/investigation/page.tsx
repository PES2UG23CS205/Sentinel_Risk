export default function Investigation() {
  return (
    <>
      <div className="sr-page-header">
        <h1 className="sr-page-title">Investigation</h1>
        <p className="sr-page-description">
          AI-assisted transaction investigation and evidence analysis
        </p>
      </div>

      <div className="sr-card">
        <div className="sr-empty-state">
          <div className="sr-empty-icon">⊘</div>
          <h2 className="sr-empty-title">Investigation agent not connected</h2>
          <p className="sr-empty-description">
            The autonomous investigation agent will gather evidence, analyze
            transaction patterns, and generate structured investigation reports
            using LangGraph.
          </p>
          <div className="sr-empty-badge">Available in Stage 4</div>
        </div>
      </div>
    </>
  );
}
