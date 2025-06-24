import './Button.css';

export default function Button({ children, onClick, variant = 'primary', disabled = false, className = '' }) {
  return (
    <button 
      className={`ui-button ${variant} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
} 