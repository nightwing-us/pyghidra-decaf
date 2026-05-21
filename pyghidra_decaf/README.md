pyghidra_decaf - Java-free Python plugin loading for Ghidra

Enables pure python ghidra plugins to be implemented by handling the boilerplate jpype glue
code to connect the java and python side plugin implementations.


# Installation

1. Activate (or create) the venv that will be used to run ghidra
2. Install `pyghidra_decaf` (`pip install pyghidra_decaf`)
3. Run ghidra `pyghidra --gui --install-dir /path/to/ghidra/install` (for example /home/user/ghidra/ghidra_11_3_2_PUBLIC)
4. You'll be prompted to enable a new plugin, confirm that. If not, open File -> Install Extensions and enable "Pyghidra Decaf"

# Installing Decaf plugins

1. Activate the venv you previously set up with pyghidra_decaf
2. Install the python module for the Decaf plugin (e.g. `pip install <your-decaf-plugin>`)
3. Run ghidra `pyghidra --gui --install-dir /path/to/ghidra/install` (for example /home/user/ghidra/ghidra_11_3_2_PUBLIC)
4. You'll be prompted to enable a new plugin, confirm that. If not, open File -> Install Extensions and enable "Pyghidra Decaf"
