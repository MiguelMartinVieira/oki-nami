"""Tests para services/projections.py — fiscalidad."""

import pytest

from services.projections import calc_tax_spain


class TestCalcTaxSpain:
    def test_sin_plusvalia(self):
        assert calc_tax_spain(0) == 0.0
        assert calc_tax_spain(-100) == 0.0

    def test_primer_tramo(self):
        # 1000€ * 19% = 190€
        assert calc_tax_spain(1000) == 190.0

    def test_limite_primer_tramo(self):
        # 6000€ * 19% = 1140€
        assert calc_tax_spain(6000) == 1140.0

    def test_segundo_tramo(self):
        # 10000€ plusvalia:
        # 6000 * 0.19 = 1140
        # 4000 * 0.21 = 840
        # Total = 1980
        assert calc_tax_spain(10000) == 1980.0

    def test_plusvalia_muy_alta(self):
        # 250k plusvalia:
        # 6k * 0.19 = 1140
        # 44k * 0.21 = 9240
        # 150k * 0.23 = 34500
        # 50k * 0.26 = 13000
        # Total = 57880
        assert calc_tax_spain(250000) == 57880.0
