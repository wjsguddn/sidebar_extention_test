import "./LoadingSpinner.css";

export default function LoadingSpinner() {
    return (
        <div className="loading-spinner-bg">
            <div className="loading-spinner" />
            <span className="loading-text"></span>
        </div>
    );
}