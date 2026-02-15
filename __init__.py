from aqt.gui_hooks import editor_did_init_buttons
from aqt.qt import QMenu, QShortcut, QAction, QCursor, QKeySequence
from aqt import mw
from aqt.utils import tooltip
import re
import json

try:
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QDialog, QMessageBox, QMainWindow     
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtCore import Qt, QObject, QTimer, QRegularExpression, QUrl
    from PyQt6.QtWebChannel import QWebChannel
    from PyQt6.QtGui import QClipboard
    pyqt_version = "PyQt6"
except ImportError:
    from PyQt5.QtWidgets import QApplication, QVBoxLayout, QDialog, QMessageBox, QMainWindow     
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtCore import Qt, QObject, QTimer, QRegExp, QUrl
    from PyQt5.QtWebChannel import QWebChannel
    from PyQt5.QtGui import QClipboard
    pyqt_version = "PyQt5"


def is_html_context(editor) -> bool:
    rf = editor.actions.get("removeFormat")
    if not rf:
        return False
    return rf.isEnabled()
    
def hotkey_for_index(i: int) -> str | None:
    if i < 9:
        return f"Ctrl+Shift+{i+1}"
    if i == 9:
        return "Ctrl+Shift+0"
    return None

# ---------- helpers ----------

def split_tag(tag: str) -> tuple[str, str]:
    """
    If there is $$, divide by before /after
    Otherwise after = ''
    """
    if "$$" in tag:
        before, after = tag.split("$$", 1)
        return before, after
    
    tag = tag.strip()    
    return tag, ""


def get_tags_from_config():
    cfg = mw.addonManager.getConfig(__name__)
    return cfg.get(
        "tags",
        [
            "<w1>$$</w1>",
            "<w2>$$</w2>",
            "<w3>$$</w3>",
            "<w4>$$</w4>",
            "<w5>$$</w5>",
            "<w6>$$</w6>",
            "<w7>$$</w7>",
            "<w8>$$</w8>",
            "<w9>$$</w9>",
            "<w0>$$</w0>",
            "&nbsp; [Ctrl+Shift+Space]",
            "removeformatALL() [Ctrl+Shift+-]"
        ],
    )

# ---------- core ----------

def on_menu_action(editor, tag_def: str):    
    if editor.web.hasFocus():        
        # especially an algorithm for some function
        if tag_def.strip() == "removeformatALL()":            
            editor.web.onCut()
            def cut_in_removeformatALL(): 
                html = editor.web._internal_field_text_for_paste                
                if html:
                    editor.doPaste(html, False, False)
            QTimer.singleShot(20, cut_in_removeformatALL)
            return
        else:        
            before, after = split_tag(tag_def)
            str_web_eval = f"wrap({before!r}, {after!r});"             

        editor.web._internal_field_text_for_paste = None
        editor.web.onCopy()
        
        def after_Copy():
            if editor.web._internal_field_text_for_paste or editor.web._get_clipboard_html_for_field(QClipboard.Mode.Clipboard):
                editor.web.eval(str_web_eval)
            else:
                if editor.web._internal_field_text_for_paste:
                    editor.web.eval(str_web_eval)
                else:
                    editor.web.onCut()
                    
                    def tooltipPaste():
                        tooltip("editor.web.onPaste(")                        
                    
                    def after_Cut():                        
                        text = editor.web._internal_field_text_for_paste
                        if text:
                            editor.web.eval(str_web_eval)
                            #tooltip("text=" + text)
                        else:
                            clp = editor.web._clipboard()
                            if clp:
                                text = clp.text()                                
                                clp.setText(wrapped)
                                QTimer.singleShot(50, editor.web.onPaste)
                                QTimer.singleShot(80, tooltipPaste)
                    
                    QTimer.singleShot(50, after_Cut)
                    
        QTimer.singleShot(50, after_Copy)
   

def add_editor_buttons(buttons, editor):
    menu = QMenu(editor.widget)
    tags = get_tags_from_config()

    # We store it so that GC doesn’t kill shortcuts
    if not hasattr(editor, "_wrap_shortcuts"):
        editor._wrap_shortcuts = []

    userHotKey = 0
    for i, tag_def in enumerate(tags):        
        # if a hotkey is added to []
        pattern = r'\s+\[([^\]]+)\]$'  # looks for space then [combination] at the end of the line
        match = re.search(pattern, tag_def)
        if match:            
            userHotKey += 1
            hotkey = match.group(1)
            tag_def = re.sub(pattern, '', tag_def)
        else:
            hotkey = hotkey_for_index(i-userHotKey)

        label = tag_def
        if hotkey:
            label = f"{tag_def}"

        # --- menu item ---
        action = QAction(label, editor.widget)
        action.triggered.connect(
            lambda _, v=tag_def, e=editor: on_menu_action(e, v)
        )
        action.setShortcut(QKeySequence(hotkey))
        menu.addAction(action)

        # --- hotkey ---
        if hotkey:
            sc = QShortcut(
                QKeySequence(hotkey),
                editor.widget,
                activated=lambda v=tag_def, e=editor: on_menu_action(e, v),
            )
            editor._wrap_shortcuts.append(sc)
            

    def show_menu(_):
        menu.exec(QCursor.pos())

    btn = editor.addButton(
        icon=None,
        cmd="wrap_with_tag",
        func=show_menu,
        tip="Wrap selection with tag",
        label="&lt;t&gt;"
    )

    buttons.append(btn)


editor_did_init_buttons.append(add_editor_buttons)
