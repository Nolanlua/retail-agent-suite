"""Shared primitives used by every service in the suite.

Keeping configuration, auth and telemetry in one package avoids the classic
problem of each microservice inventing its own error shape and log format.
"""
