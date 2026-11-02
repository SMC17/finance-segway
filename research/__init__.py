"""Research tracks. Not part of the model library; see research/ram/STAGE_GATES.md.

This file exists so `unittest discover -s research -t .` can import the
package: without it discovery raises "Start directory is not importable"
and the three test modules under research/ ran in no CI job at all. A
discovered directory picks up a new test file on its own; a hand-listed
set of module names is one more list someone has to remember to update.
"""
