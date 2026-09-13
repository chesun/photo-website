"""The build package for the photography site.

Modules:
    content  - load and validate everything under content/
    images   - resize photos, strip metadata, cache by content hash
    render   - turn content into HTML with Jinja2 templates
    serve    - local dev server with rebuild-on-change and the curate page

scripts/build.py is the command-line entry point that ties them together.
"""
