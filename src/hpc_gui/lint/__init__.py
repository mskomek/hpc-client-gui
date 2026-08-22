"""Generic declarative lint engine.

Application-generic by design: no application-specific rule IDs live here.
Rule packs are declarative data (JSON) provided by official plugins; the
engine never executes rule content.
"""
