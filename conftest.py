import sys
import os

# Add the project root to sys.path so that 'commands', 'lib', and 'utils'
# are importable from any test file regardless of where pytest is invoked.
sys.path.insert(0, os.path.dirname(__file__))
