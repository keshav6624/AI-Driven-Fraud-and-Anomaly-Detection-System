"""MPLAD-Sentinel ML package.

Every score produced here is derived exclusively from the cleaned MP
allocation table (data/processed/mp_allocations_clean.csv). The package
never fabricates records; unavailable analytics are documented as
capability gaps (see ml/delay_prediction/capability.py).
"""
__all__ = ["config"]
