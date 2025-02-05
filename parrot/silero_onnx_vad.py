# ------- ONNX Silero VAD wrapper (16 kHz: 512 samples per call) -------
import numpy as np
import onnxruntime as ort

class SileroOnnxVAD:
    """
    ONNX Runtime wrapper for Silero-VAD.
    - 16 kHz: pass exactly 512-sample float32 mono in [-1, 1]
    - Maintains internal 'state' and 'context' between calls
    """
    def __init__(self, path: str, force_cpu: bool = True):
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        providers = ['CPUExecutionProvider'] if (force_cpu and
                     'CPUExecutionProvider' in ort.get_available_providers()) else None
        self.sess = ort.InferenceSession(path, providers=providers, sess_options=opts)
        self._state = None
        self._context = None
        self._last_sr = 0
        self._last_bs = 0

    def _frame_len(self, sr: int) -> int:
        return 512 if sr == 16000 else 256

    def _ctx_len(self, sr: int) -> int:
        # Matches Silero's sample wrapper: 64 at 16 kHz, 32 at 8 kHz
        return 64 if sr == 16000 else 32

    def reset_states(self, batch_size: int = 1):
        self._state = np.zeros((2, batch_size, 128), dtype=np.float32)
        self._context = None

    def _prepare(self, x: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
        if x.ndim == 1:
            x = x[None, :]
        if x.ndim != 2:
            raise ValueError(f"Expected 1D/2D audio, got {x.ndim}D")
        if sr not in (8000, 16000):
            raise ValueError("Silero VAD supports 8000 or 16000 Hz")
        return x.astype(np.float32), sr

    def __call__(self, chunk: np.ndarray, sr: int) -> np.ndarray:
        """
        chunk: (T,) or (B,T) float32 mono in [-1,1]; T must equal 512 (16 kHz) or 256 (8 kHz)
        returns: speech probabilities (B, 1) or similar
        """
        x, sr = self._prepare(chunk, sr)
        T = self._frame_len(sr)
        if x.shape[1] != T:
            raise ValueError(f"Chunk must be {T} samples for sr={sr}, got {x.shape[1]}")
        B = x.shape[0]
        # init/resize state + context if needed
        if self._state is None or self._last_sr != sr or self._last_bs != B:
            self.reset_states(B)
        if self._context is None:
            self._context = np.zeros((B, self._ctx_len(sr)), dtype=np.float32)

        x_ctx = np.concatenate([self._context, x], axis=1)
        inputs = {
            'input': x_ctx.astype(np.float32),
            'state': self._state.astype(np.float32),
            'sr': np.array(sr, dtype=np.int64),
        }
        out, new_state = self.sess.run(None, inputs)
        # update rolling state & context
        self._state = new_state
        self._context = x_ctx[:, -self._ctx_len(sr):]
        self._last_sr, self._last_bs = sr, B
        return out
# ----------------------------------------------------------------------