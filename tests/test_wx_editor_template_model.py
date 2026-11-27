from hpc_gui.plugins.job_templates import JobTemplate
from hpc_gui.wx_editor import WxEditorModel


def test_render_template_always_opens_a_new_unsaved_document():
    model = WxEditorModel()
    model.open("/remote/existing.slurm", "original")
    template = JobTemplate("example", "Example", "slurm", "test.plugin", "1", "job.slurm",
                           content="#!/bin/bash\necho example\n")
    model.render_template(template, {}, session_key="pinned")
    model.render_template(template, {}, session_key="pinned")
    assert len(model.controller.documents) == 3
    assert model.controller.documents[0].content == "original"
    assert model.controller.active.path == ""
    assert model.controller.active.suggested_filename == "job.slurm"
    assert model.controller.active.dirty
    assert model.controller.active.session_key == "pinned"
