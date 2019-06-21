# icsd-queryer

[![Build Status](https://travis-ci.org/kmu/icsd-queryer.svg?branch=master)](https://travis-ci.org/kmu/icsd-queryer)

A python module to query data from the ICSD using a [Selenium WebDriver](http://selenium-python.readthedocs.io/).

Requires ChromeDriver for Selenium. On a Mac,

```
brew tap homebrew/cask
brew cask install chromedriver
```
Tested on ChromeDriver 2.29.
Compatible with ICSD Version 4.2.0 (build 20190513-1424) - Data Release 2019.1

```
pip install -e .
```


## Testing

Store previously crawled files in `icsd-queryer/expected`.
Then run,

```
nosetests tests/*  --with-coverage    --cover-package .  --nocapture
```

One of the tests randomly picks up expected files and compared them with newly obtained data.


## Change from previous versions


### New keys in `meta_data.json`

- ICSD_version  

The version of ICSD during the crawling

- doi

DOI for the original literature

- abstract  

Abstract of the original literature

- theoretical_calculation
- data_quality
- experimental_PDF_number
- is_structure_prototype
- cell_constants_without_sd
- calculated_PDF_number
- modulated_structure
- only_cell_and_structure_type
- temperature_factors_available

### Abolished key

- misfit_layer  # could not find the corresponding field

### Conflicting keys

Following keys can have different values compared to the previous crawling.

- PDF_number  # because of a bug
- reference_2  # current ICSD seems to abolish multiple references 
- reference_3  
- R_value  # if unavailable, previous version returns `""`, while this version returns `None`.
