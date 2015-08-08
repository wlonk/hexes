=====
Usage
=====

To use Hexes in a project:

.. include:: ../scripts/hexes_example
    :code: python


The text input area is still larval. Give me bug reports!

---------------------
Musings on the future
---------------------

What sorts of widgets are important in a terminal app?

* Text areas
* Scrollable text areas
* Auto-scrolling text areas (as for chat or Twitter feed)
* Text input areas

These widgets should be relatively smart, knowing their own dimensions, when to
resize, how to listen to things (some sort of data-binding model here?), how to
style themselves, etc.
