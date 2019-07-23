from setuptools import setup

setup(
    version='0.0.4',
    name='icsd',
    install_requires=["PyYAML","beautifulsoup4", "selenium", "PyVirtualDisplay", "pandas", "tqdm"],
    entry_points={
        "console_scripts": [
            "icsd = icsd.main:main"
        ]
    },
    maintainer="Koki Muraoka",
    maintainer_email="KMuraoka@lbl.gov"
)
