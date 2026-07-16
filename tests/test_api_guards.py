"""Unit tests for api.py's injection guards. Importing api triggers FastAPI
app construction (no network calls at import time), so this is safe without
Atlas/Mongo credentials configured."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ATLAS_PUBLIC_KEY", "")
os.environ.setdefault("ATLAS_PRIVATE_KEY", "")

from fastapi import HTTPException
import api


class TestAssertFilterIsSafe(unittest.TestCase):
    def test_plain_filter_is_allowed(self):
        api._assert_filter_is_safe({"status": "active", "amount": {"$gt": 100}})  # no raise

    def test_where_operator_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            api._assert_filter_is_safe({"$where": "this.a == this.b"})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_function_operator_rejected_nested(self):
        with self.assertRaises(HTTPException):
            api._assert_filter_is_safe({"$and": [{"$function": {}}]})

    def test_expr_operator_rejected(self):
        with self.assertRaises(HTTPException):
            api._assert_filter_is_safe({"$expr": {"$eq": ["$a", "$b"]}})

    def test_accumulator_operator_rejected(self):
        with self.assertRaises(HTTPException):
            api._assert_filter_is_safe({"$accumulator": {}})

    def test_unsafe_operator_inside_list_rejected(self):
        with self.assertRaises(HTTPException):
            api._assert_filter_is_safe({"$or": [{"a": 1}, {"$where": "1"}]})


class TestPrettyRegion(unittest.TestCase):
    def test_known_region(self):
        self.assertEqual(api.pretty_region("SA_EAST_1"), "AWS · São Paulo")

    def test_empty_dash(self):
        self.assertEqual(api.pretty_region("—"), "—")

    def test_unknown_region_titlecased(self):
        self.assertEqual(api.pretty_region("EU_NORTH_1"), "Eu North 1")


if __name__ == "__main__":
    unittest.main()
