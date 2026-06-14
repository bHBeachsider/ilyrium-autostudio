"""Ilyrium RSI L0 execution harness (ILY-203, Blueprint B).

The ONLY package allowed to import model SDKs or speak to the ComfyUI API.
Everything else calls through harness.run; the lint gate
(harness/lint_no_raw_sdk.py) enforces this structurally.
"""
