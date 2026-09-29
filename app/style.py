"""Aspire brand palette applied to the Qt widgets."""
GOLD, ORANGE, RED, PINK, PLUM, NAVY, GREY = (
    "#f8bb13", "#ee7532", "#f04735", "#d6175c", "#b81a58", "#011d45", "#b2bbc7")

QSS = f"""
* {{ font-family: "Outfit"; font-size: 13px; color: {NAVY}; }}
QMainWindow, QWidget#page {{ background: #ffffff; }}
QLabel#title {{ font-size: 20px; font-weight: 700; color: #ffffff; }}
QLabel#subtitle {{ color: {GOLD}; }}
QWidget#header {{ background: {NAVY}; }}
QGroupBox {{ border: 1px solid {GREY}; border-radius: 8px; margin-top: 14px; padding: 10px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; font-weight: 600; }}
QLineEdit, QListWidget, QPlainTextEdit, QSpinBox {{
    border: 1px solid {GREY}; border-radius: 6px; padding: 4px; background: #ffffff; }}
QPlainTextEdit {{ font-family: "Consolas", "Menlo", "DejaVu Sans Mono", monospace; font-size: 12px; }}
QPushButton {{ border: 1px solid {NAVY}; border-radius: 6px; padding: 6px 14px; background: #ffffff; }}
QPushButton:hover {{ background: {GREY}; }}
QPushButton:disabled {{ color: {GREY}; border-color: {GREY}; }}
QPushButton#primary {{ background: {GOLD}; border-color: {GOLD}; font-weight: 700; }}
QPushButton#primary:hover {{ background: {ORANGE}; border-color: {ORANGE}; }}
QPushButton#primary:disabled {{ background: {GREY}; border-color: {GREY}; color: #ffffff; }}
QPushButton#danger {{ border-color: {PINK}; color: {PINK}; }}
QProgressBar {{ border: 1px solid {GREY}; border-radius: 6px; text-align: center; height: 20px; }}
QProgressBar::chunk {{ background: {GOLD}; border-radius: 5px; }}
QProgressBar#book::chunk {{ background: {ORANGE}; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ padding: 8px 18px; border-bottom: 3px solid transparent; }}
QTabBar::tab:selected {{ border-bottom: 3px solid {GOLD}; font-weight: 700; }}
QLabel#stat {{ font-size: 16px; font-weight: 700; }}
QLabel#statcap {{ color: {PLUM}; font-size: 11px; }}
QLabel#ocrok {{ color: {NAVY}; }}
QLabel#ocrbad {{ color: {RED}; font-weight: 700; }}
"""
