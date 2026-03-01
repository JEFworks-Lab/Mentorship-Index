# Mentorship Index Calculator

The Mentorship Index (M-index) measures a scientist's contribution to mentoring early-career scientists. The M-index counts publications where the scientist served as last author (the senior/mentoring role) and the first author (the mentee who led the work) was relatively new to science, proxied by the number of publications associated with their name at the time. For example, the M10-index is the number of last-author publications where the first author had fewer than 10 publications at the time.

## Website

`index.html` is a single-page web app that lets users look up any scientist's M-index. It runs entirely in the browser with no backend — all data is fetched live from the [OpenAlex](https://openalex.org/) API.

**Features:**
- Search for any author by name
- Configurable threshold N (default 10) to compute the M[N]-index

Note this quantification is liable to errors where the scientist's name is common (ie. not a unique identifier). 

## Python script

The M-index was initially developed and tested via a Python script `mentorship_index.py` and converted into Javascript for web accessibility. If you prefer to use Python, you can also run `python mentorship_index.py "Author Name"` to compute the M10 and M25 indices. 