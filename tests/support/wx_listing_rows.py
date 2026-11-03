"""Helpers for assertions over local and remote wx listings."""


def content_rows(listing):
    """Visible entries excluding the navigation-only parent row."""
    return [
        (index, listing.GetItemText(index))
        for index in range(listing.GetItemCount())
        if listing.GetItemText(index) != ".."
    ]


def content_row(listing, name):
    return next(index for index, label in content_rows(listing) if label == name)


def select_content_row(listing, name):
    index = content_row(listing, name)
    listing.Select(index)
    return index
