import os

def setup_page_config(st, config):
    st.set_page_config(**config)


def ensure_dir_exists(path):
    """Ensure that the directory at 'path' exists."""
    os.makedirs(path, exist_ok=True)


def generate_output_filename(page_num, total_pages, prefix='page'):
    """Generate a zero-padded filename for a given page number."""
    width = max(3, len(str(total_pages)))
    return f"{prefix}_{str(page_num).zfill(width)}.pdf" 