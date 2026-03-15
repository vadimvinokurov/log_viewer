"""Highlight delegate for rendering highlighted text in table cells."""
from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QColor, QPainter, QTextDocument, QTextCharFormat, QTextOption

from src.core.highlight_engine import HighlightEngine


class HighlightDelegate(QStyledItemDelegate):
    """Delegate for rendering highlighted text in cells.
    
    This delegate uses a HighlightEngine to determine which text ranges
    should be highlighted and renders them with colored backgrounds.
    """
    
    def __init__(self, highlight_engine: Optional[HighlightEngine] = None, parent=None) -> None:
        """Initialize the highlight delegate.
        
        Args:
            highlight_engine: The highlight engine to use.
            parent: Parent object.
        """
        super().__init__(parent)
        self._highlight_engine = highlight_engine
    
    def set_highlight_engine(self, engine: Optional[HighlightEngine]) -> None:
        """Set the highlight engine.
        
        Args:
            engine: The highlight engine to use.
        """
        self._highlight_engine = engine
    
    def get_highlight_engine(self) -> Optional[HighlightEngine]:
        """Get the current highlight engine.
        
        Returns:
            The current highlight engine or None.
        """
        return self._highlight_engine
    
    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
        """Paint the cell with optional highlighting.
        
        Args:
            painter: The painter to use.
            option: Style options.
            index: Model index.
        """
        # Get the text to display
        text = index.data(Qt.DisplayRole)
        if text is None:
            super().paint(painter, option, index)
            return
        
        # Get background color from model
        bg_color = index.data(Qt.BackgroundRole)
        
        # Draw background
        if bg_color:
            painter.fillRect(option.rect, bg_color)
        else:
            # Draw default background
            painter.fillRect(option.rect, option.palette.base())
        
        # Draw selection highlight if selected
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor("#dcebf7"))
        
        # Set up text document for rich text rendering
        doc = QTextDocument()
        doc.setDocumentMargin(0)
        
        # CRITICAL: Disable text wrapping (per docs/specs/features/table-cell-text-overflow.md §3.2.1)
        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.NoWrap)
        doc.setDefaultTextOption(text_option)
        
        # Set default text color
        default_format = QTextCharFormat()
        if option.state & QStyle.State_Selected:
            default_format.setForeground(option.palette.highlightedText())
        else:
            default_format.setForeground(option.palette.text())
        doc.setDefaultFont(option.font)
        
        # Apply highlights if we have an engine
        if self._highlight_engine and isinstance(text, str):
            highlights = self._highlight_engine.highlight(text)
            if highlights:
                # Build highlighted text
                cursor_pos = 0
                result = ""
                
                for hl in highlights:
                    # Add text before highlight
                    if hl.start > cursor_pos:
                        result += text[cursor_pos:hl.start]
                    # Add highlighted text
                    highlighted_text = text[hl.start:hl.end]
                    result += f'<span style="background-color: {hl.color.name()};">{highlighted_text}</span>'
                    cursor_pos = hl.end
                
                # Add remaining text
                if cursor_pos < len(text):
                    result += text[cursor_pos:]
                
                doc.setHtml(result)
            else:
                doc.setPlainText(text)
        else:
            doc.setPlainText(text)
        
        # Get alignment from model (per docs/specs/features/table-column-alignment.md §3.1)
        alignment = index.data(Qt.TextAlignmentRole)
        if alignment is None:
            alignment = Qt.AlignLeft | Qt.AlignVCenter
        
        # Set document width to cell width for proper text layout
        doc.setTextWidth(option.rect.width())
        
        # Draw the text with alignment
        painter.save()
        
        # Clip to cell bounds (per docs/specs/features/table-cell-text-overflow.md §3.2.2)
        painter.setClipRect(option.rect)
        
        # Calculate horizontal offset based on alignment
        doc_height = doc.size().height()
        if alignment & Qt.AlignHCenter:
            # Center horizontally
            x_offset = (option.rect.width() - doc.idealWidth()) / 2
        elif alignment & Qt.AlignRight:
            # Right align
            x_offset = option.rect.width() - doc.idealWidth()
        else:
            # Left align (default)
            x_offset = 0
        
        # Calculate vertical offset based on alignment
        if alignment & Qt.AlignVCenter:
            y_offset = (option.rect.height() - doc_height) / 2
        elif alignment & Qt.AlignBottom:
            y_offset = option.rect.height() - doc_height
        else:
            y_offset = 0
        
        painter.translate(option.rect.topLeft())
        painter.translate(x_offset, y_offset)
        doc.drawContents(painter)
        painter.restore()