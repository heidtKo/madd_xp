import unittest
import argparse
from madd_xp.get_objects_in_template import parse_arg_list, get_arg_parser

class TestCliLogic(unittest.TestCase):

    def test_parse_arg_list_none(self):
        """Should return empty list for None input"""
        self.assertEqual(parse_arg_list(None), [])

    def test_parse_arg_list_simple_list(self):
        """Should return the list as-is if it contains multiple items"""
        self.assertEqual(parse_arg_list(["A", "B"]), ["A", "B"])

    def test_parse_arg_list_json_array(self):
        """Should parse a single string containing a JSON array"""
        self.assertEqual(parse_arg_list(['["A", "B"]']), ["A", "B"])

    def test_parse_arg_list_mixed_json_invalid(self):
        """Should return original list if JSON parsing fails or isn't a list"""
        self.assertEqual(parse_arg_list(['{"a":1}']), ['{"a":1}'])
        self.assertEqual(parse_arg_list(['not json']), ['not json'])

    def test_parser_defaults(self):
        """Test that parser sets correct defaults"""
        parser = get_arg_parser()
        args = parser.parse_args(['-u', 'myOrg', '-t', 'Template1'])
        self.assertEqual(args.username, 'myOrg')
        self.assertEqual(args.templates, ['Template1'])
        self.assertIsNone(args.output)
        self.assertFalse(args.json)

    def test_parser_full_args(self):
        """Test parser with all arguments provided"""
        parser = get_arg_parser()
        args = parser.parse_args([
            '-u', 'myOrg', 
            '-t', '["T1", "T2"]', 
            '-i', 'ID1', 'ID2', 
            '-o', 'out.csv'
        ])
        self.assertEqual(args.username, 'myOrg')
        self.assertEqual(args.templates, ['["T1", "T2"]']) # Parser sees raw string
        self.assertEqual(args.recordId, ['ID1', 'ID2'])
        self.assertEqual(args.output, 'out.csv')
        self.assertFalse(args.json)

    def test_parser_json_flag(self):
        parser = get_arg_parser()
        args = parser.parse_args(['-u', 'org', '-t', 'T1', '--json'])
        self.assertTrue(args.json)

if __name__ == '__main__':
    unittest.main()