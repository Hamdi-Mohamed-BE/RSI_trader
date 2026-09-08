# YT Stream Copy

Local dashboard for monitoring a YouTube trading livestream. It transcribes the stream, detects trade language, keeps evidence, and calculates an indicative MT5 lot size using 1% of current equity.

## Start

1. Double-click `INSTALL.bat` once.
2. Keep MetaTrader 5 open and connected to the account you want to inspect.
3. Double-click `RUN YT STREAM COPY.bat`.
4. Paste the current livestream URL and select **Start monitoring**.

The first run downloads the configured Whisper model. With a 4 GB RTX 3050 Ti, `small.en` is the default. If CUDA loading fails, the program automatically uses CPU transcription.

## Review workflow

The detector keeps recent conversational context, so fragmented phrases such as “Gold” followed later by “press buy” and “we’re in” are handled as one event. Explicit entries open a paper position immediately at the connected MT5 quote. An explicitly spoken exit closes that paper position. Candle commentary such as “closed above VWAP” is not treated as an exit.

The monitor also captures a stream frame every few seconds and performs local OCR. Clearly labelled Entry/Open, SL/Stop and TP/Target values can fill missing paper-trade levels; unlabelled chart-axis prices are displayed for review but are never guessed into a position.

With `AUTO_PAPER=true`, confirmed entries are marked `paper_open`. If no stop has been stated, they are marked `paper_open_unprotected` and use the `NO_SL_PAPER_VOLUME` fallback (0.04 lot by default). Once a valid stop is available, that fallback is replaced by broker-specific 1% risk sizing. This mode records the signal; it never submits, modifies or closes an MT5 order.

Prepared comments use `Stream {channel name}` and are shortened to MT5's 31-character comment limit.

GC and NQ statements are mapped only for risk calculation to the broker's discovered XAU/US100 instruments. The dashboard keeps the spoken instrument visible because futures and CFDs can have different prices.

## Configuration

Edit `.env` to change the local port, risk percentage, transcription model, or chunk size. Keep `RISK_PERCENT=1.0` to enforce the agreed per-idea sizing.
