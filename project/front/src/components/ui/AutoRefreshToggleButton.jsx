import './AutoRefreshToggleButton.css';
import Button from '../ui/Button';

export default function AutoRefreshToggleButton({ enabled, onToggle }) {
    // const iconSrc = enabled
    //   ? "/icons/disable.png"
    //   : "/icons/activate.png";
    const iconSrc = "/icons/p_dot.png";

    return (
      <Button className={`auto-refresh-toggle-btn${enabled ? " enabled" : ""}`}
        onClick={onToggle}>
        <img src={iconSrc}
        style={{ width: 30, height: 30, marginLeft: "3px", marginBottom: "3px" }}/>
        <span className="tooltip">
          {enabled ? "AutoMode 비활성화" : "AutoMode 활성화"}
        </span>
      </Button>
    );
}