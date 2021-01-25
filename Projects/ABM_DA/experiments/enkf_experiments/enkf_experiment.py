"""
main.py
@author: ksuchak1990
Python script for running experiments with the enkf.
"""

# Imports
import numpy as np
from experiment_utils import Modeller, Processor, Visualiser

np.random.seed(42)

Processor.process_batch()
