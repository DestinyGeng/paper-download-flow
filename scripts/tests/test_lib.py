#!/usr/bin/env python3
"""lib 的核心测试：覆盖今天踩过的坑。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from lib import js_expr, naming, errors, manifest


class TestJsExpr(unittest.TestCase):
    def test_chinese_preserved(self):
        expr = js_expr.js('信,解,房')
        self.assertIn('信', expr)

    def test_no_raw_quote_break(self):
        expr = js_expr.find_by_text('PDF下载')
        self.assertIn('PDF下载', expr)
        self.assertTrue(expr.startswith('Array.from'))

    def test_read_body_bounded(self):
        self.assertEqual(js_expr.read_body(100), 'document.body.innerText.slice(0,100)')

    def test_mark_visible_by_id(self):
        expr = js_expr.mark_visible_by_id('pdfDown')
        self.assertIn('pdfDown', expr)
        self.assertIn('getBoundingClientRect', expr)


class TestNaming(unittest.TestCase):
    def test_plain_title(self):
        self.assertEqual(naming.fname('Pairs Trading'), 'Pairs Trading.pdf')

    def test_chinese_strips_author(self):
        self.assertEqual(naming.fname('配对交易实证_刘喆'), '配对交易实证.pdf')

    def test_illegal_chars(self):
        self.assertEqual(naming.fname('a/b:c?d'), 'a b c d.pdf')

    def test_truncate(self):
        self.assertLessEqual(len(naming.fname('x' * 200)), 84)

    def test_unique(self):
        exists = lambda n: n == 'A.pdf'
        self.assertEqual(naming.unique('A', exists), 'A_v2.pdf')


class TestErrors(unittest.TestCase):
    def test_timeout(self):
        self.assertEqual(errors.from_exception(Exception('The read operation timed out')), errors.TIMEOUT)

    def test_403(self):
        self.assertEqual(errors.from_exception(Exception('HTTP Error 403: Forbidden')), errors.HTTP_4XX)

    def test_ssl(self):
        self.assertEqual(errors.from_exception(Exception('[SSL: CERTIFICATE_VERIFY_FAILED]')), errors.FETCH_FAILED)


class TestManifest(unittest.TestCase):
    def test_normalize_fills_fields(self):
        rec = manifest.normalize({'title': 'X'})
        self.assertEqual(rec['download'], 'not_requested')
        self.assertIsNone(rec['doi'])

    def test_counts(self):
        self.assertEqual(manifest.counts([{'download': 'ok'}, {'download': 'ok'}]), {'ok': 2})


if __name__ == '__main__':
    unittest.main(verbosity=2)
