# DEMO: UART Communication Failure

## Symptom

The device sends status messages over UART every 500 ms, but the host PC
occasionally receives garbled output such as:

```
COUNT=0
COUNT=COUNT=1COUNT=2
2
COUNT=3
```

Messages are interleaved; some are truncated or split across lines.

## Expected Behavior

Each message arrives as a complete, separate line:
```
COUNT=0
COUNT=1
COUNT=2
```

## Root Causes (intentionally introduced)

1. **Non-atomic TX buffer write** (`uart.c:42–47`): `uart_send_string` updates
   `tx_head` without disabling the UDRE interrupt. The ISR can fire mid-write
   and advance `tx_tail`, producing interleaved output.

2. **Baud rate integer truncation** (`uart.c:25`): `UBRR_VALUE` uses integer
   division without rounding, introducing a small baud rate error that
   accumulates and causes framing errors at high rates or with long messages.

## How to Demo

Load this project in the Embedded Debugging Copilot:
- Source folder: `demo/uart_failure/src/`
- Symptom: "UART messages are garbled and interleaved"
- Expected: "Each message arrives as a complete line"

The copilot will identify the ISR/main race condition and baud rate bug.
