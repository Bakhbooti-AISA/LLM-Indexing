## LLM Web Trafic Tracking Tool Kit

## Overview

This project contains variouse tool useful for tracking and studiying LLM Websearch. The main content of the project can be found in the src file which contain the SERP web scrapers and LLM web interface scrapers.

#### SERP Web Scrapers

They are two scraping tool:
1. bing_scraper.py -> Uses python requests module to simply send a get request to bings search engien.
2. google_scraper.py -> Uses serper.dev SERP API (needed to use an online servise as Googles website gardes against bots very strictly). Will have to create an account on there website to use (2500 free requests).

#### LLM Web Interface Scrapers	

#### Helpful Points
- Query = Search engine search. User prompt = what user writes to the LLM. Technially "Query" can be used for both but for sake of code understanding, we can make the definitions as such.
- An important note: very, Very, VERY much recomened to use a VPN or proxy while using SERP scrapers, as overuse can get your IP banned from the search engine.

