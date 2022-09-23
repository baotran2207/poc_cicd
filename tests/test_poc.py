#!/usr/bin/env python
"""Tests for `poc` package."""
import pytest
from click.testing import CliRunner

from poc import poc
from poc import cli


@pytest.fixture
def dummy_fixture():
    """Dummy fixture to avoid import error."""
    return 'REPLACE ME!'



def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert 'poc.cli.main' in result.output
    help_result = runner.invoke(cli.main, ['--help'])
    assert help_result.exit_code == 0
    assert '--help  Show this message and exit.' in help_result.output
