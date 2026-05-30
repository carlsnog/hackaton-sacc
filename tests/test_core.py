import unittest

from pipeline.core import abstention_rate, normalize_name, normalized_percentile_ranks, nullable_number_with_reason, pearson, spearman


class CoreTest(unittest.TestCase):
    def test_normalize_name_removes_accents_and_pb_suffix(self):
        self.assertEqual(normalize_name("João Pessoa (PB)"), "JOAO PESSOA")

    def test_percentiles_are_normalized(self):
        self.assertEqual(normalized_percentile_ranks([10, 20, 30]), [0.0, 0.5, 1.0])

    def test_correlations(self):
        self.assertAlmostEqual(pearson([1, 2, 3], [2, 4, 6]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3], [6, 4, 2]), -1.0)

    def test_special_null_markers_keep_reason(self):
        self.assertEqual(nullable_number_with_reason("#NULO"), (None, "NULO_FONTE"))
        self.assertEqual(nullable_number_with_reason("-3"), (None, "NAO_EXISTIA_REGISTRO"))
        self.assertEqual(nullable_number_with_reason(""), (None, "VAZIO"))

    def test_abstention_rate_handles_zero_denominator(self):
        self.assertIsNone(abstention_rate(0, 0))
        self.assertEqual(abstention_rate(25, 100), 25.0)
