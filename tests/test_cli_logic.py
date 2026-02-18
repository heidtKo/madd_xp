import unittest
import argparse
import sys
from io import StringIO
from unittest.mock import patch
from madd_xp.copado_helper import parse_arg_list
from madd_xp.cli import main as cli_main

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

    @patch('madd_xp.get_objects_in_template.run')
    def test_cli_get_objects(self, mock_run):
        """Test 'mxp template get template objects' command parsing"""
        test_args = [
            'mxp', 'template', 'get', 'template', 'objects',
            '-u', 'myOrg',
            '-t', 'Template1'
        ]
        with patch.object(sys, 'argv', test_args):
            cli_main()
            
        self.assertTrue(mock_run.called)
        args = mock_run.call_args[0][0]
        self.assertEqual(args.username, 'myOrg')
        self.assertEqual(args.templates, ['Template1'])
        self.assertFalse(args.json)

    @patch('madd_xp.update_template_status.run')
    def test_cli_activate(self, mock_run):
        """Test 'mxp template activate' command parsing"""
        test_args = [
            'mxp', 'template', 'activate',
            '-u', 'myOrg',
            '-i', 'ID1'
        ]
        with patch.object(sys, 'argv', test_args):
            cli_main()
            
        self.assertTrue(mock_run.called)
        args, active = mock_run.call_args[0] # args, active=True
        self.assertEqual(args.username, 'myOrg')
        self.assertEqual(args.ids, ['ID1'])
        self.assertTrue(active)

    @patch('madd_xp.update_template_status.run')
    def test_cli_deactivate(self, mock_run):
        """Test 'mxp template deactivate' command parsing"""
        test_args = ['mxp', 'template', 'deactivate', '-u', 'myOrg', '-i', 'ID1']
        with patch.object(sys, 'argv', test_args):
            cli_main()
            
        self.assertTrue(mock_run.called)
        _, active = mock_run.call_args[0]
        self.assertFalse(active)

    @patch('madd_xp.analyze_files.run')
    def test_cli_analytics_files(self, mock_run):
        """Test 'mxp analytics files' command parsing"""
        test_args = ['mxp', 'analytics', 'files', '-u', 'myOrg', '-o', 'report.csv']
        with patch.object(sys, 'argv', test_args):
            cli_main()
            
        self.assertTrue(mock_run.called)
        args = mock_run.call_args[0][0]
        self.assertEqual(args.username, 'myOrg')
        self.assertEqual(args.output, 'report.csv')

    @patch('madd_xp.find_templates.run')
    def test_cli_template_find(self, mock_run):
        """Test 'mxp template find' command parsing"""
        test_args = ['mxp', 'template', 'find', '-u', 'myOrg', '-obj', 'Account', 'Contact', '--active', '--json']
        with patch.object(sys, 'argv', test_args):
            cli_main()
            
        self.assertTrue(mock_run.called)
        args = mock_run.call_args[0][0]
        self.assertEqual(args.username, 'myOrg')
        self.assertEqual(args.objects, ['Account', 'Contact'])
        self.assertTrue(args.active)
        self.assertTrue(args.json)

if __name__ == '__main__':
    unittest.main()