from django.test import SimpleTestCase

from purchase.services.outsource_progress_compare import _collect_candidate_codes


def _word(x0, y0, x1, y1, text):
    return (x0, y0, x1, y1, text, 0, 0, 0)


class OutsourceProgressCompareTest(SimpleTestCase):
    def test_progress_candidate_codes_ignore_name_word_inside_block(self):
        words = [
            _word(14.1, 130.8, 57.1, 136.8, "YD40008380G"),
            _word(17.0, 140.7, 30.0, 146.7, "ブラケット"),
            _word(33.4, 140.7, 47.7, 146.7, "KTEG"),
            _word(47.7, 140.7, 88.0, 146.7, "typeB右"),
            _word(112.4, 149.2, 128.0, 155.2, "8/17"),
            _word(134.0, 149.2, 150.0, 155.2, "18日"),
            _word(90.0, 151.5, 100.0, 157.5, "繰越"),
            _word(60.9, 162.4, 82.0, 168.4, "内示"),
            _word(315.4, 162.4, 320.0, 168.4, "1"),
            _word(336.7, 162.4, 341.0, 168.4, "2"),
            _word(60.9, 171.5, 82.0, 177.5, "確定"),
            _word(124.1, 171.5, 129.0, 177.5, "3"),
            _word(145.4, 171.5, 150.0, 177.5, "4"),
            _word(14.1, 399.5, 67.0, 405.5, "YD40008457-06G"),
            _word(17.0, 409.5, 45.0, 415.5, "ブラケット06"),
            _word(112.4, 418.0, 128.0, 424.0, "8/17"),
            _word(60.9, 430.0, 82.0, 436.0, "内示"),
        ]

        candidates = _collect_candidate_codes(words, "progress")
        codes = [candidate[4] for candidate in candidates]

        self.assertEqual(codes, ["YD40008380G", "YD40008457-06G"])

    def test_progress_candidate_codes_accept_block_with_lower_header_position(self):
        words = [
            _word(14.0, 200.0, 58.0, 206.0, "YD40009999G"),
            _word(18.0, 210.0, 54.0, 216.0, "ブラケット"),
            _word(58.0, 210.0, 95.0, 216.0, "右"),
            _word(112.0, 223.5, 128.0, 229.5, "8/17"),
            _word(134.0, 223.5, 150.0, 229.5, "18日"),
            _word(90.0, 226.0, 104.0, 232.0, "繰越"),
            _word(60.9, 234.0, 82.0, 240.0, "内示"),
            _word(116.0, 234.0, 120.0, 240.0, "1"),
            _word(138.0, 234.0, 142.0, 240.0, "2"),
            _word(60.9, 244.0, 82.0, 250.0, "確定"),
            _word(116.0, 244.0, 120.0, 250.0, "3"),
        ]

        candidates = _collect_candidate_codes(words, "progress")
        codes = [candidate[4] for candidate in candidates]

        self.assertEqual(codes, ["YD40009999G"])
