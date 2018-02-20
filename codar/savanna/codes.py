"""
Classes that generate support `Code`s to add to `Workflow`s.
"""

from codar.savanna.model import Code


builtin = {
    'sosflow': SOSFlowAugmentor,,
    'dataspaces': DataSpacesMaker,
    'stage_write': StageWriteMaker,
}


class WorkflowAugmentor(object):
    """Abstract base class.
    TODO: how to incorperate execution environment."""

    def add_codes(workflow):
        raise NotImplemented()


class SOSFlowAugmentor(CodeAugmentor):
    def add_codes(workflow):


class DataSpacesAugmentor(object):
    def add_codes(workflow):
        raise NotImplemented()


class StageWriteAugmentor(object):
    def add_codes(workflow):
        raise NotImplemented()
