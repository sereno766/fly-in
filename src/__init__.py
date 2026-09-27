"""Public interface for the Fly-in source package."""

from .parser import ParseError, Parser

__all__ = ["Parser", "ParseError"]
