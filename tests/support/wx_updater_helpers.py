"""Shared support for wx updater behavior tests."""

def make_release(
    version="1.9.0",
    body="- Demo update\n- New features\n- Fixes",
    size=184 * 1024 * 1024,
):
    from hpc_gui.services.app_updater import UpdateRelease

    return UpdateRelease(
        version=version,
        tag=f"v{version}",
        zip_name="a.zip",
        zip_url="https://example.com/a.zip",
        sha_name="a.sha",
        sha_url="https://example.com/a.sha",
        html_url="https://example.com",
        body=body,
        size=size,
    )
