
from setuptools import setup, find_packages

setup(
    name='Dictmaster',
    version='0.1',
    description='Downloading and converting dictionaries from the web',
    url='https://framagit.org/tuxor1337/dictmaster',
    author='Thomas Vogt',
    author_email='thomas.vogt@tovotu.de',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Topic :: Internet',
    ],
    keywords='dictionary language download',
    packages=find_packages(),
    package_data={'': ['*.glade']},
    install_requires=[
        "PyGObject",
        "pyquery",
        "beautifulsoup4",
        "jinja2",
        "lxml",
        "html5lib",
        "pyglossary",
    ],
    scripts=["bin/dictmaster"],
    project_urls={ 'Source': 'https://framagit.org/tuxor1337/dictmaster', },
)
