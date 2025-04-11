from dataclasses import dataclass
from typing import Callable, Union, Optional
from pathlib import Path
import threading
import ctypes
import win32api
import win32gui
import win32con
import win32clipboard

import logging

logger = logging.getLogger(__name__)


@dataclass
class Clip:
    type: str
    value: Union[str, list[Path]]

    def __eq__(self, value):
        if not isinstance(value, Clip):
            return False

        if self.type != value.type:
            return False

        match self.type:
            case "text" | "unicode":
                return self.value == value.value
            case "image":
                return self.value == value.value
            case "file":
                return len(self.value) == len(value.value) and all(
                    self.value[i] == value.value[i] for i in range(len(self.value))
                )
            case _:
                return False


class Clipboard:
    WM_CLIPBOARDUPDATE = 0x031D
    FORMATS = {
        win32con.CF_UNICODETEXT: "unicode",
        win32con.CF_TEXT: "text",
        win32con.CF_BITMAP: "image",
        win32con.CF_DIB: "image",
        win32con.CF_HDROP: "file",
    }

    def __init__(
        self,
        callbacks: dict[str, Callable[[Clip, "Clipboard"], None]] = None,
        default_callback: Callable[[Clip, "Clipboard"], None] = None,
    ):
        """
        Callbacks is a dict corresponding to the type of Clip plus an update callback:
        {
            "text": Callable[[Clip, Clipboard], None],
            "unicode": Callable[[Clip, Clipboard], None],
            "image": Callable[[Clip, Clipboard], None],
            "file": Callable[[Clip, Clipboard], None],
            "update": Callable[[Clip, Clipboard], None],
        }
        When Clipboard gets a Clip of type T, it will find the corresponding callback
        or use default_callback (which defaults to Clipboard.callback_nop) if not found.
        """
        self._callbacks = callbacks or {}
        self._default_callback = default_callback or Clipboard.callback_nop
        self._enabled = True
        self._last_clip = None

    def enable(self):
        """Enable the clipboard listener"""
        if not self._enabled:
            self._enabled = True

    def disable(self):
        """Disable the clipboard listener"""
        if self._enabled:
            self._enabled = False

    def _create_window(self) -> int:
        """
        Create a window for listening to messages
        :return: window hwnd
        """
        window_class = win32gui.WNDCLASS()
        window_class.lpfnWndProc = self._process_message
        window_class.lpszClassName = self.__class__.__name__
        window_class.hInstance = win32api.GetModuleHandle(None)
        class_atom = win32gui.RegisterClass(window_class)
        return win32gui.CreateWindow(
            class_atom,
            self.__class__.__name__,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            window_class.hInstance,
            None,
        )

    def _process_message(self, hwnd: int, msg: int, wparam: int, lparam: int):
        if not self._enabled:
            logger.debug("Clipboard listener is disabled")
            return 0

        if msg != Clipboard.WM_CLIPBOARDUPDATE:
            return 0

        logger.debug(
            "process message: hwnd=%s, msg=%s, wparam=%s, lparam=%s",
            hwnd,
            msg,
            wparam,
            lparam,
        )

        data = self.read_clipboard()
        logger.debug("Clipboard data: %s", data)
        if data is None:
            return 0

        if data == self._last_clip:
            # This prevents edit loops
            logger.debug("Clipboard data is the same, not processing")
            return 0

        self._callbacks.get(data.type, self._default_callback)(data, self)

        return 0

    @staticmethod
    def read_clipboard() -> Optional[Clip]:
        logger.debug("Reading clipboard")
        try:
            win32clipboard.OpenClipboard()
            clip_type = None
            for clipboard_format, clipboard_type in Clipboard.FORMATS.items():
                if win32clipboard.IsClipboardFormatAvailable(clipboard_format):
                    clip_type = clipboard_type
                    data = win32clipboard.GetClipboardData(clipboard_format)
                    break

            match clip_type:
                case "text":
                    return Clip(clip_type, data.decode("utf-8"))
                case "unicode":
                    return Clip(clip_type, data)
                case "image":
                    # TODO: Handle images
                    return None
                case "file":
                    return Clip(clip_type, [Path(file) for file in data])
                case _:
                    return None

        finally:
            win32clipboard.CloseClipboard()

    @staticmethod
    def write_clipboard(data: Clip, sender: "Clipboard") -> None:
        if data == sender.read_clipboard():
            logger.debug("Clipboard data is the same, not writing")
            return

        if not sender._enabled:
            logger.debug("Clipboard listener is disabled")
            return

        logger.info("Writing to clipboard: %s", data)
        sender.disable()
        try:
            win32clipboard.OpenClipboard()
            # win32clipboard.EmptyClipboard()
            match data.type:
                case "text" | "unicode":
                    win32clipboard.SetClipboardText(data.value, win32con.CF_UNICODETEXT)
                case "image":
                    win32clipboard.SetClipboardData(win32con.CF_BITMAP, data.value)
                case "file":
                    win32clipboard.SetClipboardData(win32con.CF_HDROP, data.value)
                case _:
                    raise ValueError(f"Unsupported clipboard type: {data.type}")
        finally:
            win32clipboard.CloseClipboard()

        sender._last_clip = data
        sender.enable()

    def listen(self):
        def runner():
            hwnd = self._create_window()
            ctypes.windll.user32.AddClipboardFormatListener(hwnd)
            win32gui.PumpMessages()

        # PumpMessages is blocking, so we need to run it in a separate thread
        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        while thread.is_alive():
            thread.join(0.25)

    # Callbacks
    @staticmethod
    def callback_nop() -> Callable[[Clip, "Clipboard"], None]:
        """Create a callback that does nothing"""

        def callback(clip: Clip, sender: "Clipboard") -> None:
            pass

        return callback

    @staticmethod
    def callback_print() -> Callable[[Clip, "Clipboard"], None]:
        """Create a callback that prints the clipboard data"""

        def callback(clip: Clip, sender: "Clipboard") -> None:
            print(clip)

        return callback

    @staticmethod
    def callback_edit(
        edit_function: Callable[[Clip], Clip],
    ) -> Callable[[Clip, "Clipboard"], None]:
        """Create a callback that edits the clipboard data"""

        def callback(clip: Clip, sender: "Clipboard") -> None:
            new_clip = edit_function(clip)
            if new_clip is not None:
                sender.write_clipboard(new_clip, sender)

        return callback

    @staticmethod
    def callback_multi(
        *args: Callable[[Clip, "Clipboard"], None]
    ) -> Callable[[Clip, "Clipboard"], None]:
        """
        Create a callback that applies multiple independent callbacks
        Each callback is expected to operate independently on the clip and return None.
        """

        def callback(clip: Clip, sender: "Clipboard") -> None:
            for callback_func in args:
                callback_func(clip, sender)

        return callback

    @staticmethod
    def callback_chain(
        *args: Callable[[Clip, "Clipboard"], Clip | None]
    ) -> Callable[[Clip, "Clipboard"], None]:
        """
        Create a callback chain that applies multiple callbacks in sequence.
        Each callback is expected to return a Clip or None.
        """

        def callback(clip: Clip, sender: "Clipboard") -> None:
            for callback_func in args:
                clip = callback_func(clip, sender)
                if clip is None:
                    break

        return callback


if __name__ == "__main__":
    def edit_func(clip: Clip) -> Clip:
        """Example edit function that converts text to uppercase"""
        return Clip(clip.type, clip.value.upper())

    clipboard = Clipboard(
        callbacks={
            "unicode": Clipboard.callback_edit(edit_func),
            "text": Clipboard.callback_edit(edit_func),
            "image": Clipboard.callback_nop(),
        },
        default_callback=Clipboard.callback_print(),
    )
    try:
        clipboard.listen()
    except KeyboardInterrupt:
        logger.info("Program terminated by user.")
