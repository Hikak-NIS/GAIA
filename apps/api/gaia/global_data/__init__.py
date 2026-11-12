"""Providers must explicitly declare provenance; no silent real-to-demo fallback."""

from .demo import DemoProvider
from .copernicus import CopernicusProvider
from .nasa import NasaProvider
from .earth_engine import EarthEngineProvider

PROVIDERS = {p.key: p for p in (DemoProvider(), CopernicusProvider(), NasaProvider(), EarthEngineProvider())}
