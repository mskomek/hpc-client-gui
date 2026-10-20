"""Small navigation functions shared by the embedded Jobs pages."""

from __future__ import annotations


def select_workspace_page(notebook, page) -> None:
    for index in range(notebook.GetPageCount()):
        if notebook.GetPage(index) == page:
            notebook.SetSelection(index)
            return


def go_to_jobs(notebook, jobs_page, _event=None) -> None:
    select_workspace_page(notebook, jobs_page)
