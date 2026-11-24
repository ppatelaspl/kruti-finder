"""Background workers. All heavy work runs off the UI thread; the UI only receives
throttled progress signals, so it stays responsive with hundreds of books."""
import logging
import traceback

from PySide6.QtCore import QObject, Signal

from kruti.pipeline import Cancelled, Controller, run


class _SignalLogHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__(logging.INFO)
        self._signal = signal

    def emit(self, record):
        self._signal.emit(self.format(record))


class RunWorker(QObject):
    progress = Signal(object)      # kruti.pipeline.Progress
    log = Signal(str)
    finished = Signal(object)      # kruti.pipeline.RunResult
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, excel, inputs, out_dir, cfg):
        super().__init__()
        self.excel, self.inputs, self.out_dir, self.cfg = excel, inputs, out_dir, cfg
        self.ctl = Controller()

    def run(self):
        handler = _SignalLogHandler(self.log)
        handler.setFormatter(logging.Formatter("%(message)s"))
        engine_log = logging.getLogger("kruti")
        engine_log.addHandler(handler)
        engine_log.setLevel(logging.INFO)
        try:
            result = run(self.excel, self.inputs, self.out_dir, self.cfg,
                         on_progress=self.progress.emit, log=self.log.emit, ctl=self.ctl)
            self.finished.emit(result)
        except Cancelled:
            self.cancelled.emit()
        except ValueError as e:                     # expected input problems
            self.failed.emit(str(e))
        except Exception:                           # noqa: BLE001 - show, never crash the UI
            self.failed.emit(traceback.format_exc())
        finally:
            engine_log.removeHandler(handler)


class GathaWorker(QObject):
    """Runs Gatha Lines (kruti.gatha_pipeline.run_gatha) off the UI thread."""
    progress = Signal(object)      # kruti.pipeline.Progress (+ gathas_found)
    log = Signal(str)
    finished = Signal(object)      # kruti.gatha_pipeline.GathaResult
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, inputs, out_dir, cfg):
        super().__init__()
        self.inputs, self.out_dir, self.cfg = inputs, out_dir, cfg
        self.ctl = Controller()

    def run(self):
        from kruti.gatha_pipeline import run_gatha

        handler = _SignalLogHandler(self.log)
        handler.setFormatter(logging.Formatter("%(message)s"))
        engine_log = logging.getLogger("kruti")
        engine_log.addHandler(handler)
        engine_log.setLevel(logging.INFO)
        try:
            result = run_gatha(self.inputs, self.out_dir, self.cfg,
                               on_progress=self.progress.emit, log=self.log.emit, ctl=self.ctl)
            self.finished.emit(result)
        except Cancelled:
            self.cancelled.emit()
        except ValueError as e:
            self.failed.emit(str(e))
        except Exception:                           # noqa: BLE001 - show, never crash the UI
            self.failed.emit(traceback.format_exc())
        finally:
            engine_log.removeHandler(handler)
