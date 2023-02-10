#!/bin/env python
"""
tests for SSHComputingElement module
"""
import os
import shutil
import subprocess
import shlex
import pytest

import DIRAC

from DIRAC.Resources.Computing.SSHComputingElement import SSHComputingElement
from DIRAC.Resources.Computing.BatchSystems.executeBatch import executeBatchContent


@pytest.mark.parametrize("batchSystem", ["Condor", "GE", "Host", "LSF", "OAR", "SLURM", "Torque"])
def test_generateControlScript(batchSystem):
    """Test that the control script generated by the merging operation
    between a BatchSystem and executeBatch.py is:
    * complete: contains the content of both files
    * executable and doesn't raise any syntax error.

    Example: it may check that a __future__ import is not misplaced in the script due to the
    merging of the files.
    """

    ce = SSHComputingElement("Test_SSHCE")
    # Change the batch system file used during the control script generation
    ce.loadBatchSystem(batchSystem)
    # Get the local control script
    result = ce._generateControlScript()
    assert result["OK"] is True

    source = result["Value"]
    dest = "execute_batch.py"

    # Simulate operation done by the scpCall method

    # Copy the local control script into the "remote" control script
    # As the source can be composed of multiple files, we have to copy the content of each file
    sources = source.split(" ")
    with open(dest, "wb") as dst:
        for sourceFile in sources:
            with open(sourceFile, "rb") as src:
                shutil.copyfileobj(src, dst)

    # Test that the control script is complete
    with open(dest) as dst:
        dataDest = dst.read()

    batchSystemDir = os.path.join(os.path.dirname(DIRAC.__file__), "Resources", "Computing", "BatchSystems")
    batchSystemScript = os.path.join(batchSystemDir, f"{batchSystem}.py")
    with open(batchSystemScript) as bsc:
        dataBatchSystemScript = bsc.read()

    assert executeBatchContent in dataDest
    assert dataBatchSystemScript in dataDest

    # Test the execution of the remote control script
    cmd = f"python -m py_compile {dest}"
    args = shlex.split(cmd)
    process = subprocess.Popen(args, universal_newlines=True)
    process.communicate()
    assert process.returncode == 0

    # Delete the control script and the .pyc file associated
    os.remove(source)
    os.remove(dest)
    if os.path.isfile(f"{dest}c"):
        os.remove(f"{dest}c")
