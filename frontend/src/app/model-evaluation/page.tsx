export default function ModelEvaluation() {
  return (
    <>
      <div className="sr-page-header">
        <h1 className="sr-page-title">Model Evaluation</h1>
        <p className="sr-page-description">
          ML model performance monitoring and evaluation reports
        </p>
      </div>

      <div className="sr-card">
        <div className="sr-empty-state">
          <div className="sr-empty-icon">◧</div>
          <h2 className="sr-empty-title">No models evaluated yet</h2>
          <p className="sr-empty-description">
            Model evaluation metrics — precision, recall, calibration curves,
            and feature importance — will appear here after the ML risk model
            is trained and evaluated.
          </p>
          <div className="sr-empty-badge">Available in Stage 2+</div>
        </div>
      </div>
    </>
  );
}
