.menubar {
  display: flex;
  gap: 16px;
}
.menu-item {
  color: var(--text-primary);
  text-decoration: none;
  font-size: 15px;
  padding: 6px 12px;
  border-radius: 4px;
  transition: background 0.2s;
}
.menu-item:hover {
  background: var(--bg-secondary);
}

.menubar-container {
  position: relative;
  display: flex;
  align-items: center;
}

.hamburger {
  width: 16px;
  height: 14px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  cursor: pointer;
  gap: 5px;
}
.hamburger span {
  display: block;
  height: 1px;
  width: 100%;
  background: var(--text-secondary);
  border-radius: 2px;
  transition: 0.2s;
}

.dropdown-menu {
  position: absolute;
  top: -5px;
  right: -5px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  box-shadow: none;
  min-width: 120px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  padding: 8px 0;
}
.menu-item {
  color: var(--text-primary);
  text-decoration: none;
  font-size: 13px;
  padding: 8px 20px;
  border: none;
  background: none;
  text-align: left;
  cursor: pointer;
  transition: background 0.3s;
}
.menu-item:hover {
  background: var(--border-color);
}

.theme-toggle-switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 20px;
  margin-left: 8px;
}
.theme-toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.theme-toggle-switch .slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: var(--border-color);
  transition: .4s;
  border-radius: 15px;
}
.theme-toggle-switch input:checked + .slider {
  background-color: var(--accent-primary);
}
.theme-toggle-switch .slider:before {
  position: absolute;
  content: "";
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
  background-color: var(--bg-primary);
  transition: .4s;
  border-radius: 50%;
}
.theme-toggle-switch input:checked + .slider:before {
  transform: translateX(17px);
}

.menubar-container .dropdown-menu {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}
.menu-item {
  color: var(--text-primary);
}
.menu-item:hover {
  background: var(--bg-primary);
  /*color: var(--bg-primary);*/
}

.dropdown-menu {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
}